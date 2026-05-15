// App.jsx — top-level layout + demo state machine.
//
// LIVE DATA: assets / pipeline summary / approvals / audit_log are fetched from
// the backend API every POLL_INTERVAL_MS. The "Run chaos" button still drives
// a scripted tool-stream + envState animation so the right inspector panel has
// activity during the agent's diagnosis, but the ACTUAL approval gate is
// driven by the real Firestore approvals/ collection.

const { useState, useEffect, useRef, useCallback } = React;

const POLL_INTERVAL_MS = 3000;

// Map an API approval doc into the ApprovalGate's expected `remediation` shape.
const mapApprovalToRemediation = (approval) => {
  if (!approval) return null;
  const actions = (approval.proposed_actions || []).map((a, i) => {
    const params = a.params || {};
    const memoryMi = params.memory_mi || params.memory_mb || params.memory;
    let label, target, duration;
    if (a.action === "scale") {
      label = "Scale memory";
      target = memoryMi ? `${memoryMi} MiB` : (a.target || "memory");
      duration = "~12s";
    } else if (a.action === "rollback") {
      label = "Rollback to commit";
      target = params.to_commit || a.target;
      duration = "~30s";
    } else if (a.action === "retry" || a.action === "retry-asset" || a.action === "retry_asset") {
      label = "Retry asset";
      target = a.target;
      duration = "~5s";
    } else {
      label = a.action || "Action";
      target = a.target || "—";
      duration = "—";
    }
    return { id: i + 1, label, target, duration };
  });
  return {
    actions,
    confidence: approval.confidence,
    problemId: approval.id.slice(0, 8),
    planId: approval.id,
  };
};

/* ============================================================
   The demo state machine
   ------------------------------------------------------------
   healthy
     └─[Run chaos]──▶ incident-detected
                          └─(t≈400ms)──▶ agent-diagnosing
                                              └─(tool stream)──▶ awaiting-approval
                                                                     ├─[Approve]──▶ remediating ─▶ recovered
                                                                     └─[Reject]───▶ recovered
   ============================================================ */

const App = () => {
  const [envState,    setEnvState]    = useState("healthy");
  const [selectedId,  setSelectedId]  = useState(null);
  const [toolLines,   setToolLines]   = useState([]);
  const [toasts,      setToasts]      = useState([]);
  const [time,        setTime]        = useState("14:31:02");
  // LIVE DATA from backend.
  const [liveAssets,       setLiveAssets]       = useState([]);
  const [liveServices,     setLiveServices]     = useState([]);
  const [livePending,      setLivePending]      = useState(null);   // first pending approval
  const [liveAuditLog,     setLiveAuditLog]     = useState([]);
  const seenAuditIdsRef = useRef(new Set());
  const timersRef = useRef([]);

  // Live clock
  useEffect(() => {
    const id = setInterval(() => {
      const d = new Date();
      setTime(d.toLocaleTimeString("en-GB", { hour12: false }));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  // LIVE DATA polling. Fires immediately and then every POLL_INTERVAL_MS.
  useEffect(() => {
    let cancelled = false;
    const pushToastSafe = (toast) => {
      const id = Math.random().toString(36).slice(2);
      setToasts(ts => [...ts, { ...toast, id }]);
      setTimeout(() => setToasts(ts => ts.filter(t => t.id !== id)), toast.duration || 4500);
    };
    const tick = async () => {
      try {
        const [assets, services, approvals, audit] = await Promise.all([
          fetch("/api/assets?limit=20").then(r => r.json()).catch(() => []),
          fetch("/api/pipeline-summary").then(r => r.json()).catch(() => []),
          fetch("/api/approvals?status=pending&limit=5").then(r => r.json()).catch(() => []),
          fetch("/api/audit-log?limit=10").then(r => r.json()).catch(() => []),
        ]);
        if (cancelled) return;
        setLiveAssets(assets);
        setLiveServices(services);
        setLivePending(approvals && approvals.length ? approvals[0] : null);
        // Toast for any audit entry we haven't seen before.
        const seen = seenAuditIdsRef.current;
        const isFirstFetch = seen.size === 0;
        for (const a of audit) {
          if (a.id && !seen.has(a.id)) {
            seen.add(a.id);
            if (!isFirstFetch) {
              pushToastSafe({
                tone: a.simulated ? "indigo" : "green",
                msg: a.result || `${a.action} ${a.target}`,
                meta: a.simulated ? "simulated" : "executed",
              });
            }
          }
        }
        setLiveAuditLog(audit);
      } catch (e) {
        // Best-effort polling; ignore transient errors.
      }
    };
    tick();
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  // Util — schedule timers that get cleared on reset.
  const schedule = useCallback((delay, fn) => {
    const id = setTimeout(fn, delay);
    timersRef.current.push(id);
    return id;
  }, []);

  const clearAllTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  const pushToast = useCallback((toast) => {
    const id = Math.random().toString(36).slice(2);
    setToasts(ts => [...ts, { ...toast, id }]);
    schedule(toast.duration || 4500, () => {
      setToasts(ts => ts.filter(t => t.id !== id));
    });
  }, [schedule]);

  // Run the chaos arc.
  const runChaos = useCallback(() => {
    clearAllTimers();
    setToolLines([]);
    setEnvState("incident-detected");
    pushToast({ tone: "red", msg: "encode · OOM killed", meta: "PRB-7281" });

    // small gap before agent kicks in
    schedule(400, () => setEnvState("agent-diagnosing"));

    // Stream tool calls
    window.SF_AGENT_SCRIPT.forEach((step) => {
      schedule(step.tAt + 400, () => {
        const d = new Date();
        const t = d.toLocaleTimeString("en-GB", { hour12: false });
        setToolLines(lines => [...lines, {
          t,
          tool: step.tool,
          args: step.args,
          result: step.result,
          resultTone: step.resultTone,
        }]);
        if (step.tool === "approval_gate.request") {
          setEnvState("awaiting-approval");
          pushToast({ tone: "amber", msg: "Approval required", meta: "rollback + scale" });
        }
      });
    });
  }, [clearAllTimers, pushToast, schedule]);

  const decideLive = useCallback(async (decision) => {
    if (!livePending) return false;
    try {
      const resp = await fetch(`/api/approvals/${livePending.id}/decide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, decided_by: "operator@studio-control-room" }),
      });
      return resp.ok;
    } catch (e) {
      return false;
    }
  }, [livePending]);

  const onApprove = useCallback(async () => {
    setEnvState("remediating");
    const planLabel = livePending ? livePending.id.slice(0, 8) : "pending";
    pushToast({ tone: "indigo", msg: `Approving ${planLabel}…`, meta: "execute via agent" });
    const ok = await decideLive("approved");
    if (!ok) {
      pushToast({ tone: "red", msg: "Approval failed", meta: "see console" });
      return;
    }
    // The agent's HumanApprovalGate will see status=approved on its next poll,
    // unblock, and call scale_service. The new audit_log entry surfaces via the
    // polling tick above (with its own toast).
    schedule(1400, () => setEnvState("recovered"));
  }, [decideLive, livePending, pushToast, schedule]);

  const onReject = useCallback(async () => {
    setEnvState("recovered");
    const ok = await decideLive("rejected");
    pushToast({
      tone: ok ? "neutral" : "red",
      msg: ok ? "Remediation rejected." : "Reject failed",
      meta: "logged",
    });
  }, [decideLive, pushToast]);

  const reset = useCallback(() => {
    clearAllTimers();
    setEnvState("healthy");
    setToolLines([]);
    setToasts([]);
  }, [clearAllTimers]);

  // ⌘↵ / esc shortcuts for the approval sheet.
  useEffect(() => {
    const handler = (e) => {
      if (envState === "awaiting-approval") {
        if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); onApprove(); }
        else if (e.key === "Escape") { e.preventDefault(); onReject(); }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [envState, onApprove, onReject]);

  // LIVE: pending approval auto-opens the gate, overriding scripted envState.
  const gateOpen = !!livePending || envState === "awaiting-approval";
  const liveRemediation = mapApprovalToRemediation(livePending) || window.SF_REMEDIATION;

  // Pick a "failing" asset to highlight in the table:
  //   prefer any asset whose state is failed/encoding when there's a live incident.
  const baseAssets = (liveAssets && liveAssets.length) ? liveAssets : window.SF_ASSETS;
  const failedAssetId = (() => {
    if (envState === "healthy" || envState === "recovered") return null;
    const failed = baseAssets.find(a => a.state === "failed");
    if (failed) return failed.id;
    const encoding = baseAssets.find(a => a.state === "encoding");
    return encoding ? encoding.id : null;
  })();

  const services = (liveServices && liveServices.length ? liveServices : window.SF_SERVICES).map(s => {
    if (s.id !== "encode") return s;
    if (envState === "healthy" && !gateOpen)                 return { ...s, health: "healthy" };
    if (envState === "incident-detected" || envState === "agent-diagnosing" || gateOpen)
                                                              return { ...s, health: "failing", meta: "OOM" };
    if (envState === "remediating")                          return { ...s, health: "degraded", meta: "scaling…" };
    if (envState === "recovered")                            return { ...s, health: "healthy" };
    return s;
  });

  const selectedAsset = selectedId ? baseAssets.find(a => a.id === selectedId) : null;
  const incidentCount = (gateOpen || (envState !== "healthy" && envState !== "recovered")) ? 1 : 0;
  const agentNavState = gateOpen ? "waiting"
                      : envState === "healthy" ? "idle"
                      : envState === "recovered" ? "idle"
                      : envState === "remediating" ? "running"
                      : "diagnosing";

  return (
    <div style={{ minHeight: "100vh", background: "#000", display: "flex", flexDirection: "column" }}>
      <TopBar
        envState={envState}
        time={time}
        onChaos={runChaos}
        onReset={reset}
      />

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <Sidebar
          active="overview"
          incidentCount={incidentCount}
          agentState={agentNavState}
        />

        {/* Main content */}
        <main style={{
          flex: 1, minWidth: 0,
          padding: "24px 24px 32px",
          display: "flex", flexDirection: "column", gap: 16,
        }}>
          {/* Page header */}
          <div style={{ display: "flex", alignItems: "flex-end", gap: 16 }}>
            <div>
              <div style={{ font: "var(--sf-text-micro)", letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(255,255,255,0.42)" }}>
                Overview · last 1h
              </div>
              <h1 style={{ margin: 0, font: "var(--sf-text-h1)", letterSpacing: "-0.01em", color: "#fff" }}>
                Studio Control Room
              </h1>
            </div>
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
              {envState !== "healthy" && envState !== "recovered" && (
                <Pill tone="red"><Dot tone="red" glow/> 1 active incident</Pill>
              )}
              {envState === "recovered" && (
                <Pill tone="green"><Dot tone="green"/> All systems healthy</Pill>
              )}
              <Pill tone="neutral">us-central1</Pill>
            </div>
          </div>

          <PipelineSummary services={services} envState={envState}/>

          {/* Asset table */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
            <h2 style={{ margin: 0, font: "var(--sf-text-h2)", letterSpacing: "-0.005em", color: "#fff" }}>
              Assets in flight
            </h2>
            <span style={{ marginLeft: 6, font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)" }}>
              {baseAssets.length} in pipeline
            </span>
            <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
              <Button variant="ghost" size="sm">All</Button>
              <Button variant="secondary" size="sm">Encoding</Button>
              <Button variant="ghost" size="sm">Failed</Button>
              <Button variant="ghost" size="sm">Published</Button>
            </div>
          </div>

          <AssetTable
            assets={baseAssets}
            selectedId={selectedId}
            failedId={failedAssetId}
            onSelect={(id) => setSelectedId(prev => prev === id ? null : id)}
          />
        </main>

        <Inspector
          envState={gateOpen ? "awaiting-approval" : envState}
          remediation={liveRemediation}
          toolLines={toolLines}
          selectedAsset={selectedAsset}
          onApprove={onApprove}
          onReject={onReject}
          onClose={() => setSelectedId(null)}
        />
      </div>

      <ApprovalGate
        open={gateOpen}
        remediation={liveRemediation}
        onApprove={onApprove}
        onReject={onReject}
      />

      <Toast toasts={toasts}/>
    </div>
  );
};

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App/>);
