#!/bin/bash
set -e

echo "Generating large dummy file (505MB)..."
dd if=/dev/zero of=chaos_dummy.mp4 bs=1M count=505

PROJECT_ID=$(gcloud config get-value project)
BUCKET="${PROJECT_ID}-assets"

echo "Uploading directly to GCS to avoid 32MB Cloud Run request limit..."
gcloud storage cp chaos_dummy.mp4 gs://${BUCKET}/chaos/chaos_dummy.mp4

ASSET_ID="chaos-$(uuidgen | tr 'A-Z' 'a-z')"

echo "Creating Firestore document for $ASSET_ID..."
cat << JS > fs_payload.json
{
  "fields": {
    "id": {"stringValue": "$ASSET_ID"},
    "status": {"stringValue": "encoding"},
    "gcs_uri": {"stringValue": "gs://${BUCKET}/chaos/chaos_dummy.mp4"}
  }
}
JS
curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d @fs_payload.json \
  "https://firestore.googleapis.com/v1/projects/$PROJECT_ID/databases/(default)/documents/assets?documentId=$ASSET_ID" \
  > /dev/null

echo "Publishing 4 concurrent encoding requests to trigger MEMORY_LEAK..."
EVENT_MSG="{\"event_type\": \"asset.encoding_requested\", \"asset_id\": \"$ASSET_ID\"}"

for i in {1..7}; do
  gcloud pubsub topics publish studioflow-events --message="$EVENT_MSG" &
done
wait

echo "Chaos unleashed. Check Dynatrace."
rm chaos_dummy.mp4 fs_payload.json
