# Architecture

> Detailed design decisions. CLAUDE.md §4 holds the canonical block diagram; this file holds the rationale.

## Status

Stub — populate as decisions are made. Each section answers a question; if it can't, delete it.

## Event flow

Why Pub/Sub over Cloud Tasks: each service publishes one event, multiple subscribers can fan out (e.g. agent will eventually subscribe to `asset.failed` for proactive triage). Cloud Tasks is point-to-point; Pub/Sub is the right shape.

## State machine ownership

The workflow service owns `asset.state` in Firestore. No other service writes that field. This keeps the state transition graph in one place and makes it the only thing the agent has to model.

## Why Firestore (not Cloud SQL)

Realtime listeners power the frontend's live state updates with zero polling code. The state machine doesn't need joins. Cost at demo scale is rounding error.

## OTel resource attributes

Every service sets: `service.name`, `service.version` (git short SHA), `deployment.environment` (`demo`). These are what Dynatrace uses to group spans into services on the Smartscape — without them the agent can't ask "what's wrong with the encode service" by name.

## Decisions deferred until needed

- Cloud Run vs. Agent Runtime for the agent host: pick at Week 2 Day 10 when we know the agent's resource profile.
- Frontend auth: none for demo; revisit only if a judge raises it.
