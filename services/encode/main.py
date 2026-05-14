import os
import json
import base64
import time
import asyncio
from fastapi import FastAPI, Request, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

from google.cloud import pubsub_v1

# Import OTel tracer
from observability.tracer import init_tracer

app = FastAPI(title="StudioFlow Encode Service (Stub)")

# Initialize OTel Tracer
init_tracer("studioflow-encode")
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer(__name__)

# Initialize GCP clients
project_id = os.environ.get("PROJECT_ID")
pubsub_topic = os.environ.get("PUBSUB_TOPIC", "studioflow-events")

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
    
    # GCP Pub/Sub pushes envelope["message"]["data"]
    message = envelope.get("message", {})
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

    # Only process target event type
    if event_type != "asset.encoding_requested":
        return {"status": "success", "action": "ignored"}

    with tracer.start_as_current_span("encode_asset") as span:
        span.set_attribute("asset.id", asset_id)
        span.set_attribute("event.type", event_type)

        # 1. Stub the encoding process (Sleep 3 seconds)
        with tracer.start_as_current_span("ffmpeg_transcode_stub") as sleep_span:
            sleep_span.set_attribute("action", "simulating_transcode")
            await asyncio.sleep(3)

        # 2. Publish next event
        with tracer.start_as_current_span("publish_encoded") as pub_span:
            new_event = {
                "event_type": "asset.encoded",
                "asset_id": asset_id,
                "timestamp": time.time()
            }
            data_bytes = json.dumps(new_event).encode("utf-8")
            pubsub_publisher.publish(topic_path, data=data_bytes)
            pub_span.set_attribute("event.type", "asset.encoded")

        return {"status": "success", "action": "encoded"}
