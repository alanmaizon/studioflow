#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "opentelemetry-api>=1.27",
#   "opentelemetry-sdk>=1.27",
#   "opentelemetry-exporter-otlp-proto-http>=1.27",
# ]
# ///
"""
Standalone OTLP/HTTP trace probe.

Sends one synthetic span to Dynatrace using the same SDK + exporter the services use.
This isolates the auth/endpoint question from any Cloud Run deployment.

Required env (typically sourced from .env):
  DT_TENANT              tenant URL (.apps or .live, either form works)
  DYNATRACE_API_TOKEN    classic API token (dt0c01.*) with scope openTelemetryTrace.ingest

Exit codes:
  0  success — trace exported
  1  failure — see stderr
  2  config — missing env / wrong token shape
"""
import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("verify-trace")

dt_tenant = os.environ.get("DT_TENANT")
dt_token = os.environ.get("DYNATRACE_API_TOKEN")

if not dt_tenant or not dt_token:
    log.error("Set DT_TENANT and DYNATRACE_API_TOKEN before running (source .env).")
    sys.exit(2)

if dt_token.startswith("dt0s"):
    log.error("DYNATRACE_API_TOKEN starts with dt0s (Platform Token). OTLP needs classic API token (dt0c01.*).")
    sys.exit(2)

ingest_host = dt_tenant.replace("apps.dynatrace.com", "live.dynatrace.com").rstrip("/")
endpoint = f"{ingest_host}/api/v2/otlp/v1/traces"
log.info("endpoint=%s", endpoint)

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, DEPLOYMENT_ENVIRONMENT

resource = Resource(attributes={
    SERVICE_NAME: "studioflow-probe",
    DEPLOYMENT_ENVIRONMENT: "verify",
})

exporter = OTLPSpanExporter(
    endpoint=endpoint,
    headers={"Authorization": f"Api-Token {dt_token}"},
)

provider = TracerProvider(resource=resource)
provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("verify-trace")

with tracer.start_as_current_span("verify_trace_probe") as span:
    trace_id = format(span.get_span_context().trace_id, "032x")
    span_id = format(span.get_span_context().span_id, "016x")
    span.set_attribute("probe.timestamp", int(time.time()))
    span.set_attribute("probe.note", "standalone OTLP verification")
    log.info("emitted span: trace_id=%s span_id=%s", trace_id, span_id)

# Force flush so SimpleSpanProcessor exports synchronously and we can read the result.
ok = provider.force_flush(timeout_millis=10_000)
provider.shutdown()

if ok:
    log.info("✅ Trace exported. Search Dynatrace for service 'studioflow-probe' / trace_id=%s", trace_id)
    sys.exit(0)
else:
    log.error("❌ Export did not complete within 10s. Check token scopes and tenant URL.")
    sys.exit(1)
