# Build Plan — 4 weeks to submission

> Deadline: **June 11, 2026, 2:00 PM PDT**. Today: May 14, 2026. Net 28 days. Plan assumes ~25 hrs/week.
> Each week ends with a **demo-able milestone**. If a week slips, cut features — don't slip the deadline.

---

## Week 1 (May 14–20): Infrastructure foundation + first OTel trace

**Milestone**: Single asset moves from upload → Firestore → encode (stub) → done. Traces visible in Dynatrace. No agent yet.

### Day 1 (today)
- [ ] Create GCP project for hackathon, set `PROJECT_ID` env var globally
- [ ] Enable APIs: Cloud Run, Cloud Build, Firestore, Pub/Sub, Cloud Storage, Vertex AI, Secret Manager, Artifact Registry
- [ ] Sign up Dynatrace free trial; capture tenant URL and platform token
- [ ] Store Dynatrace token in Secret Manager (`dynatrace-token`)
- [ ] `gh repo create studioflow --public --license=apache-2.0`
- [ ] Commit this CLAUDE.md and build plan to repo

### Day 2
- [ ] Build `services/observability/tracer.py` — shared OTel setup: OTLP exporter pointed at Dynatrace, resource attrs (service.name, deployment.environment).
- [ ] Verify: a 5-line "hello world" script with the tracer produces a trace visible in Dynatrace UI. **Don't move on until you see it.**

### Day 3
- [ ] `services/ingest`: FastAPI app, `POST /assets` accepts multipart, writes to GCS bucket `studioflow-assets`, writes Firestore doc, publishes `asset.ingested` to Pub/Sub topic `studioflow-events`. Full OTel instrumentation.
- [ ] Dockerfile + cloudbuild.yaml. Deploy to Cloud Run. Smoke test with curl.

### Day 4
- [ ] `services/workflow`: state machine. Subscribes to `studioflow-events`. On `asset.ingested` → emit `asset.encoding_requested`. Firestore updates `asset.state`.
- [ ] Deploy. Verify by uploading via Day 3 endpoint and watching Firestore state transition.

### Day 5
- [ ] `services/encode` stub: subscribes to `asset.encoding_requested`, sleeps 3s, emits `asset.encoded`. No real ffmpeg yet.
- [ ] Verify end-to-end: upload an asset, watch all 3 services trace it through, see the full distributed trace in Dynatrace.

### Day 6–7 (weekend)
- [ ] Frontend skeleton (`frontend/`): Next.js, single page showing list of assets and their current state from Firestore (realtime listener).
- [ ] Buffer day for bugs.

**Week 1 demo to yourself**: upload a video, see it move through states in the UI, see the trace in Dynatrace. If this isn't working by Sunday night, scope down (drop frontend until Week 3).

---

## Week 2 (May 21–27): Make encode real + agent skeleton

**Milestone**: Real ffmpeg transcode runs. Scripted failure mode (`MEMORY_LEAK`) reliably triggers and is visible in Dynatrace as a Problem. Agent skeleton boots and successfully calls one Dynatrace MCP tool.

### Day 8
- [ ] `services/encode` real: ffmpeg subprocess, transcodes input to 720p H.264. Output to GCS. OTel span wraps the ffmpeg call.
- [ ] Failure mode `MEMORY_LEAK`: when file > 500MB AND concurrent jobs > 3, deliberately allocate a 2GB buffer and don't release. Cloud Run will OOM kill. Verify Dynatrace sees the OOM as a problem.

### Day 9
- [ ] `services/enrichment`: subscribes to `asset.encoded`, calls Vertex AI Gemini Flash for a 2-sentence description, writes back to Firestore. Emit `asset.enriched`.
- [ ] Workflow: on `asset.enriched` → state `published`. Done.

### Day 10
- [ ] `services/agent` skeleton: ADK Python project, `agent.py` with one tool (Dynatrace MCP via remote URL + bearer). Just verify it can list Dynatrace problems.
- [ ] Local dev only this day. No deploy yet.

### Day 11
- [ ] Add second agent tool: `pipeline_api.get_asset_state(asset_id)`. Read-only REST endpoint on the workflow service.
- [ ] System prompt v1 (see CLAUDE.md §8). Test: "what's broken in the pipeline?" — agent calls Dynatrace, summarizes.

### Day 12
- [ ] Third tool: `git_history.get_recent_deploys(service)`. Wrap `gh api` for deploy commit list. Read-only.
- [ ] Test the diagnosis loop manually: trigger MEMORY_LEAK in encode, ask agent "what's wrong with encode service?" Expect: identifies OOM, mentions recent commits.

### Day 13–14 (weekend)
- [ ] Build `scripts/chaos.sh`: one command that uploads 5 large assets and triggers MEMORY_LEAK reproducibly. This is the demo trigger.
- [ ] Buffer.

**Week 2 demo**: run chaos.sh, agent (from local Python REPL) correctly identifies which service failed and why. UI not required this week.

---

## Week 3 (May 28–Jun 3): Approval gates + UI + remediation

**Milestone**: Full demo path works locally end-to-end. Operator can approve a remediation; agent executes it. UI shows incident timeline.

### Day 15
- [ ] `HumanApprovalGate` tool: agent calls with a structured `RemediationPlan`. Tool writes to Firestore `approvals/{id}` with status `pending`, then long-polls (or uses Pub/Sub) for status change. Returns `approved`/`rejected` to agent.
- [ ] Frontend: approval queue page. Pending plans render as cards with approve/reject buttons.

### Day 16
- [ ] Remediation actions (whitelisted, idempotent):
  - `scale_service(service, memory_mb)` — Cloud Run revision update
  - `rollback_service(service, to_commit)` — redeploy previous Cloud Build
  - `retry_asset(asset_id)` — re-publish event
- [ ] Each wired through `pipeline_api` with audit log.

### Day 17
- [ ] Frontend: incident timeline view. For each Dynatrace problem, show: detected → agent diagnosing → plan proposed → approved/rejected → executed → resolved. Pull from Firestore + Dynatrace API.

### Day 18
- [ ] Agent prompt v2: tighten output to the `IncidentResponse` schema. Add evidence-citation requirement.
- [ ] End-to-end dry run: chaos.sh → agent diagnoses → UI shows plan → human approves → remediation runs → Dynatrace shows recovery. Time it. Should fit in 90 seconds.

### Day 19
- [ ] Deploy agent to Cloud Run (or Agent Runtime, depending on cost). Configure with production Dynatrace + Pipeline endpoints.
- [ ] Run full demo against production deployment.

### Day 20–21 (weekend)
- [ ] Frontend polish: design pass on the incident timeline + approval cards. (See `docs/design-notes.md` — not yet written.)
- [ ] Write `README.md`: setup, architecture diagram, demo instructions.

**Week 3 demo**: full hosted demo URL works. You can hand someone a link and they can watch chaos.sh trigger an incident and walk through the agent's reasoning.

---

## Week 4 (Jun 4–11): Polish, video, submission

**Code freeze: June 6 EOD.** After that, only bug fixes and demo polish.

### Day 22 (Jun 4)
- [ ] Final feature: agent's post-incident summary (auto-generated incident report in the timeline). Use Gemini Flash for this — cheap.

### Day 23 (Jun 5)
- [ ] Add a second failure mode to chaos.sh (`CODEC_PANIC`) for robustness. Verify agent handles it.
- [ ] Buffer for bugs.

### Day 24 (Jun 6) — CODE FREEZE
- [ ] Final end-to-end run. Lock the build. Tag `v1.0-submission`.

### Day 25 (Jun 7)
- [ ] Record demo video. Use the script in `docs/demo-script.md`. Multiple takes; ~3 min final.

### Day 26 (Jun 8)
- [ ] Video edit. Add captions for clarity (judges may watch muted).
- [ ] Upload to YouTube unlisted.

### Day 27 (Jun 9)
- [ ] Write Devpost submission: project description, what it does, how we built it, challenges, accomplishments, what's next.
- [ ] Submit early. **Do not wait for the deadline.**

### Day 28 (Jun 10)
- [ ] Reserved for emergencies.

### Jun 11 — deadline day
- [ ] Confirm submission status. Done.

---

## Risk register

| Risk | Mitigation |
|---|---|
| Dynatrace MCP remote server changes API mid-sprint | Pin a fork or local install as fallback |
| Gemini 3.1 Pro preview ends or pricing changes | Have Gemini Flash fallback path tested by Day 12 |
| ffmpeg in Cloud Run has cold-start issues | Use min-instances=1 for encode service during demo |
| Cloud Run cost overruns | Set hard quota; tear down between sessions |
| Demo video re-shoot needed | Build buffer is Days 26-28 — three full days |
| Apple JD reveals project doesn't fit | Once you paste the JD, we adjust the narrative, not the project (which already fits broadly) |

---

## What we are NOT doing (anti-scope)

- Multi-tenant auth — single demo user
- Real DRM, real rights mgmt — out of scope
- Multi-region deploys — single region (us-central1)
- Custom evaluation framework — Dynatrace's existing problem detection is enough
- A2A (agent-to-agent) protocol — single agent
- Mobile app — desktop browser only
