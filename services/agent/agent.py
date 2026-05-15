"""
StudioFlow Agent — Day 10 skeleton.

A Gemini-powered ADK agent that uses the Dynatrace remote MCP server as its
primary tool. This module exposes `root_agent`, which is what ADK's runner
picks up.

Required env (typically sourced from .env):
  DT_TENANT                 tenant URL on .apps.dynatrace.com (Platform/Grail)
  DT_TOKEN                  Dynatrace Platform Token (dt0s.*) for MCP auth
  GOOGLE_CLOUD_PROJECT      GCP project for Vertex AI
  GOOGLE_CLOUD_LOCATION     usually us-central1
  GOOGLE_GENAI_USE_VERTEXAI True (so ADK routes via Vertex AI ADC, not API keys)

Optional:
  AGENT_MODEL               Gemini model id. Default `gemini-flash-latest` for
                            cheap iteration; switch to `gemini-3.1-pro-preview`
                            once we're locked on the prompt.
"""
import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from approval_gate import request_remediation_approval
from remediation import scale_service


def _load_system_instruction() -> str:
    path = Path(__file__).parent / "prompts" / "system.md"
    return path.read_text(encoding="utf-8")


def _build_dynatrace_toolset() -> McpToolset:
    tenant = os.environ.get("DT_TENANT")
    token = os.environ.get("DT_TOKEN")
    if not tenant or not token:
        raise RuntimeError(
            "DT_TENANT and DT_TOKEN must be set (source .env). "
            "DT_TOKEN must be a Platform Token (dt0s.*) — the OTLP classic "
            "API token in DYNATRACE_API_TOKEN does NOT work with the MCP gateway."
        )
    if not token.startswith("dt0s"):
        raise RuntimeError(
            "DT_TOKEN does not look like a Platform Token (expected dt0s.* prefix). "
            "MCP requires a Platform Token, not a classic API token."
        )

    mcp_url = (
        os.environ.get("DT_MCP_URL")
        or f"{tenant.rstrip('/')}/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp"
    )

    # Whitelist the schema-clean tools we actually need for incident diagnosis.
    # The Dynatrace MCP also exposes anomaly-detector tools whose JSON schemas
    # omit required `type` fields and crash Gemini's function-call validator.
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=mcp_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        ),
        tool_filter=[
            "query-problems",
            "get-problem-by-id",
            "execute-dql",
            "create-dql",
            "explain-dql",
            "get-entity-id",
            "get-entity-name",
            "find-documents",
            "ask-dynatrace-docs",
            "get-vulnerabilities",
        ],
    )


# Per CLAUDE.md §0 the brain is gemini-3.1-pro-preview. For sub-tasks (cheaper,
# faster, lower thinking budget) callers can override via AGENT_MODEL or use
# GEMINI_FLASH_MODEL directly. Defaults cascade Pro → Flash → safety fallback.
MODEL = (
    os.environ.get("AGENT_MODEL")
    or os.environ.get("GEMINI_MODEL")
    or os.environ.get("GEMINI_FLASH_MODEL")
    or "gemini-3.1-pro-preview"
)

root_agent = LlmAgent(
    model=MODEL,
    name="studioflow_agent",
    description="SRE copilot for the StudioFlow media pipeline. Uses Dynatrace observability to diagnose incidents.",
    instruction=_load_system_instruction(),
    tools=[
        _build_dynatrace_toolset(),
        FunctionTool(request_remediation_approval),
        FunctionTool(scale_service),
    ],
)
