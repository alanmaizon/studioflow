"""
HumanApprovalGate — the soul of StudioFlow Agent.

The agent diagnoses, proposes a RemediationPlan, then HANDS THE WHEEL to a
human via this gate. The tool function blocks until a human marks the
Firestore approval doc as approved or rejected (or times out).

Firestore document at approvals/{plan_id}:
  status:        "pending" | "approved" | "rejected" | "timeout"
  hypothesis:    str
  confidence:    "low" | "medium" | "high"
  evidence:      list[dict]   — each: {source, id, what_it_shows}
  proposed_actions: list[dict] — each: {action, target, params}
  submitted_at:  Firestore timestamp
  decided_at:    Firestore timestamp (set by frontend)
  decided_by:    str (set by frontend)
  decision_note: str (optional, set by frontend)
"""
from __future__ import annotations

import os
import time
import uuid
import logging
from typing import Any

from google.cloud import firestore

logger = logging.getLogger(__name__)

# Demo defaults. Polling interval is short for a snappy demo; the 5-minute
# timeout caps the agent loop so it never hangs forever in a CI run.
_POLL_INTERVAL_S = 2.0
_DEFAULT_TIMEOUT_S = 300.0
_TERMINAL_STATUSES = {"approved", "rejected"}


def _firestore() -> firestore.Client:
    project = os.environ.get("PROJECT_ID")
    if not project:
        raise RuntimeError("PROJECT_ID env var required for HumanApprovalGate")
    return firestore.Client(project=project)


def request_remediation_approval(
    hypothesis: str,
    confidence: str,
    proposed_actions: list[dict[str, Any]],
    evidence: list[dict[str, Any]] | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Submit a remediation plan to the human approval queue and BLOCK until decided.

    Use this tool AFTER diagnosing an incident. Pass the same fields you would put
    in your IncidentResponse JSON. The tool writes the plan to Firestore at
    approvals/{generated_id} with status="pending", then polls until a human
    operator marks it approved or rejected via the Studio Control Room UI.

    NEVER call write/remediation actions without going through this gate first.
    The hackathon brief's "while keeping you in control" requirement depends on it.

    Args:
        hypothesis: One-sentence root cause from your diagnosis.
        confidence: "low" | "medium" | "high"
        proposed_actions: List of {action, target, params} dicts. Same shape
            as your IncidentResponse.proposed_actions.
        evidence: Optional list of {source, id, what_it_shows} dicts citing
            Dynatrace trace IDs / DQL results / git history.
        timeout_seconds: How long to wait. Defaults to 300s (5 minutes). The
            tool returns status="timeout" if no decision arrives in time.

    Returns:
        A dict with:
          plan_id:        the Firestore document id (str)
          status:         "approved" | "rejected" | "timeout"
          decided_by:     str (human operator id, only when not timeout)
          decided_at:     ISO timestamp string (only when not timeout)
          decision_note:  str, optional human-written rationale
    """
    plan_id = uuid.uuid4().hex
    timeout = timeout_seconds if timeout_seconds is not None else _DEFAULT_TIMEOUT_S

    db = _firestore()
    doc_ref = db.collection("approvals").document(plan_id)

    doc_ref.set({
        "status": "pending",
        "hypothesis": hypothesis,
        "confidence": confidence,
        "proposed_actions": proposed_actions,
        "evidence": evidence or [],
        "submitted_at": firestore.SERVER_TIMESTAMP,
    })
    logger.info("HumanApprovalGate: submitted plan_id=%s timeout=%.0fs", plan_id, timeout)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            status = data.get("status")
            if status in _TERMINAL_STATUSES:
                decided_at_field = data.get("decided_at")
                decided_at_iso = (
                    decided_at_field.isoformat()
                    if decided_at_field and hasattr(decided_at_field, "isoformat")
                    else None
                )
                logger.info(
                    "HumanApprovalGate: plan_id=%s decided status=%s by=%s",
                    plan_id, status, data.get("decided_by"),
                )
                return {
                    "plan_id": plan_id,
                    "status": status,
                    "decided_by": data.get("decided_by"),
                    "decided_at": decided_at_iso,
                    "decision_note": data.get("decision_note"),
                }
        time.sleep(_POLL_INTERVAL_S)

    # Timeout — record it on the doc so the UI shows the lapsed state.
    doc_ref.update({"status": "timeout"})
    logger.warning("HumanApprovalGate: plan_id=%s timed out after %.0fs", plan_id, timeout)
    return {
        "plan_id": plan_id,
        "status": "timeout",
        "decided_by": None,
        "decided_at": None,
        "decision_note": None,
    }
