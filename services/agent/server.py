"""
StudioFlow Agent — Cloud Run FastAPI shim.

Wraps the local `run.py` agent loop in a single HTTP endpoint so the agent
can be triggered from the Studio Control Room UI (or `curl`) rather than a
developer laptop. Cloud Run keeps the instance alive while the request is in
flight, which is exactly the window we need to span the
diagnose → submit-plan → block-on-approval-gate → execute lifecycle.

Endpoints:
  GET  /health      health probe.
  POST /diagnose    body: { "prompt": str (optional) }.
                    Runs the agent loop synchronously. Returns the agent's
                    final user-facing text plus a small structured summary
                    parsed from the tool call log (plan_id, audit_id).
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

# Ensure Vertex AI routing env vars are set BEFORE we import the agent module
# (which constructs the LlmAgent on import).
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.environ.get("PROJECT_ID", ""))
os.environ.setdefault(
    "GOOGLE_CLOUD_LOCATION",
    os.environ.get("VERTEX_LOCATION") or os.environ.get("REGION", "us-central1"),
)

from observability.tracer import init_tracer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="StudioFlow Agent")
init_tracer("studioflow-agent")
FastAPIInstrumentor.instrument_app(app)
tracer = trace.get_tracer(__name__)

# Lazy import to avoid the SDK side effects on health probes (Cloud Run startup
# probes will succeed faster).
_AGENT = None
_DEFAULT_PROMPT = (
    "Diagnose studioflow-encode. Find recent boom.oom_killed=true spans in Dynatrace, "
    "build an IncidentResponse plan proposing scaling encode to 2Gi (memory_mi=2048), "
    "call request_remediation_approval with timeout_seconds=180, and after approval "
    "call scale_service(service='studioflow-encode', memory_mi=2048, approval_id=<plan_id>). "
    "Report the audit_id in your final summary."
)


def _agent():
    global _AGENT
    if _AGENT is None:
        from agent import root_agent
        _AGENT = root_agent
    return _AGENT


class DiagnoseRequest(BaseModel):
    prompt: str | None = Field(default=None, description="Override the default diagnostic prompt.")


class DiagnoseResponse(BaseModel):
    model: str
    summary: str
    plan_id: str | None = None
    audit_id: str | None = None
    approval_status: str | None = None
    tool_calls: list[dict[str, Any]] = []


@app.get("/health")
def health():
    return {"status": "ok"}


async def _run_agent(prompt: str) -> DiagnoseResponse:
    from google.adk.runners import InMemoryRunner
    from google.genai import types as genai_types

    agent = _agent()
    runner = InMemoryRunner(agent=agent, app_name="studioflow-agent-api")
    session = await runner.session_service.create_session(
        app_name="studioflow-agent-api",
        user_id="frontend",
    )

    message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=prompt)],
    )

    final_text: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    plan_id: str | None = None
    audit_id: str | None = None
    approval_status: str | None = None

    async for event in runner.run_async(
        user_id="frontend",
        session_id=session.id,
        new_message=message,
    ):
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            if part.function_call:
                tool_calls.append({
                    "phase": "request",
                    "tool": part.function_call.name,
                    "args": {k: v for k, v in (part.function_call.args or {}).items()},
                })
            if part.function_response:
                response = part.function_response.response
                if isinstance(response, dict):
                    if response.get("plan_id"):
                        plan_id = response["plan_id"]
                    if response.get("audit_id"):
                        audit_id = response["audit_id"]
                    if part.function_response.name == "request_remediation_approval":
                        approval_status = response.get("status")
                tool_calls.append({
                    "phase": "response",
                    "tool": part.function_response.name,
                    "result_preview": str(response)[:300],
                })
            if part.text and event.is_final_response():
                final_text.append(part.text)

    return DiagnoseResponse(
        model=agent.model,
        summary="\n".join(final_text) if final_text else "(agent produced no final text)",
        plan_id=plan_id,
        audit_id=audit_id,
        approval_status=approval_status,
        tool_calls=tool_calls,
    )


@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(req: DiagnoseRequest):
    prompt = req.prompt or _DEFAULT_PROMPT
    with tracer.start_as_current_span("agent_diagnose") as span:
        span.set_attribute("agent.prompt.length", len(prompt))
        result = await _run_agent(prompt)
        span.set_attribute("agent.plan_id", result.plan_id or "")
        span.set_attribute("agent.audit_id", result.audit_id or "")
        span.set_attribute("agent.approval_status", result.approval_status or "")
        span.set_attribute("agent.tool_call_count", len(result.tool_calls))
        return result
