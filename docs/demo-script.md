# Demo script — 3-minute video

> CLAUDE.md §3 has the arc. This file holds the exact words and shot list.
> Final cut by June 6 EOD (Day 24). Recording sessions: Day 25.

## Shot list

| Time | Visual | Voiceover |
|------|--------|-----------|
| 0:00–0:10 | StudioFlow landing page, "Studio Control Room" header, list of assets at various stages | "StudioFlow is a simulated media production pipeline — the kind of system that moves an Apple TV show from raw upload to publish." |
| 0:10–0:20 | Drag-drop a 4K asset; watch it appear and move through ingest → encoding states in real time | "Each stage is a Cloud Run service, instrumented with OpenTelemetry, streaming traces into Dynatrace." |
| 0:20–0:30 | Run `scripts/chaos.sh` in a terminal overlay; latency dashboard in Dynatrace spikes; a red "Problem" banner appears | "Now we inject a real failure: the encode service starts OOM-killing under 4K concurrency." |
| 0:30–0:50 | Cut to the StudioFlow Agent card. Watch it call Dynatrace MCP tools in sequence; tool-call lines render live | "The agent picks up the Dynatrace problem. It pulls traces, queries entities, finds the failing service." |
| 0:50–1:30 | Agent's hypothesis card renders with cited trace IDs; correlated with the `enable-4k` commit from `git_history` | "Then it correlates the failure window with our recent deploy history — the `enable-4k` change. Each claim cites a trace ID. No hand-waving." |
| 1:30–2:00 | Remediation plan card slides up: "Rollback encode to commit abc123, scale memory 1→4Gi". An "Approve" button glows. | "Now the agent stops. It's drafted a remediation plan, but it will not execute without explicit human approval. This is the gate." |
| 2:00–2:20 | Click Approve. Status bar: rollback running → scale running → done | "One click. The agent executes the rollback, scales the service, and re-publishes failed assets." |
| 2:20–2:40 | Dynatrace panel: problem resolves; agent posts post-incident summary card | "Dynatrace confirms recovery. The agent writes the incident report and closes the loop." |
| 2:40–3:00 | StudioFlow logo, tagline | "Production media systems that operate themselves — under human control. StudioFlow." |

## Recording notes

- Two takes: one for voiceover-on-screen, one silent for B-roll.
- Captions mandatory — judges may watch muted.
- Browser zoom: 125%. Terminal font: 18pt.
- Hide all dock/menu-bar clutter; demo desktop is a fresh user.
- Record at 1440p; export 1080p H.264 for YouTube.

## Cuts (do not include even if tempting)

- Architecture diagrams: they belong in the Devpost write-up, not the video.
- "Built with ADK" callouts: judges already read the Devpost form for the stack.
- Multiple failure modes: pick MEMORY_LEAK, stop. Showing two = confusing.

