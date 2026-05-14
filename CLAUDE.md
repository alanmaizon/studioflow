# CLAUDE.md — StudioFlow Agent

> This file is the contract between you (Claude Code / VSCode extension / any agent) and this project. Read it first, every session. When in doubt, prefer **what's in this file** over assumptions from training data.

---

## 0. The non-negotiables (read this twice)

1. **Hackathon deadline: June 11, 2026, 2:00 PM PDT** (~21:00 UTC). Submission to Google Cloud Rapid Agent Hackathon — **Dynatrace track**.
2. **Required stack** (these are submission requirements, not preferences):
   - Brain: **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) via Vertex AI / Gemini Enterprise Agent Platform. NOT gemini-3-pro-preview (discontinued March 26, 2026).
   - Framework: **Google ADK (Agent Development Kit)** — Python, open-source, the way to build agents on Agent Platform.
   - Partner MCP: **Dynatrace Remote MCP Server** (`https://{tenant}.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp`). Bearer token auth.
   - Deploy target: **Cloud Run** (for the simulated services and the agent runtime).
3. **Submission deliverables**: hosted URL, public open-source repo with license file detectable at top of repo, ~3 min demo video, Devpost form.
4. **Judging criteria, weighted equally**: Tech Implementation, Design, Potential Impact, Idea Quality.

If a change you're about to make conflicts with any of the above, **stop and surface the conflict** rather than silently working around it.

---

## 1. What we're building, in one paragraph

**StudioFlow** is a simulated Apple-style media production pipeline (ingest → transcode → enrichment → review → publish) running as event-driven microservices on Cloud Run, fully instrumented with OpenTelemetry exporting to Dynatrace. On top sits **StudioFlow Agent**: a Gemini 3.1 Pro agent built with ADK that uses the **Dynatrace MCP server** as its primary tool to autonomously detect, diagnose, root-cause, and propose remediation for pipeline incidents — under human approval gates. The pipeline is the substrate; the agent is the product.

---

## 2. Why this shape (the strategic frame)

This project must win on **two** fronts at once. Don't optimize for one and lose the other.

### Front A — win the Dynatrace track ($5k/$3k/$2k)
- Judges are Dynatrace solution architects + Google partner engineers.
- "Quality of Idea" criterion: an agent that *reasons over observability data* is the demo Dynatrace wrote their sponsor blurb to attract. Other entries will use Dynatrace as a passive sink for traces. We use it as the agent's eyes.
- "Tech Implementation": every Dynatrace MCP tool call must look intentional. We log which tools the agent picks and why.
- "Design": human approval gates ("keep you in control" is the hackathon's literal language). Clean incident timeline UI.
- "Potential Impact": AIOps / SRE automation is a real market, not a toy.

### Front B — Apple Services Technology application
- Apple TV Studio + Music ops = media pipelines + production reliability.
- The pipeline subsystem (Section 7) demonstrates: distributed systems, event-driven architecture, state machines, retries, observability, full-stack delivery. These are the signals the role requires.
- The agent on top demonstrates current AI fluency layered on top of solid production engineering — which is the differentiator vs candidates who only have one or the other.
- In interview: lead with the pipeline (system design), then reveal the agent (innovation). The story is "I built the production system AND the automation on top of it."

---

## 3. The story arc (this is what the demo video must show)

A 3-minute video, in this order:

1. **0:00–0:20** — "StudioFlow: a simulated Apple-style media production pipeline." Show a video asset being uploaded, traversing ingest → transcode → enrichment → review → publish. Mention OTel + Dynatrace.
2. **0:20–0:40** — Inject failure: transcode service starts dropping frames at high concurrency. Dynatrace surfaces a problem.
3. **0:40–2:20** — Hand off to the **StudioFlow Agent**. Show it (a) querying Dynatrace via MCP for the failing service, (b) pulling traces, (c) correlating with recent deploys, (d) identifying root cause (e.g. memory pressure during 4K transcodes), (e) drafting a remediation plan, (f) **stopping at the approval gate**.
4. **2:20–2:50** — Operator approves; agent executes remediation (scale up + rollback bad commit), Dynatrace shows recovery, agent posts post-incident summary.
5. **2:50–3:00** — One-line summary: "Production media systems that operate themselves, under human control."

Everything we build serves this video. If a feature doesn't appear in this story, it's cut.

---

## 4. Architecture (concrete)

```
                  ┌──────────────────────────────────────┐
                  │     Frontend: Studio Control Room    │
                  │  (Next.js on Cloud Run, served via   │
                  │   Cloud Run domain mapping)          │
                  └──────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  StudioFlow Pipeline (Cloud Run)             │
│                                                              │
│   Ingest ──Pub/Sub──> Workflow ──Pub/Sub──> Encode           │
│      │                   │                     │             │
│      ▼                   ▼                     ▼             │
│   Firestore           Firestore             Cloud Storage   │
│      ▲                   ▲                                   │
│      │                   │                                   │
│      └────── Enrichment ◀┘ (Vertex AI tagging)              │
│                                                              │
│   All services: OpenTelemetry SDK → OTLP exporter ──────────┼──> Dynatrace
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ MCP (HTTPS bearer)
                              │
┌─────────────────────────────────────────────────────────────┐
│         StudioFlow Agent (ADK on Agent Runtime)              │
│                                                              │
│   Gemini 3.1 Pro (thinking_level: high)                     │
│      │                                                       │
│      ├── Tool: Dynatrace MCP (primary — incident, traces)   │
│      ├── Tool: Pipeline API (read state, propose actions)   │
│      ├── Tool: Git history (gh CLI wrapped) — find bad deploy│
│      └── Tool: HumanApprovalGate (blocks until UI approves) │
└─────────────────────────────────────────────────────────────┘
```

### Service contracts (don't drift from these)

- **Ingest service** (`services/ingest`, Python FastAPI). Receives multipart upload, writes to GCS, writes asset record to Firestore, publishes `asset.ingested` event. SLO: p99 < 2s.
- **Workflow service** (`services/workflow`, Python FastAPI). State machine: `ingested → encoding → enriching → review → published | failed`. Subscribes to all `asset.*` events; emits next-stage events.
- **Encode service** (`services/encode`, Python + ffmpeg). Subscribes to `asset.encoding_requested`. **This is the service we will deliberately make fragile** (the agent's whipping boy). It will fail under specific scripted conditions: high concurrency, files > 500MB, certain codecs. Real ffmpeg, real failures, real traces.
- **Enrichment service** (`services/enrichment`, Python). Calls Vertex AI for auto-tagging (scene classification, transcript summary). Subscribes to `asset.encoded`.
- **Observability layer**: each service uses `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-requests`, `opentelemetry-sdk` with OTLP exporter to Dynatrace.
- **Agent** (`services/agent`, ADK Python). Long-running. Exposed via Agent Runtime or a thin FastAPI shim for the frontend.

---

## 5. Repo layout

```
studioflow/
├── CLAUDE.md                    ← this file
├── LICENSE                      ← Apache 2.0 (required for hackathon)
├── README.md                    ← user-facing; written LAST
├── docs/
│   ├── architecture.md          ← detailed design decisions
│   ├── apple-narrative.md       ← interview talking points
│   └── demo-script.md           ← exact words for the 3-min video
├── services/
│   ├── ingest/
│   ├── workflow/
│   ├── encode/
│   ├── enrichment/
│   ├── observability/           ← shared OTel setup module
│   └── agent/                   ← the ADK agent
├── infra/
│   ├── terraform/               ← GCP resources (Pub/Sub, Firestore, etc.)
│   └── cloudbuild/              ← per-service Dockerfile + cloudbuild.yaml
├── frontend/                    ← Studio Control Room (Next.js)
└── scripts/
    ├── seed.sh                  ← load demo assets
    └── chaos.sh                 ← trigger the scripted incident for the demo
```

---

## 6. Coding conventions

- **Python**: 3.12. `ruff` for lint, `black` for format (line length 100), `mypy --strict` where tractable. `uv` for env mgmt.
- **JavaScript**: Next.js 15, TypeScript strict, Tailwind v4.
- **Commit style**: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`). Branch per service.
- **Never commit**: `.env`, service-account JSON keys, Dynatrace tokens, anything in `secrets/`. Use Secret Manager.
- **Every service** must have: `Dockerfile`, `cloudbuild.yaml`, `requirements.txt` (or `pyproject.toml`), and a `/health` endpoint returning 200.
- **Every external call** must be wrapped in an OTel span. The traces ARE the demo.

---

## 7. The "deliberately fragile" encode service

The agent needs real incidents to diagnose. We script them in. Three failure modes, gated by env vars or query params for the demo:

| Mode | Trigger | What it looks like in Dynatrace |
|---|---|---|
| `MEMORY_LEAK` | files > 500MB, concurrent > 3 | RSS climbs, eventually OOM kill, span errors with `oom_killed=true` |
| `CODEC_PANIC` | input contains `prores` | ffmpeg exits non-zero, span exception type `CodecNotSupportedError` |
| `SLOW_TRANSCODE` | env `THROTTLE=1` | duration p99 climbs from 5s to 60s, Dynatrace flags latency anomaly |

The demo uses `MEMORY_LEAK`. The agent is expected to (1) identify the failing service, (2) read traces showing OOM, (3) correlate with the recent `enable-4k` commit, (4) propose: rollback + scale up memory.

---

## 8. Agent design (ADK)

### Tools the agent has access to

1. **Dynatrace MCP** (remote, HTTPS bearer) — primary. Use the official `dynatrace-mcp` tools: list problems, get problem details, fetch entities, run DQL queries, get traces for a service.
2. **Pipeline API** — internal REST endpoint exposing pipeline state and a constrained set of remediation actions (`scale`, `rollback`, `retry-asset`). All write actions require approval.
3. **Git history** — wraps `gh` CLI for `gh api` deploy history queries. Read-only.
4. **HumanApprovalGate** — the agent calls this tool with a structured remediation plan; the call blocks (via Pub/Sub round-trip) until the operator clicks approve/reject in the UI. **This tool is the soul of the project — the hackathon brief says "while keeping you in control".**

### Prompt structure (high-level — full prompt lives in `services/agent/prompts/`)

- **Persona**: "You are StudioFlow Agent, an SRE copilot for a media production pipeline."
- **Operating rules**: "(1) Diagnose before acting. (2) Cite evidence — every claim references a Dynatrace trace ID or DQL result. (3) Never call a write action without going through `HumanApprovalGate` first. (4) If uncertain, ask. (5) Be concise — operators read these at 3am."
- **Thinking level**: `high` for diagnosis, `low` for status summaries (cost optimization).

### Output schema
Every agent decision emits a structured `IncidentResponse` JSON: `{problem_id, hypothesis, evidence: [], proposed_actions: [], confidence}`. The frontend renders this as an incident card.

---

## 9. Working with this codebase (rules for any agent editing it)

1. **One service at a time.** Don't refactor across services in a single session unless explicitly asked.
2. **Read before writing.** Before modifying a service, `cat services/<name>/main.py` (or equivalent). Code may have drifted from this doc — the code is truth, this doc is intent.
3. **OTel everywhere.** Any new function that does I/O gets a span. No exceptions. Use the `observability/tracer.py` helpers.
4. **Don't hide errors.** Surface exceptions to spans; don't except-and-log-silent. The agent needs them.
5. **Demo path is sacred.** The exact upload → fail → diagnose → remediate flow in `scripts/chaos.sh` must work end-to-end before any new feature is merged.
6. **Cost vigilance.** Gemini 3.1 Pro is not cheap. Default to `gemini-3-flash` for sub-tasks; reserve Pro for the main reasoning loop. Cap agent context. Dynatrace DQL queries scan billable GB — keep timeframes tight (≤ 1h).
7. **Hackathon scope = freeze.** After June 6, no new features. Only bug fixes and demo polish. Cut, don't add.

---

## 10. Definition of done (per week)

See `docs/build-plan.md` for the week-by-week breakdown. At any moment, ask: **does this work serve the 3-minute demo script in Section 3?** If no, defer it.

---

## 11. What this project is NOT

- Not a real production system. (No multi-tenancy, no auth beyond demo, no real DRM.)
- Not a generic agent framework. (One use case: SRE for our pipeline.)
- Not a chatbot. The agent acts; it doesn't converse. UI shows decisions and gates, not chat bubbles.
- Not a Dynatrace replacement. We use Dynatrace; we don't reinvent it.

---

## 12. Open questions for the human (Carlos)

These are tracked here until resolved; agents should not silently decide them:

- [x] Dynatrace tenant URL and bearer token: tenant `mde08902.apps.dynatrace.com`. Platform Token generation in progress; will live in Secret Manager as `dynatrace-token`.
- [ ] Apple JD full text: paste into `docs/apple-narrative.md` so the interview prep is grounded in the actual JD, not the recruiter blurb.
- [x] GCP project ID for the hackathon: `project-87d15b7f-7332-458c-a73`, region `us-central1`. Captured in `.env` (gitignored); template in `.env.example`.
- [ ] Domain for the hosted demo URL: Cloud Run default or custom?
- [ ] Will you record the demo video yourself or do we need to script a screen-recording walk-through?
