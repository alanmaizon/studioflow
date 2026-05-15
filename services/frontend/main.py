"""
StudioFlow Frontend service — serves the Studio Control Room and a thin Firestore-backed API.

The HTML/JSX prototype in `frontend/ui_kits/control_room` is served as static
assets, and the React app (running in the browser) fetches live state from the
JSON endpoints below instead of the static `data.js` fixtures.

Endpoints:
  GET  /                                Redirect to the Control Room prototype.
  GET  /health                          Health probe.
  GET  /api/assets                      Live Firestore `assets/` collection.
  GET  /api/approvals?status=pending    Live Firestore `approvals/` collection (optionally filtered).
  POST /api/approvals/{plan_id}/decide  Approve or reject an approval plan.
  GET  /api/audit-log?limit=20          Recent Firestore `audit_log/` entries.
  GET  /api/pipeline-summary            Aggregated counts per pipeline stage.
"""
from __future__ import annotations

import os
import json
import time
import uuid
import logging
import urllib.request
import urllib.error
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

from google.cloud import firestore, pubsub_v1

from observability.tracer import init_tracer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="StudioFlow Frontend")
init_tracer("studioflow-frontend")
FastAPIInstrumentor.instrument_app(app)
tracer = trace.get_tracer(__name__)

project_id = os.environ.get("PROJECT_ID")
firestore_client = firestore.Client(project=project_id) if project_id else None
pubsub_publisher = pubsub_v1.PublisherClient() if project_id else None

PUBSUB_TOPIC = os.environ.get("PUBSUB_TOPIC", "studioflow-events")
GCS_BUCKET = os.environ.get("GCS_BUCKET") or (f"{project_id}-assets" if project_id else "")
AGENT_URL = (os.environ.get("AGENT_URL") or "").rstrip("/")
CHAOS_GCS_OBJECT = os.environ.get("CHAOS_GCS_OBJECT", "chaos/chaos_dummy.mp4")
TOPIC_PATH = pubsub_publisher.topic_path(project_id, PUBSUB_TOPIC) if (pubsub_publisher and project_id) else ""


# =============================================================================
# Helpers — translate Firestore docs into shapes the prototype already expects.
# =============================================================================

_STATE_PROGRESS = {
    "ingested": 5,
    "encoding": 45,
    "encoded": 75,
    "enriching": 85,
    "enriched": 95,
    "review": 95,
    "published": 100,
    "failed": 0,
}

_STATE_TINT = {
    "ingested":  "#3a3a3c",
    "encoding":  "#3a3a3c",
    "encoded":   "#ff9f0a25",
    "enriching": "#5e5ce625",
    "enriched":  "#5e5ce625",
    "review":    "#3a3a3c",
    "published": "#30d15825",
    "failed":    "#ff453a25",
}


def _ts(value: Any) -> str | None:
    """Firestore Timestamp / datetime -> ISO string."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _hhmm(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    return None


def _duration(start: Any, end: Any = None) -> str:
    if start is None or not hasattr(start, "timestamp"):
        return "—"
    end_dt = end if end is not None and hasattr(end, "timestamp") else datetime.now(timezone.utc)
    delta = end_dt - start
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m"


def _codec_from_filename(fn: str | None) -> str:
    if not fn:
        return "h264"
    lower = fn.lower()
    if ".prores" in lower or ".mov" in lower:
        return "prores"
    return "h264"


def _asset_to_card(doc: firestore.DocumentSnapshot) -> dict[str, Any]:
    d = doc.to_dict() or {}
    state = (d.get("status") or "ingested").lower()
    created = d.get("created_at")
    encoded = d.get("encoded_at")
    filename = d.get("filename") or doc.id
    return {
        "id": doc.id,
        "title": filename,
        "codec": _codec_from_filename(filename),
        "size": d.get("size_label") or "—",
        "state": state,
        "progress": _STATE_PROGRESS.get(state, 0),
        "started": _hhmm(created) or "—",
        "duration": _duration(created, encoded),
        "tint": _STATE_TINT.get(state, "#3a3a3c"),
    }


def _approval_to_card(doc: firestore.DocumentSnapshot) -> dict[str, Any]:
    d = doc.to_dict() or {}
    return {
        "id": doc.id,
        "status": d.get("status"),
        "hypothesis": d.get("hypothesis"),
        "confidence": d.get("confidence"),
        "proposed_actions": d.get("proposed_actions") or [],
        "evidence": d.get("evidence") or [],
        "submitted_at": _ts(d.get("submitted_at")),
        "decided_at": _ts(d.get("decided_at")),
        "decided_by": d.get("decided_by"),
        "decision_note": d.get("decision_note"),
    }


def _audit_to_card(doc: firestore.DocumentSnapshot) -> dict[str, Any]:
    d = doc.to_dict() or {}
    return {
        "id": doc.id,
        "action": d.get("action"),
        "target": d.get("target"),
        "params": d.get("params") or {},
        "approval_id": d.get("approval_id"),
        "executed_at": _ts(d.get("executed_at")),
        "executed_by_service": d.get("executed_by_service"),
        "simulated": d.get("simulated"),
        "result": d.get("result"),
    }


def _require_firestore() -> firestore.Client:
    if firestore_client is None:
        raise HTTPException(status_code=503, detail="Firestore client not initialized (PROJECT_ID missing)")
    return firestore_client


# =============================================================================
# API endpoints
# =============================================================================

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/assets")
def list_assets(limit: int = 30):
    db = _require_firestore()
    with tracer.start_as_current_span("api_list_assets") as span:
        docs = list(
            db.collection("assets")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        span.set_attribute("assets.count", len(docs))
        return [_asset_to_card(d) for d in docs]


@app.get("/api/approvals")
def list_approvals(status: str | None = None, limit: int = 20):
    """List approvals. Filter by status in Python (avoids needing a Firestore
    composite index for the where+orderBy combo at our scale)."""
    db = _require_firestore()
    with tracer.start_as_current_span("api_list_approvals") as span:
        # Pull a generous batch ordered by submitted_at DESC, then filter.
        docs = list(
            db.collection("approvals")
            .order_by("submitted_at", direction=firestore.Query.DESCENDING)
            .limit(max(limit * 4, 40))
            .stream()
        )
        cards = [_approval_to_card(d) for d in docs]
        if status:
            cards = [c for c in cards if c.get("status") == status]
        span.set_attribute("approvals.count", len(cards))
        return cards[:limit]


class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    decided_by: str = Field(default="operator@studio-control-room")
    decision_note: str | None = None


@app.post("/api/approvals/{plan_id}/decide")
def decide_approval(plan_id: str, body: DecisionRequest):
    """Operator approves or rejects a pending plan. Unblocks the agent's HumanApprovalGate."""
    db = _require_firestore()
    with tracer.start_as_current_span("api_decide_approval") as span:
        span.set_attribute("approval.id", plan_id)
        span.set_attribute("approval.decision", body.decision)
        doc_ref = db.collection("approvals").document(plan_id)
        snap = doc_ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail=f"approval {plan_id} not found")
        current = (snap.to_dict() or {}).get("status")
        if current != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"approval {plan_id} is already '{current}' — cannot re-decide",
            )
        doc_ref.update({
            "status": body.decision,
            "decided_at": firestore.SERVER_TIMESTAMP,
            "decided_by": body.decided_by,
            "decision_note": body.decision_note or f"{body.decision} via Studio Control Room",
        })
        logger.info("approvals/%s decided: %s by %s", plan_id, body.decision, body.decided_by)
        return {"plan_id": plan_id, "status": body.decision, "decided_by": body.decided_by}


@app.get("/api/audit-log")
def list_audit_log(limit: int = 20):
    db = _require_firestore()
    with tracer.start_as_current_span("api_list_audit_log") as span:
        docs = list(
            db.collection("audit_log")
            .order_by("executed_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        span.set_attribute("audit_log.count", len(docs))
        return [_audit_to_card(d) for d in docs]


@app.get("/api/pipeline-summary")
def pipeline_summary():
    """Aggregate live counts per pipeline stage. Drives the four big pipeline tiles."""
    db = _require_firestore()
    buckets = {
        "ingest":     0,
        "encode":     0,
        "enrichment": 0,
        "publish":    0,
    }
    for doc in db.collection("assets").stream():
        state = ((doc.to_dict() or {}).get("status") or "").lower()
        if state == "ingested":
            buckets["ingest"] += 1
        elif state in ("encoding", "encoded"):
            buckets["encode"] += 1
        elif state in ("enriching", "enriched", "review"):
            buckets["enrichment"] += 1
        elif state == "published":
            buckets["publish"] += 1

    return [
        {"id": "ingest",     "name": "Ingest",     "count": buckets["ingest"],     "health": "healthy", "meta": "p99 1.8s"},
        {"id": "encode",     "name": "Encode",     "count": buckets["encode"],     "health": "healthy", "meta": "p99 14s"},
        {"id": "enrichment", "name": "Enrichment", "count": buckets["enrichment"], "health": "healthy", "meta": "p99 6s"},
        {"id": "publish",    "name": "Publish",    "count": buckets["publish"],    "health": "healthy", "meta": "p99 2.1s"},
    ]


# =============================================================================
# Demo trigger endpoints — make the UI's "Run chaos" + "Diagnose" buttons real.
# =============================================================================

class ChaosResponse(BaseModel):
    asset_id: str
    message_count: int
    gcs_uri: str


@app.post("/api/chaos/trigger", response_model=ChaosResponse)
def trigger_chaos():
    """Mirror scripts/chaos.sh: register a fresh chaos asset against the
    pre-staged chaos_dummy.mp4 in GCS and publish 10 encoding-requested
    events in parallel. The encode service's deterministic file-size trigger
    fires MEMORY_LEAK on the first request that hits the threshold."""
    db = _require_firestore()
    if not pubsub_publisher or not TOPIC_PATH:
        raise HTTPException(status_code=503, detail="Pub/Sub publisher not initialized")
    asset_id = f"chaos-{uuid.uuid4().hex}"
    gcs_uri = f"gs://{GCS_BUCKET}/{CHAOS_GCS_OBJECT}"
    with tracer.start_as_current_span("api_chaos_trigger") as span:
        span.set_attribute("asset.id", asset_id)
        span.set_attribute("gcs.uri", gcs_uri)
        db.collection("assets").document(asset_id).set({
            "id": asset_id,
            "status": "encoding",
            "gcs_uri": gcs_uri,
            "filename": f"chaos-{asset_id[:8]}.mp4",
            "created_at": firestore.SERVER_TIMESTAMP,
            "source": "chaos-button",
        })
        payload = json.dumps({
            "event_type": "asset.encoding_requested",
            "asset_id": asset_id,
            "timestamp": time.time(),
        }).encode("utf-8")
        # Concurrent publish — match the burst chaos.sh produces.
        BURST = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=BURST) as pool:
            futures = [pool.submit(lambda: pubsub_publisher.publish(TOPIC_PATH, data=payload).result(timeout=15))
                       for _ in range(BURST)]
            for f in concurrent.futures.as_completed(futures):
                f.result()
        logger.info("chaos triggered: asset_id=%s messages=%d", asset_id, BURST)
        span.set_attribute("messages.published", BURST)
        return ChaosResponse(asset_id=asset_id, message_count=BURST, gcs_uri=gcs_uri)


class DiagnoseRequest(BaseModel):
    prompt: str | None = None


@app.post("/api/agent/diagnose")
def proxy_diagnose(req: DiagnoseRequest):
    """Proxy to the deployed agent service's /diagnose. Keeps the agent URL
    out of the browser and lets the browser fetch hit the same origin."""
    if not AGENT_URL:
        raise HTTPException(status_code=503, detail="AGENT_URL env var not configured on frontend service")
    body = json.dumps({"prompt": req.prompt} if req.prompt else {}).encode("utf-8")
    request = urllib.request.Request(
        f"{AGENT_URL}/diagnose",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with tracer.start_as_current_span("api_proxy_diagnose") as span:
        span.set_attribute("agent.url", AGENT_URL)
        try:
            with urllib.request.urlopen(request, timeout=540) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                span.set_attribute("agent.audit_id", payload.get("audit_id") or "")
                span.set_attribute("agent.approval_status", payload.get("approval_status") or "")
                return payload
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            logger.warning("agent /diagnose returned HTTP %d: %s", e.code, detail)
            raise HTTPException(status_code=e.code, detail=detail) from e
        except Exception as e:  # noqa: BLE001
            logger.exception("agent /diagnose proxy failed")
            raise HTTPException(status_code=502, detail=f"agent proxy error: {e}") from e


# =============================================================================
# Static files — serve the prototype.
# =============================================================================

# `static/` is populated at build time (Dockerfile copies frontend/ -> static/).
# In local dev, fall back to the in-repo frontend/ folder.
_STATIC_DIR = Path(__file__).parent / "static"
if not _STATIC_DIR.exists():
    _STATIC_DIR = Path(__file__).parent.parent.parent / "frontend"


@app.get("/")
def index():
    return RedirectResponse(url="/ui_kits/control_room/index.html")


# Mount must be last — any unmatched route falls through to static files.
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="frontend")
