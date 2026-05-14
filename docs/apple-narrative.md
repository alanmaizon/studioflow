# Apple Services Technology — interview narrative

> CLAUDE.md §2 Front B. This file is the talking-points doc for the Apple interview, grounded in the actual JD once pasted in.

## JD (paste full text here)

```
TODO: paste Apple Services Technology JD verbatim. Keep formatting.
```

## How StudioFlow maps to the JD

Filled in once the JD is in the block above. Each bullet of the JD's "responsibilities" should pair to a concrete artifact in this repo (a service, a trace, a remediation).

## Lead-with stories

1. **System design**: walk the pipeline. Ingest → workflow → encode → enrichment → publish. Event-driven, idempotent retries, state machine in one place, observability everywhere. (Frame in terms of how Apple TV / Music actually ingest and publish assets.)
2. **Production reliability**: the encode service's deliberate failure modes are *not* a hack — they're a calibrated chaos harness. Real incidents, real traces, real diagnosis.
3. **AI fluency**: the agent on top isn't a chatbot bolted on; it consumes the same observability data a human operator would, with the same gates.

## Anti-stories (do not lead with these)

- "I built a chatbot for SREs." (Wrong frame — the agent acts, doesn't chat.)
- "I made a Gemini wrapper." (Sells the system layer short.)
- "I learned Cloud Run." (Too small.)

## Questions to ask back

- How does Apple TV's ingest pipeline handle codec drift across studios? (Shows you've thought about the real domain.)
- What's the team's posture on agentic automation in production paths? (Reads the room on AI maturity.)
