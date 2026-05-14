import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, DEPLOYMENT_ENVIRONMENT

def init_tracer(service_name: str) -> None:
    dt_tenant = os.environ.get("DT_TENANT")
    # Use API token for trace ingest, fallback to DT_TOKEN (Platform Token) if needed
    dt_token = os.environ.get("DYNATRACE_API_TOKEN") or os.environ.get("DT_TOKEN")
    env = os.environ.get("DEPLOYMENT_ENV", "dev")

    if not dt_tenant or not dt_token:
        logging.warning("DT_TENANT or OTLP api token not set, tracer will not export to Dynatrace.")
        return

    # Rewrite apps.dynatrace.com to live.dynatrace.com for OTLP ingest
    if "apps.dynatrace.com" in dt_tenant:
        ingest_tenant = dt_tenant.replace("apps.dynatrace.com", "live.dynatrace.com")
    else:
        ingest_tenant = dt_tenant
        
    endpoint = f"{ingest_tenant}/api/v2/otlp/v1/traces"

    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        DEPLOYMENT_ENVIRONMENT: env
    })
    
    provider = TracerProvider(resource=resource)
    
    # We use Api-Token for classic Dynatrace API tokens (dt0c01.*)
    exporter = OTLPSpanExporter(
        endpoint=endpoint,
        headers={"Authorization": f"Api-Token {dt_token}"}
    )
    
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
