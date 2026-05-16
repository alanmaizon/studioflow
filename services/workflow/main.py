import os
import json
import base64
import time
import logging
from typing import Any
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

from google.cloud import firestore
from google.cloud import pubsub_v1
from google.cloud import run_v2

# Import OTel tracer
from observability.tracer import init_tracer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="StudioFlow Workflow Service")

# Initialize OTel Tracer
init_tracer("studioflow-workflow")
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer(__name__)

# Initialize GCP clients
project_id = os.environ.get("PROJECT_ID")
pubsub_topic = os.environ.get("PUBSUB_TOPIC", "studioflow-events")

firestore_client = firestore.Client(project=project_id)
pubsub_publisher = pubsub_v1.PublisherClient()
topic_path = pubsub_publisher.topic_path(project_id, pubsub_topic) if project_id else ""

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/pubsub/push")
async def handle_pubsub_message(request: Request):
    envelope = await request.json()
    if not envelope:
        raise HTTPException(status_code=400, detail="Bad request")
    if "message" not in envelope:
        raise HTTPException(status_code=400, detail="No message in envelope")

    message = envelope["message"]
    if "data" not in message:
        raise HTTPException(status_code=400, detail="No data in message")

    # Decode data
    try:
        data = base64.b64decode(message["data"]).decode("utf-8")
        payload = json.loads(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bad data payload: {e}")

    event_type = payload.get("event_type")
    asset_id = payload.get("asset_id")

    if not event_type or not asset_id:
        raise HTTPException(status_code=400, detail="Missing event_type or asset_id")

    with tracer.start_as_current_span(f"workflow_{event_type}") as span:
        span.set_attribute("asset.id", asset_id)
        span.set_attribute("event.type", event_type)

        if event_type == "asset.ingested":
            # State Machine: ingested -> encoding
            with tracer.start_as_current_span("state_transition_encoding") as st_span:
                # Update Firestore
                doc_ref = firestore_client.collection("assets").document(asset_id)
                doc_ref.update({"status": "encoding"})
                st_span.set_attribute("firestore.document", asset_id)
                st_span.set_attribute("asset.new_status", "encoding")

            # Publish next event
            with tracer.start_as_current_span("publish_encoding_requested") as pub_span:
                new_event = {
                    "event_type": "asset.encoding_requested",
                    "asset_id": asset_id,
                    "timestamp": time.time()
                }
                data_bytes = json.dumps(new_event).encode("utf-8")
                pubsub_publisher.publish(topic_path, data=data_bytes)
                pub_span.set_attribute("event.type", "asset.encoding_requested")

            return {"status": "success", "action": "transitioned_to_encoding"}
        else:
            # We don't handle other events yet
            span.set_attribute("workflow.ignored", True)
            return {"status": "success", "action": "ignored"}


# =============================================================================
# Admin endpoints — the "Pipeline API" surface per CLAUDE.md §8.
#
# The agent calls these after HumanApprovalGate returns status=approved. Every
# write action goes through verify_approval() first, and every execution writes
# to the Firestore audit_log/ collection so the demo can render an audit trail.
# =============================================================================

class ScaleRequest(BaseModel):
    """Scale a Cloud Run service. memory_mi is mebibytes (e.g. 2048 = 2Gi)."""
    service: str = Field(..., description="Cloud Run service name, e.g. 'studioflow-encode'")
    memory_mi: int = Field(..., gt=0, le=32768, description="New memory limit in Mi")
    approval_id: str = Field(..., description="approvals/{id} that authorised this action")


def _verify_approval(approval_id: str) -> dict[str, Any]:
    """Look up the approval doc and confirm status=approved. Raises 403 otherwise."""
    doc = firestore_client.collection("approvals").document(approval_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"approval {approval_id} not found")
    data = doc.to_dict() or {}
    if data.get("status") != "approved":
        raise HTTPException(
            status_code=403,
            detail=f"approval {approval_id} status is '{data.get('status')}', not 'approved'",
        )
    return data


def _audit_log(action: str, target: str, params: dict[str, Any],
               approval_id: str, simulated: bool, result: str) -> str:
    """Append a remediation execution entry to Firestore audit_log/. Returns the doc id."""
    doc_ref = firestore_client.collection("audit_log").document()
    doc_ref.set({
        "action": action,
        "target": target,
        "params": params,
        "approval_id": approval_id,
        "executed_at": firestore.SERVER_TIMESTAMP,
        "executed_by_service": "workflow-service",
        "simulated": simulated,
        "result": result,
    })
    logger.info("audit_log: action=%s target=%s approval_id=%s id=%s",
                action, target, approval_id, doc_ref.id)
    return doc_ref.id


_run_client = run_v2.ServicesClient()
_region = os.environ.get("REGION", "us-central1")
_scale_mode = os.environ.get("WORKFLOW_SCALE_MODE", "real").lower()  # "real" | "simulated"


def _otel_to_cloud_run_name(otel_name: str) -> str:
    """Map the OTel service.name the agent uses (e.g. 'studioflow-encode') to the
    Cloud Run service id (e.g. 'encode-service')."""
    stripped = otel_name.removeprefix("studioflow-")
    return f"{stripped}-service"


def _scale_cloud_run(cloud_run_name: str, memory_mi: int) -> str:
    """Update a Cloud Run service's memory limit via the admin API.
    Returns a short description suitable for audit_log.result."""
    name = f"projects/{project_id}/locations/{_region}/services/{cloud_run_name}"
    service = _run_client.get_service(name=name)
    if not service.template.containers:
        raise HTTPException(status_code=500, detail=f"{cloud_run_name} has no containers")
    container = service.template.containers[0]
    container.resources.limits["memory"] = f"{memory_mi}Mi"
    op = _run_client.update_service(service=service)
    op.result(timeout=180)  # block until rollout settles
    return f"scaled {cloud_run_name} to {memory_mi}Mi"


@app.post("/admin/scale")
def admin_scale(req: ScaleRequest):
    """Scale a Cloud Run service's memory. WORKFLOW_SCALE_MODE=simulated falls back
    to log+audit only; default 'real' actually calls the Cloud Run admin API."""
    with tracer.start_as_current_span("admin_scale") as span:
        span.set_attribute("approval.id", req.approval_id)
        span.set_attribute("service.target", req.service)
        span.set_attribute("scale.memory_mi", req.memory_mi)
        span.set_attribute("scale.mode", _scale_mode)
        _verify_approval(req.approval_id)

        simulated = _scale_mode == "simulated"
        if simulated:
            result = f"simulated scale of {req.service} to {req.memory_mi}Mi"
        else:
            cloud_run_name = _otel_to_cloud_run_name(req.service)
            span.set_attribute("scale.cloud_run_name", cloud_run_name)
            try:
                result = _scale_cloud_run(cloud_run_name, req.memory_mi)
            except Exception as e:
                span.record_exception(e)
                logger.exception("real scale failed for %s -> %dMi", cloud_run_name, req.memory_mi)
                raise HTTPException(status_code=502, detail=f"Cloud Run scale failed: {e}")

        audit_id = _audit_log(
            action="scale",
            target=req.service,
            params={"memory_mi": req.memory_mi},
            approval_id=req.approval_id,
            simulated=simulated,
            result=result,
        )
        span.set_attribute("audit_log.id", audit_id)
        return {
            "status": "executed",
            "simulated": simulated,
            "audit_id": audit_id,
            "service": req.service,
            "memory_mi": req.memory_mi,
        }


