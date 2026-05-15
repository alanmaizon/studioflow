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


@app.post("/admin/scale")
def admin_scale(req: ScaleRequest):
    """Scale a Cloud Run service's memory. Currently SIMULATED — logs + audits without
    mutating Cloud Run. The boundary stays correct so we can swap in real
    google-cloud-run admin calls behind this endpoint without changing the agent."""
    with tracer.start_as_current_span("admin_scale") as span:
        span.set_attribute("approval.id", req.approval_id)
        span.set_attribute("service.target", req.service)
        span.set_attribute("scale.memory_mi", req.memory_mi)
        _verify_approval(req.approval_id)
        audit_id = _audit_log(
            action="scale",
            target=req.service,
            params={"memory_mi": req.memory_mi},
            approval_id=req.approval_id,
            simulated=True,
            result=f"simulated scale of {req.service} to {req.memory_mi}Mi",
        )
        span.set_attribute("audit_log.id", audit_id)
        return {
            "status": "executed",
            "simulated": True,
            "audit_id": audit_id,
            "service": req.service,
            "memory_mi": req.memory_mi,
        }


