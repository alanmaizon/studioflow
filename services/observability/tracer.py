import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, DEPLOYMENT_ENVIRONMENT

logger = logging.getLogger(__name__)


def init_tracer(service_name: str) -> None:
    """
    Configure OTel → Dynatrace OTLP HTTP trace export.

    Required env vars:
      DT_TENANT             — tenant URL, either .apps.dynatrace.com or .live.dynatrace.com form
      DYNATRACE_API_TOKEN   — classic Dynatrace API token (dt0c01.*) with scope `openTelemetryTrace.ingest`
                              NOT a Platform Token (dt0s.*) — those are for MCP / Platform APIs.
      DEPLOYMENT_ENV        — optional, defaults to "dev"

    If env vars are missing, logs a warning and returns (no-op). This lets services boot
    locally without Dynatrace credentials.
    """
    dt_tenant = os.environ.get("DT_TENANT")
    dt_token = os.environ.get("DYNATRACE_API_TOKEN")
    env = os.environ.get("DEPLOYMENT_ENV", "dev")

    if not dt_tenant or not dt_token:
        logger.warning(
            "Tracer disabled: DT_TENANT=%s, DYNATRACE_API_TOKEN=%s. "
            "Spans will be created but not exported.",
            "set" if dt_tenant else "MISSING",
            "set" if dt_token else "MISSING",
        )
        return

    if dt_token.startswith("dt0s"):
        logger.error(
            "DYNATRACE_API_TOKEN looks like a Platform Token (dt0s prefix). "
            "OTLP ingest requires a classic API Token (dt0c01 prefix) with "
            "openTelemetryTrace.ingest scope. Refusing to configure exporter."
        )
        return

    # OTLP trace ingest lives on the classic .live. domain, not the Platform .apps. domain.
    # Dynatrace docs: https://docs.dynatrace.com/docs/ingest-from/opentelemetry/getting-started/otlp-export
    ingest_tenant = dt_tenant.replace("apps.dynatrace.com", "live.dynatrace.com")
    endpoint = f"{ingest_tenant.rstrip('/')}/api/v2/otlp/v1/traces"

    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        DEPLOYMENT_ENVIRONMENT: env,
    })

    exporter = OTLPSpanExporter(
        endpoint=endpoint,
        headers={"Authorization": f"Api-Token {dt_token}"},
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    logger.info("Tracer configured: service=%s endpoint=%s env=%s", service_name, endpoint, env)
