// data.js — fixture data for the control-room prototype.

window.SF_SERVICES = [
  { id: "ingest",     name: "Ingest",     count: 128, health: "healthy",  meta: "p99 1.8s" },
  { id: "encode",     name: "Encode",     count: 38,  health: "healthy",  meta: "p99 14s" },
  { id: "enrichment", name: "Enrichment", count: 34,  health: "healthy",  meta: "p99 6s" },
  { id: "publish",    name: "Publish",    count: 34,  health: "healthy",  meta: "p99 2.1s" },
];

window.SF_ASSETS = [
  { id: "a8f1", title: "S03E04 · Cold open",         codec: "prores", size: "4.2 GiB", state: "encoding",  progress: 38, started: "14:32", duration: "12m", tint: "#3a3a3c" },
  { id: "b7e2", title: "S03E05 · Title sequence",    codec: "prores", size: "5.8 GiB", state: "encoding",  progress: 72, started: "14:18", duration: "26m", tint: "#3a3a3c" },
  { id: "c4d9", title: "S03E03 · Final mix",         codec: "h264",   size: "3.1 GiB", state: "published", progress: 100, started: "13:47", duration: "1h",  tint: "#30d15825" },
  { id: "d8a4", title: "S03E02 · Color pass",        codec: "h264",   size: "2.8 GiB", state: "enriching", progress: 60,  started: "14:05", duration: "39m", tint: "#5e5ce625" },
  { id: "e1c2", title: "S03E01 · Episode master",    codec: "h264",   size: "3.4 GiB", state: "published", progress: 100, started: "12:02", duration: "2h 30m", tint: "#30d15825" },
  { id: "f6b7", title: "Trailer · Season 3",         codec: "h264",   size: "1.1 GiB", state: "review",    progress: 100, started: "13:11", duration: "24m", tint: "#3a3a3c" },
  { id: "g3d2", title: "Behind the scenes · Ep4",    codec: "h264",   size: "1.9 GiB", state: "ingested",  progress: 0,   started: "14:41", duration: "1m",  tint: "#3a3a3c" },
];

// The "deploy" that, in the demo, makes the encode service fragile.
window.SF_BAD_DEPLOY = {
  sha: "abc123",
  branch: "enable-4k",
  author: "carlos",
  at: "13:45 UTC+01",
  diff: "+ concurrency=8, +4K codec path",
};

// Agent script — what tool calls happen in what order, when chaos runs.
window.SF_AGENT_SCRIPT = [
  { tAt: 800,  tool: "dynatrace.list_problems",  args: "now-1h",                                 result: "→ 1 problem", resultTone: "ok" },
  { tAt: 1600, tool: "dynatrace.get_problem",    args: "PRB-7281",                               result: "→ encode · OOM", resultTone: "ok" },
  { tAt: 2600, tool: "dynatrace.dql",            args: "fetch spans, service.name=encode",       result: "→ 47 spans · oom_killed=true", resultTone: "ok" },
  { tAt: 3600, tool: "dynatrace.get_entity",     args: "encode (Cloud Run service)",             result: "→ rss p99 3.94 GiB / 4.00 GiB", resultTone: "ok" },
  { tAt: 4500, tool: "git.deploy_history",       args: "--service encode --since=2h",            result: "→ 2 deploys", resultTone: "ok" },
  { tAt: 5400, tool: "git.diff",                 args: "abc123",                                 result: "→ +concurrency=8, +4K path", resultTone: "ok" },
  { tAt: 6200, tool: "approval_gate.request",    args: "plan=rollback+scale",                    result: "→ waiting", resultTone: "wait" },
];

window.SF_REMEDIATION = {
  actions: [
    { id: 1, label: "Rollback to commit", target: "abc123", duration: "~30s" },
    { id: 2, label: "Scale memory",        target: "1 GiB → 4 GiB", duration: "~12s" },
  ],
  confidence: 0.86,
  problemId: "PRB-7281",
};
