import os
import json
import base64
import time
import threading
import tempfile
import subprocess
import logging
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

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

# Concurrency counter for the scripted MEMORY_LEAK trigger condition.
# Shared across threads (sync handler under FastAPI's threadpool) — a Lock keeps
# read-modify-write ordered so the threshold check is consistent.
active_encodes = 0
_active_encodes_lock = threading.Lock()


class PubSubMessage(BaseModel):
    """Pub/Sub HTTP push envelope. We only care about message.data; the SDK fills the rest."""
    message: dict[str, Any]


@app.get("/health")
def health_check():
    return {"status": "ok", "active_encodes": active_encodes}


# NOTE: sync `def` is intentional. FastAPI runs sync routes on a threadpool, so
# concurrent Pub/Sub pushes execute in parallel threads sharing `active_encodes`.
# An `async def` here would block the event loop on every GCS / ffmpeg call and
# serialise requests, making `active_encodes > 3` impossible to reach.
@app.post("/pubsub/push")
def handle_pubsub_message(envelope: PubSubMessage):
    global active_encodes

    message = envelope.message
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

    with _active_encodes_lock:
        active_encodes += 1
        joined_at = active_encodes
    logger.info("ENC enter: asset=%s joined_at=%d", asset_id, joined_at)
    try:
        with tracer.start_as_current_span("encode_asset") as span:
            span.set_attribute("asset.id", asset_id)
            span.set_attribute("event.type", event_type)
            span.set_attribute("encode.active_encodes_at_start", joined_at)

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
            # DELIBERATE FAILURE MODE: MEMORY_LEAK (telemetry-only)
            # ---------------------------------------------------------
            # Trigger: file > 500MB and concurrent > 3.
            # Records OOM-style telemetry and returns a clean HTTP 500. We do
            # NOT actually allocate the 2GB buffer because hard OOMs put
            # Cloud Run into a circuit-breaker state that throttles the LB,
            # which masks the very signal Davis needs to see. With clean 500s,
            # Dynatrace records error spans normally and Davis detects the
            # error-rate anomaly. The agent uses the boom.oom_killed=true
            # attribute as evidence.
            # Read the LIVE counter (not the stale joined_at snapshot) so we see
            # the wave of concurrent threads that joined after us.
            # CPython int reads are atomic; no lock needed for a read.
            live_active = active_encodes
            logger.info(
                "ENC threshold-check: asset=%s file_size=%d joined_at=%d live_active=%d",
                asset_id, file_size, joined_at, live_active,
            )
            if file_size > (500 * 1024 * 1024) and live_active > 1:
                span.set_attribute("boom.oom_killed", True)
                span.set_attribute("boom.reason", "MEMORY_LEAK_scripted")
                span.set_attribute("encode.file_size_bytes", file_size)
                span.set_attribute("encode.active_encodes", live_active)
                span.set_attribute("encode.simulated_allocation_bytes", 2 * 1024 * 1024 * 1024)
                span.set_status(Status(StatusCode.ERROR, "MEMORY_LEAK triggered"))
                logger.warning(
                    "MEMORY_LEAK triggered: asset=%s file_size=%d active=%d",
                    asset_id, file_size, live_active,
                )
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Encode service exhausted memory while transcoding 4K source "
                        "under high concurrency (MEMORY_LEAK)"
                    ),
                )
            
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
            
    except HTTPException as exc:
        # MEMORY_LEAK reaches here. Span has ended (with-block exited) and is
        # queued for export — force flush so the breadcrumb lands in Dynatrace
        # before the agent queries.
        if "MEMORY_LEAK" in str(exc.detail):
            try:
                trace.get_tracer_provider().force_flush(timeout_millis=3000)
            except Exception:  # noqa: BLE001
                pass
        raise
    except Exception as e:
        # Unexpected. FastAPI's instrumentation will record this on the
        # request span; we don't touch the (already-ended) encode_asset span.
        logger.exception("encode_asset failed unexpectedly")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        with _active_encodes_lock:
            active_encodes -= 1