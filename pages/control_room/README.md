# Studio Control Room — UI kit

A pixel-faithful, click-thru recreation of the StudioFlow control room: the operator's view onto the media pipeline (ingest → transcode → enrichment → publish) and the AI agent that diagnoses incidents in it.

This is **not** production code. It's a high-fidelity mock that ships the visual vocabulary the design system specifies, in a working flow you can click through.

## What's interactive

Open `index.html`. The prototype starts in a **healthy** steady state. From the top bar:

1. Click **"Run chaos"** — fakes a deploy of `enable-4k`, then watches the encode service start failing under 4K concurrency. A red incident pill lights up the sidebar, an asset turns red in the table.
2. The **StudioFlow Agent** picks up the Dynatrace problem and starts streaming tool calls in the right inspector. After ~6 seconds it posts a structured remediation plan.
3. An **approval gate** sheet slides up — "rollback to `abc123`, scale memory 1 → 4 GiB". Click **Approve** (or press ⌘↵).
4. The actions run; service health returns to green; the agent posts an incident summary.

You can also click an asset in the table to open its inspector panel.

## Files

- `index.html` — entry. Loads React + Babel, all components, mounts `<App />`.
- `App.jsx` — top-level layout + state machine (`healthy` / `incident-detected` / `agent-diagnosing` / `awaiting-approval` / `remediating` / `recovered`).
- `TopBar.jsx` — sticky glass top bar with search, environment chip, user.
- `Sidebar.jsx` — left nav with the four pipeline stages and the agent entry.
- `PipelineSummary.jsx` — the stage tiles row at the top of Overview.
- `AssetTable.jsx` + `AssetRow.jsx` — the main pipeline asset list.
- `Inspector.jsx` — right panel: agent stream when an incident is active, otherwise selected-asset detail.
- `IncidentCard.jsx` — the agent's structured hypothesis card with evidence.
- `ToolStream.jsx` — live tool-call log.
- `ApprovalGate.jsx` — bottom sheet for confirming a proposed remediation.
- `Toast.jsx` — bottom-right toast stack.
- `ui.jsx` — primitives: `Button`, `StatusPill`, `Dot`, `Pill`, `Icon`, `GlassPanel`.
- `data.js` — fixture data (services, assets, agent script).

## What this kit deliberately omits

- Auth, multi-tenancy, real Dynatrace MCP calls — all faked.
- Charts beyond the inline sparkline shown in stage tiles.
- Settings, account screens.
- Mobile layout.

These were out of scope for the demo arc the upstream repo describes (see `CLAUDE.md` §3 of <https://github.com/alanmaizon/studioflow>).
