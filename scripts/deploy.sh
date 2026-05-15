#!/usr/bin/env bash
# Build + deploy one or more StudioFlow services to Cloud Run via Cloud Build.
#
# Usage:
#   scripts/deploy.sh ingest
#   scripts/deploy.sh workflow
#   scripts/deploy.sh encode
#   scripts/deploy.sh all
#
# Sources .env automatically. Pass COMMIT_SHA + all _SUBSTITUTIONS the
# cloudbuild.yamls reference so `gcloud builds submit` works from local.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Source .env so PROJECT_ID, REGION, etc. are available.
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${PROJECT_ID:?PROJECT_ID not set (check .env)}"
: "${REGION:?REGION not set (check .env)}"

REPO="${ARTIFACT_REGISTRY_REPO:-studioflow}"
BUCKET="${GCS_BUCKET:-${PROJECT_ID}-assets}"
TOPIC="${PUBSUB_TOPIC:-studioflow-events}"
SHA="$(git rev-parse --short HEAD)"

SHARED_SUBS="COMMIT_SHA=${SHA},_REGION=${REGION},_REPO=${REPO},_PUBSUB_TOPIC=${TOPIC}"
INGEST_SUBS="${SHARED_SUBS},_GCS_BUCKET=${BUCKET}"

deploy_one() {
  local service="$1"
  local subs="$SHARED_SUBS"
  [[ "$service" == "ingest" ]] && subs="$INGEST_SUBS"

  echo
  echo "=== deploying $service (SHA=$SHA) ==="
  gcloud builds submit \
    --project="$PROJECT_ID" \
    --config="services/${service}/cloudbuild.yaml" \
    --substitutions="$subs"
}

case "${1:-}" in
  ingest|workflow|encode|frontend)
    deploy_one "$1"
    ;;
  all)
    deploy_one ingest
    deploy_one workflow
    deploy_one encode
    deploy_one frontend
    ;;
  *)
    echo "Usage: $0 {ingest|workflow|encode|frontend|all}" >&2
    exit 2
    ;;
esac

echo
echo "✅ Deploy complete. Service URLs:"
for svc in ingest workflow encode frontend; do
  url=$(gcloud run services describe "${svc}-service" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)' 2>/dev/null || echo "(not deployed)")
  printf "  %-10s %s\n" "$svc:" "$url"
done
