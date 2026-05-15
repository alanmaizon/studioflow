# Devpost submission — draft

Working copy for the Devpost submission form. Each section maps to a field on the Google Cloud Rapid Agent Hackathon submission page. Keep each section under the listed cap.

---

## Project name
StudioFlow Agent

## Tagline (≤ 200 chars)
A Gemini 3.1 Pro agent that diagnoses real Dynatrace incidents in a media production pipeline, then waits for a human to click Approve before remediating anything.

## Built with (tags)
gemini, vertex-ai, google-adk, dynatrace, mcp, cloud-run, firestore, pub-sub, opentelemetry, python, fastapi

## Track
Dynatrace

---

## Inspiration

The interesting AI agents in production aren't chat bots — they're SREs. They sit on top of observability data, form hypotheses, and propose actions. The Rapid Agent Hackathon's brief said it out loud: *"while keeping you in control."* That clause is where every demo I'd seen this year hand-waved.

So I built two systems on purpose: a simulated Apple-style media production pipeline (the kind of thing Apple TV Studio or Apple Music ops actually run — ingest → transcode → enrich → publish, event-driven, OTel-instrumented), and a Gemini agent that operates on it. The agent has to find real incidents through the Dynatrace MCP, cite real trace IDs, and stop dead at a human approval gate before any write action ships.

## What it does

StudioFlow Agent is an autonomous SRE copilot for a media pipeline. End to end:

1. The pipeline runs assets through ingest → workflow → encode (with a deliberately fragile MEMORY_LEAK path under high concurrency). Every service exports OpenTelemetry spans to Dynatrace.
2. When the encode service starts dropping requests, the agent — Gemini 3.1 Pro via Google ADK — pulls problems from Dynatrace through the official remote MCP server, runs DQL queries against Grail to find error spans with the `boom.oom_killed=true` attribute, and assembles a structured `IncidentResponse` with cited evidence (trace IDs, file size, concurrent encode count) and a proposed remediation plan.
3. Before executing anything, the agent submits the plan to `HumanApprovalGate` — a custom ADK tool that writes the plan to Firestore and blocks for up to 5 minutes waiting for a human to click Approve in the Studio Control Room UI.
4. On approval, the agent calls `scale_service` against a constrained "Pipeline API" on the workflow service. The action is validated against the approved plan, executed, and logged to a tamper-evident audit collection. The UI surfaces the audit entry as a toast.
5. The agent posts a post-incident summary referencing every trace ID, the operator who approved, and the audit log ID.

The whole loop is deployed on Cloud Run. The demo runs entirely against hosted infrastructure — no laptop in the loop.

## How we built it

**Five services on Cloud Run.** `ingest` (FastAPI multipart upload to GCS + Firestore), `workflow` (state-machine + admin/scale Pipeline API), `encode` (ffmpeg + scripted MEMORY_LEAK), `frontend` (FastAPI serving the Studio Control Room UI prototype + Firestore-backed JSON API), and `agent` (ADK `LlmAgent` wrapped in a FastAPI shim for a `POST /diagnose` HTTP entry point).

**The agent stack.** Gemini 3.1 Pro Preview reachable only on Vertex AI's `locations/global` endpoint (a non-obvious detail — `us-central1` returns 404 for the preview families even on a billed project). ADK's `LlmAgent` with three kinds of tools:

- `McpToolset(StreamableHTTPConnectionParams)` for Dynatrace MCP. Filtered to a 10-tool allowlist because three of Dynatrace's anomaly-detector tools ship MCP schemas that omit required `type` fields and crash Vertex's function-call validator.
- `FunctionTool(request_remediation_approval)` — a custom Python function that blocks on a Firestore poll.
- `FunctionTool(scale_service)` — a thin HTTP POST to the workflow service.

**Dynatrace observability has two token surfaces, which is easy to get wrong.** OTLP HTTP trace ingest on `.live.dynatrace.com` requires a *classic API token* (`dt0c01.*`) with the `openTelemetryTrace.ingest` scope. The MCP gateway on `.apps.dynatrace.com` requires a *Platform Token* (`dt0s.*`). Our `tracer.py` refuses to start if it sees a Platform Token under `DYNATRACE_API_TOKEN` and emits a loud error.

**The approval gate is the soul of the project.** A Cloud Run instance happily holds an HTTP connection open for 5 minutes while a background poll watches Firestore. When the operator clicks Approve, the tool returns the operator identity, decision note, and timestamp to the agent, which captures them in its post-incident summary. Reject and timeout are handled identically — the agent never executes without an explicit `approved` status.

## Challenges we ran into

- **Cloud Run circuit-breaker.** Hard-OOM'ing the encode container (the original MEMORY_LEAK design) put Cloud Run into a protective rate-limit that returned 429 at the load balancer for minutes, hiding the very signal Davis needed to see. We pivoted to telemetry-only OOM — record `boom.oom_killed=true` on a span, force-flush the tracer, raise a clean HTTP 500. Cloud Run sees a healthy service returning errors (within tolerance), Dynatrace sees the application-level signal, the agent reads it.
- **Async vs threadpool.** The encode handler was `async def` but every Google Cloud SDK call inside it is synchronous and blocks the event loop, serialising requests. The `active_encodes > 3` MEMORY_LEAK trigger could never fire because only one request was ever in flight on a container. Converting to `def` + Pydantic body parsing put FastAPI's threadpool back in charge and made the trigger reliable.
- **Gemini 3.x model access.** A fresh billed GCP project does not get Gemini 3.x access on regional endpoints; the call returns 404 with no actionable error message. We confirmed via Google's Cloud Assist that previews are gated to `locations/global`. CLAUDE.md §0 calls out the brain as `gemini-3.1-pro-preview` — we got there by setting `VERTEX_LOCATION=global` everywhere.
- **MCP tool schemas.** Several of Dynatrace's MCP tools ship parameters whose JSON schema omits the `type` field, which the Vertex function-calling validator rejects with HTTP 400. Filtering the toolset to ten schema-clean tools (`query-problems`, `execute-dql`, `create-dql`, `get-entity-id`, etc.) lets the agent run.
- **Span propagation timing.** When the MEMORY_LEAK path raised an HTTPException, the parent `encode_asset` span hadn't ended yet by the time the outer except tried to record on it. Restructuring to set attributes inside the `with` block, then force-flushing the tracer provider in the outer except, made the OOM breadcrumb land in Dynatrace consistently before the next chaos burst.

## Accomplishments we're proud of

- **The full demo arc runs end-to-end against hosted infrastructure** with no laptop in the loop. Chaos → Dynatrace problem → Pro 3.1 diagnosis with cited trace IDs → operator clicks Approve in the deployed UI → `scale_service` executes against a constrained `/admin/scale` endpoint → audit log entry appears in the UI. ~50 seconds when Pro 3.1 reasons through it.
- **Auditability** is not a slide. Every remediation gets a Firestore `audit_log/{id}` with the approval ID, the executing service, the operator, the params, and an "intentionally simulated" flag for actions that are gated by a stronger IAM boundary we haven't crossed.
- **The agent's `IncidentResponse` is structured JSON** — `hypothesis`, `confidence`, `evidence: [{source, id, what_it_shows}]`, `proposed_actions` — and the UI renders the same shape the agent emits.
- **The pipeline is a real distributed system**, not a stub. Pub/Sub fan-out between services, OpenTelemetry spans across the three hops, real ffmpeg in the encode container, real Firestore state transitions.

## What we learned

- **Auditability comes for free once you've got a real boundary.** The constraint that the agent has to go through HTTP POST to a separate service for any write action means the audit log writes itself.
- **Cloud Run is happy to host long-blocking requests** as long as you bump the timeout, which lets a single synchronous `POST /diagnose` endpoint span the entire agent lifecycle including the 5-minute approval window. No queue, no session store, no Pub/Sub round-trip needed.
- **OpenTelemetry's "BatchSpanProcessor" is dangerous near failure paths.** If your container is going to die or return fast, the breadcrumb spans you carefully set just don't ship. Force-flushing at the moment of error capture is the difference between "the agent has evidence" and "the agent can't see what happened."
- **MCP plus Gemini surfaces real schema bugs in tool servers.** The schema strictness Vertex enforces caught three actual issues in the Dynatrace MCP. That's a feature.

## What's next for StudioFlow Agent

- **Wire `rollback` and `retry-asset`** as Pipeline API actions. The agent already proposes them in `proposed_actions`; today only `scale` is wired.
- **Real Cloud Run mutation** behind `/admin/scale`. The endpoint structure is in place; swapping the simulated audit entry for a real `google-cloud-run` revision update is a self-contained change. The IAM grant (`roles/run.developer` on workflow's SA) is the only delta.
- **Live tool-call stream in the UI.** The Studio Control Room prototype has a tool-stream component; right now it's scripted. Plumbing it to the agent's emitted tool calls via Server-Sent Events would let an operator watch the agent think in real time.
- **More incident types.** SLOW_TRANSCODE and CODEC_PANIC are sketched in [CLAUDE.md §7](https://github.com/alanmaizon/studioflow/blob/main/CLAUDE.md). Adding them would test the agent's ability to differentiate failure modes rather than just recognise the one it's been shown.

---

## Demo video script
See [docs/demo-script.md](https://github.com/alanmaizon/studioflow/blob/main/docs/demo-script.md). Three minutes, shot list locked, captioned for muted viewing.

## Source code
[https://github.com/alanmaizon/studioflow](https://github.com/alanmaizon/studioflow) — Apache 2.0 licensed.

## Hosted URL
https://frontend-service-vb6z2eah4a-uc.a.run.app
