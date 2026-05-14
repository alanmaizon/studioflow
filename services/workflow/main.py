import os
import json
import base64
import time
from fastapi import FastAPI, Request, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

from google.cloud import firestore
from google.cloud import pubsub_v1

# Import OTel tracer
from observability.tracer import init_tracer

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
