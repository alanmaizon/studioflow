# Day 1 — Today (May 14)

Goal: leave today with a GCP project provisioned, a Dynatrace tenant ready, and an empty repo with this doc tree committed. No code yet.

## 1. GCP project (15 min)

```bash
# Pick a project ID. Suggestion: studioflow-{your-initials}-{random4}
export PROJECT_ID="studioflow-cl-XXXX"
export REGION="us-central1"
export BILLING_ACCOUNT="$(gcloud beta billing accounts list --format='value(name)' --limit=1)"

gcloud projects create $PROJECT_ID --name="StudioFlow"
gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Enable all APIs we'll need this month, in one shot
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudresourcemanager.googleapis.com

# Firestore (Native mode)
gcloud firestore databases create --location=$REGION

# Pub/Sub topic
gcloud pubsub topics create studioflow-events

# GCS bucket for assets
gsutil mb -l $REGION gs://${PROJECT_ID}-assets

# Artifact Registry for container images
gcloud artifacts repositories create studioflow \
  --repository-format=docker \
  --location=$REGION
```

**Save somewhere safe**: `PROJECT_ID`, `REGION`, billing alert threshold ($50 recommended for the month).

```bash
# Budget alert — don't skip this
gcloud billing budgets create --billing-account=$BILLING_ACCOUNT \
  --display-name="StudioFlow Hackathon" \
  --budget-amount=100USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 || true
# (gcloud's budgets API is finicky; fall back to console if this fails.)
```

## 2. Dynatrace (10 min)

1. Sign up: https://www.dynatrace.com/signup/ — free trial, 15 days, no credit card.
2. **Capture the tenant URL** — it looks like `https://abc12345.apps.dynatrace.com`. Note: must be `.apps.dynatrace.com`, NOT `.live.dynatrace.com` (the MCP server requires the new platform).
3. Generate a **Platform Token** (Settings → Access Tokens → Platform Tokens → Generate). Scopes needed:
   - `app-engine:apps:run`
   - `storage:logs:read`
   - `storage:events:read`
   - `storage:bizevents:read`
   - `storage:spans:read`
   - `storage:metrics:read`
   - `storage:entities:read`
   - `storage:problems:read`
   - `environment:roles:viewer`
4. Test the MCP endpoint with curl:

```bash
export DT_TENANT="https://abc12345.apps.dynatrace.com"
export DT_TOKEN="dt0s..."  # paste the platform token

curl -s -H "Authorization: Bearer $DT_TOKEN" \
  "${DT_TENANT}/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp" \
  -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | head -100
```

You want to see a JSON response listing tools. If you get 401, the token scopes are wrong.

## 3. Store the Dynatrace token in GCP (5 min)

```bash
echo -n "$DT_TOKEN" | gcloud secrets create dynatrace-token --data-file=-
echo -n "$DT_TENANT" | gcloud secrets create dynatrace-tenant --data-file=-
```

## 4. Create the repo (10 min)

```bash
cd ~/code  # or wherever
gh repo create studioflow --public --license=apache-2.0 --clone
cd studioflow

# Copy the CLAUDE.md and docs from /home/claude/studioflow into this repo
# (Or recreate from this Claude conversation.)

git add CLAUDE.md docs/
git commit -m "docs: project foundation — CLAUDE.md, build plan, day-1 checklist"
git push
```

## 5. Final check before stopping for the day

You should now have:

- [ ] A GCP project with billing enabled and APIs turned on
- [ ] A Firestore database
- [ ] A Pub/Sub topic
- [ ] A GCS bucket
- [ ] An Artifact Registry repo
- [ ] A Dynatrace tenant with a working platform token
- [ ] Both stored in Secret Manager
- [ ] A public GitHub repo with `CLAUDE.md`, `docs/build-plan.md`, this checklist, and an Apache-2.0 LICENSE file detectable at the top of the repo (required by hackathon rules)

If any of these is incomplete, **don't move to Day 2 tomorrow** — finish the gaps first. The whole stack rests on these.

## What NOT to do today

- Don't write service code yet
- Don't set up the frontend
- Don't start the agent
- Don't optimize anything

Day 1 is foundation. Discipline today saves panic in Week 4.
