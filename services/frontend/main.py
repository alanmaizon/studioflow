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
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

from google.cloud import firestore

from observability.tracer import init_tracer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="StudioFlow Frontend")
init_tracer("studioflow-frontend")
FastAPIInstrumentor.instrument_app(app)
tracer = trace.get_tracer(__name__)

project_id = os.environ.get("PROJECT_ID")
firestore_client = firestore.Client(project=project_id) if project_id else None


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
    db = _require_firestore()
    with tracer.start_as_current_span("api_list_approvals") as span:
        q = db.collection("approvals")
        if status:
            q = q.where("status", "==", status)
        q = q.order_by("submitted_at", direction=firestore.Query.DESCENDING).limit(limit)
        docs = list(q.stream())
        span.set_attribute("approvals.count", len(docs))
        return [_approval_to_card(d) for d in docs]


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
