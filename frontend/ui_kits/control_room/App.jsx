// App.jsx — top-level layout + demo state machine.

const { useState, useEffect, useRef, useCallback } = React;

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
  const timersRef = useRef([]);

  // Live clock
  useEffect(() => {
    const id = setInterval(() => {
      const d = new Date();
      setTime(d.toLocaleTimeString("en-GB", { hour12: false }));
    }, 1000);
    return () => clearInterval(id);
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

  const onApprove = useCallback(() => {
    setEnvState("remediating");
    pushToast({ tone: "indigo", msg: "Rolling back to abc123…", meta: "~30s" });
    schedule(1400, () => {
      pushToast({ tone: "indigo", msg: "Scaling memory 1 → 4 GiB…", meta: "~12s" });
    });
    schedule(2800, () => {
      setEnvState("recovered");
      pushToast({ tone: "green", msg: "Recovered. 1 asset re-queued.", meta: "PRB-7281 closed" });
    });
  }, [pushToast, schedule]);

  const onReject = useCallback(() => {
    setEnvState("recovered");
    pushToast({ tone: "neutral", msg: "Remediation rejected.", meta: "logged" });
  }, [pushToast]);

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

  // Derived: which asset is failing in the table during incident.
  const failedAssetId = (envState !== "healthy" && envState !== "recovered") ? "b7e2" : null;

  // Modify assets[0] progress under failure for visual feedback
  const services = window.SF_SERVICES.map(s => {
    if (s.id !== "encode") return s;
    if (envState === "healthy")                              return { ...s, health: "healthy",  count: 38, meta: "p99 14s" };
    if (envState === "incident-detected" || envState === "agent-diagnosing" || envState === "awaiting-approval")
                                                              return { ...s, health: "failing", count: 35, meta: "OOM" };
    if (envState === "remediating")                          return { ...s, health: "degraded", count: 36, meta: "rolling back…" };
    if (envState === "recovered")                            return { ...s, health: "healthy",  count: 39, meta: "p99 12s" };
    return s;
  });

  const selectedAsset = selectedId ? window.SF_ASSETS.find(a => a.id === selectedId) : null;
  const incidentCount = (envState !== "healthy" && envState !== "recovered") ? 1 : 0;
  const agentNavState = envState === "healthy" ? "idle"
                      : envState === "recovered" ? "idle"
                      : envState === "remediating" ? "running"
                      : envState === "awaiting-approval" ? "waiting"
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
              {window.SF_ASSETS.length} in pipeline
            </span>
            <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
              <Button variant="ghost" size="sm">All</Button>
              <Button variant="secondary" size="sm">Encoding</Button>
              <Button variant="ghost" size="sm">Failed</Button>
              <Button variant="ghost" size="sm">Published</Button>
            </div>
          </div>

          <AssetTable
            assets={window.SF_ASSETS}
            selectedId={selectedId}
            failedId={failedAssetId}
            onSelect={(id) => setSelectedId(prev => prev === id ? null : id)}
          />
        </main>

        <Inspector
          envState={envState}
          remediation={window.SF_REMEDIATION}
          toolLines={toolLines}
          selectedAsset={selectedAsset}
          onApprove={onApprove}
          onReject={onReject}
          onClose={() => setSelectedId(null)}
        />
      </div>

      <ApprovalGate
        open={envState === "awaiting-approval"}
        remediation={window.SF_REMEDIATION}
        onApprove={onApprove}
        onReject={onReject}
      />

      <Toast toasts={toasts}/>
    </div>
  );
};

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App/>);
