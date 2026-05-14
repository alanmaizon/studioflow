import os
import uuid
import time
import json
from fastapi import FastAPI, File, UploadFile, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

from google.cloud import storage
from google.cloud import firestore
from google.cloud import pubsub_v1

# Import out OTel tracer
from observability.tracer import init_tracer

app = FastAPI(title="StudioFlow Ingest Service")

# Initialize OTel Tracer
init_tracer("studioflow-ingest")
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer(__name__)

# Initialize GCP clients
project_id = os.environ.get("PROJECT_ID")
gcs_bucket = os.environ.get("GCS_BUCKET", f"{project_id}-assets")
pubsub_topic = os.environ.get("PUBSUB_TOPIC", "studioflow-events")

# Try to initialize clients, but fail gracefully if not in GCP env
storage_client = storage.Client(project=project_id)
firestore_client = firestore.Client(project=project_id)
pubsub_publisher = pubsub_v1.PublisherClient()
topic_path = pubsub_publisher.topic_path(project_id, pubsub_topic) if project_id else ""

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/assets")
async def ingest_asset(file: UploadFile = File(...)):
    asset_id = str(uuid.uuid4())
    
    with tracer.start_as_current_span("ingest_asset") as span:
        span.set_attribute("asset.id", asset_id)
        span.set_attribute("asset.filename", file.filename)
        
        try:
            # 1. Upload to GCS
            with tracer.start_as_current_span("upload_to_gcs") as gcs_span:
                bucket = storage_client.bucket(gcs_bucket)
                blob = bucket.blob(f"{asset_id}/{file.filename}")
                blob.upload_from_file(file.file, content_type=file.content_type)
                gcs_span.set_attribute("gcs.bucket", gcs_bucket)
                gcs_span.set_attribute("gcs.blob", blob.name)
            
            # 2. Write to Firestore
            with tracer.start_as_current_span("write_to_firestore") as fs_span:
                doc_ref = firestore_client.collection("assets").document(asset_id)
                asset_data = {
                    "id": asset_id,
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "status": "ingested",
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "gcs_uri": f"gs://{gcs_bucket}/{blob.name}"
                }
                doc_ref.set(asset_data)
                fs_span.set_attribute("firestore.collection", "assets")
                fs_span.set_attribute("firestore.document", asset_id)
                
            # 3. Publish Event
            with tracer.start_as_current_span("publish_event") as ps_span:
                event_data = {
                    "event_type": "asset.ingested",
                    "asset_id": asset_id,
                    "timestamp": time.time()
                }
                data_bytes = json.dumps(event_data).encode("utf-8")
                future = pubsub_publisher.publish(topic_path, data=data_bytes)
                future.result() # Wait for publish to complete
                ps_span.set_attribute("pubsub.topic", pubsub_topic)
                
            span.set_attribute("ingest.status", "success")
            return {"asset_id": asset_id, "status": "ingested"}
            
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("ingest.status", "failed")
            raise HTTPException(status_code=500, detail=str(e))
