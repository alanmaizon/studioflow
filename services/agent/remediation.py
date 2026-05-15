"""
Remediation tools — the executable end of the agent's pipeline_api.

Each function below maps 1:1 to an endpoint on the workflow service's admin
surface. The agent must already hold an approval_id from a successful
request_remediation_approval call before invoking these — the workflow service
rejects unapproved or non-matching approval_ids with 403/404.

Required env:
  WORKFLOW_URL    Base URL of the workflow service. Default falls back to the
                  Cloud Run-provided URL for this project.
"""
from __future__ import annotations

import os
import logging
from typing import Any

import urllib.request
import urllib.error
import json

logger = logging.getLogger(__name__)

_DEFAULT_WORKFLOW_URL = "https://workflow-service-vb6z2eah4a-uc.a.run.app"
_REQUEST_TIMEOUT_S = 30.0


def _workflow_base() -> str:
    return os.environ.get("WORKFLOW_URL", _DEFAULT_WORKFLOW_URL).rstrip("/")


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{_workflow_base()}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            logger.info("remediation %s OK: %s", path, payload)
            return payload
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        logger.warning("remediation %s HTTP %d: %s", path, e.code, detail)
        return {"status": "error", "http_status": e.code, "detail": detail}
    except Exception as e:  # noqa: BLE001
        logger.exception("remediation %s failed", path)
        return {"status": "error", "detail": str(e)}


def scale_service(service: str, memory_mi: int, approval_id: str) -> dict[str, Any]:
    """Scale a Cloud Run service's memory limit. CALL ONLY AFTER `request_remediation_approval`
    returns status="approved" AND the approved plan contains an action matching this call.

    Args:
        service:     Cloud Run service name (e.g. "studioflow-encode").
        memory_mi:   New memory limit in mebibytes. 2048 = 2Gi.
        approval_id: The plan_id returned by `request_remediation_approval`.

    Returns:
        Dict with execution outcome. On success contains:
          status:    "executed"
          simulated: bool (true until real Cloud Run mutation is wired)
          audit_id:  Firestore audit_log/{id}
          service:   the targeted service
          memory_mi: the applied memory value
        On error: status="error", http_status, detail.
    """
    return _post("/admin/scale", {
        "service": service,
        "memory_mi": memory_mi,
        "approval_id": approval_id,
    })


