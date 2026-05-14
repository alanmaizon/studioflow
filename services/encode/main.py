import os
import json
import base64
import time
import asyncio
import tempfile
import subprocess
from fastapi import FastAPI, Request, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
import logging

from google.cloud import pubsub_v1
from google.cloud import firestore
from google.cloud import storage

from observability.tracer import init_tracer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="StudioFlow Encode Service (Real)")

init_tracer("studioflow-encode")
FastAPIInstrumentor.instrument_app(app)
tracer = trace.get_tracer(__name__)

project_id = os.environ.get("PROJECT_ID")
pubsub_topic = os.environ.get("PUBSUB_TOPIC", "studioflow-events")

firestore_client = firestore.Client(project=project_id)
storage_client = storage.Client(project=project_id)
pubsub_publisher = pubsub_v1.PublisherClient()
topic_path = pubsub_publisher.topic_path(project_id, pubsub_topic) if project_id else ""

# State variables for our scripted incidents
active_encodes = 0
_leaked_memory = []

@app.get("/health")
def health_check():
    return {"status": "ok", "active_encodes": active_encodes}

@app.post("/pubsub/push")
async def handle_pubsub_message(request: Request):
    global active_encodes
    
    envelope = await request.json()
    if not envelope:
        raise HTTPException(status_code=400, detail="Bad request")
    
    message = envelope.get("message", {})
    if "data" not in message:
        raise HTTPException(status_code=400, detail="No data in message")

    try:
        data = base64.b64decode(message["data"]).decode("utf-8")
        payload = json.loads(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bad data payload: {e}")

    event_type = payload.get("event_type")
    asset_id = payload.get("asset_id")

    if not event_type or not asset_id:
        raise HTTPException(status_code=400, detail="Missing event_type or asset_id")

    if event_type != "asset.encoding_requested":
        return {"status": "success", "action": "ignored"}

    active_encodes += 1
    try:
        with tracer.start_as_current_span("encode_asset") as span:
            span.set_attribute("asset.id", asset_id)
            span.set_attribute("event.type", event_type)
            span.set_attribute("encode.active_encodes_at_start", active_encodes)

            # Get Asset from Firestore
            doc_ref = firestore_client.collection("assets").document(asset_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise HTTPException(status_code=404, detail="Asset not found")
            
            asset_data = doc.to_dict()
            gcs_uri = asset_data.get("gcs_uri")
            if not gcs_uri or not gcs_uri.startswith("gs://"):
                raise HTTPException(status_code=400, detail="Invalid GCS URI")

            # Parse gs://bucket/path/to/blob
            parts = gcs_uri[5:].split("/", 1)
            bucket_name = parts[0]
            blob_name = parts[1]

            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            # Reload to get size
            blob.reload()
            file_size = blob.size or 0

            # ---------------------------------------------------------
            # DELIBERATE FAILURE MODE: MEMORY_LEAK
            # ---------------------------------------------------------
            # Trigger: file > 500MB and concurrent > 3
            # We use 500MB = 500 * 1024 * 1024
            if file_size > (500 * 1024 * 1024) and active_encodes > 3:
                span.set_attribute("boom.oom_killed", True)
                logger.warning("MEMORY_LEAK scripted failure triggered!")
                # Deliberately allocate a massive 2GB buffer and maintain reference to trigger OOM limit in Cloud Run
                _leaked_memory.append(bytearray(2 * 1024 * 1024 * 1024))
            
            # Use temp directory for downloading and transcoding
            with tempfile.TemporaryDirectory() as temp_dir:
                input_path = os.path.join(temp_dir, "input.mp4")
                output_path = os.path.join(temp_dir, "output_720p.mp4")

                with tracer.start_as_current_span("download_source") as dl_span:
                    blob.download_to_filename(input_path)
                    dl_span.set_attribute("gcs.bucket", bucket_name)
                    dl_span.set_attribute("gcs.blob", blob_name)
                    dl_span.set_attribute("file.size", file_size)

                # Real ffmpeg execution
                with tracer.start_as_current_span("ffmpeg_transcode") as transcode_span:
                    # ffmpeg -i input.mp4 -vf scale=-1:720 -c:v libx264 -preset fast -y output.mp4
                    cmd = [
                        "ffmpeg", "-i", input_path,
                        "-vf", "scale=-1:720",
                        "-c:v", "libx264", "-preset", "fast",
                        "-y", output_path
                    ]
                    
                    try:
                        # For async we should technically run this in a thread pool, but subprocess.run block is fine for this demo
                        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        if result.returncode != 0:
                            transcode_span.set_attribute("ffmpeg.error", result.stderr)
                            raise Exception(f"ffmpeg failed: {result.stderr}")
                    except Exception as e:
                        transcode_span.record_exception(e)
                        raise

                with tracer.start_as_current_span("upload_output") as ul_span:
                    encoded_blob_name = blob_name.rsplit('.', 1)[0] + "_720p.mp4"
                    encoded_blob = bucket.blob(encoded_blob_name)
                    encoded_blob.upload_from_filename(output_path, content_type="video/mp4")
                    ul_span.set_attribute("gcs.bucket", bucket_name)
                    ul_span.set_attribute("gcs.blob", encoded_blob_name)
                    encoded_gcs_uri = f"gs://{bucket_name}/{encoded_blob_name}"

            # Update Firestore with encoded state
            with tracer.start_as_current_span("update_firestore") as fs_span:
                doc_ref.update({
                    "status": "encoded",
                    "encoded_gcs_uri": encoded_gcs_uri,
                    "encoded_at": firestore.SERVER_TIMESTAMP
                })

            # Publish next event
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
            
    except Exception as e:
        span.record_exception(e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        active_encodes -= 1