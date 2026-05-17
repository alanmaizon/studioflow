// Sidebar.jsx — left navigation.

const Sidebar = ({ active = "overview", incidentCount = 0, agentState = "idle", onNav }) => {
  const item = (id, label, icon, badge, badgeTone) => {
    const isActive = id === active;
    return (
      <button
        key={id}
        onClick={() => onNav && onNav(id)}
        style={{
          width: "100%",
          display: "flex", alignItems: "center", gap: 10,
          height: 32, padding: "0 10px",
          background: isActive ? "rgba(255,255,255,0.06)" : "transparent",
          color: isActive ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.65)",
          border: 0, cursor: "pointer",
          fontSize: 13, fontWeight: isActive ? 600 : 500, fontFamily: "var(--sf-font-sans)",
          textAlign: "left",
          borderRadius: 8,
        }}>
        <Icon name={icon} size={16}/>
        <span style={{ flex: 1 }}>{label}</span>
        {badge != null && badge > 0 && <Pill tone={badgeTone} style={{ padding: "1px 6px" }}>{badge}</Pill>}
      </button>
    );
  };

  const stage = (id, label, dot) => (
    <button onClick={() => onNav && onNav(id)} style={{
      width: "100%", display: "flex", alignItems: "center", gap: 8,
      height: 28, padding: "0 10px 0 28px",
      background: "transparent", border: 0, cursor: "pointer",
      color: "rgba(255,255,255,0.65)", fontSize: 12, fontFamily: "var(--sf-font-sans)",
      textAlign: "left", borderRadius: 6,
    }}>
      <Dot tone={dot} size={6}/>
      <span>{label}</span>
    </button>
  );

  return (
    <aside style={{
      width: 240, flex: "0 0 240px",
      background: "#0a0a0a",
      borderRight: "1px solid rgba(255,255,255,0.06)",
      padding: "16px 12px",
      display: "flex", flexDirection: "column", gap: 18,
      minHeight: 0, overflowY: "auto",
    }}>
      {item("overview",  "Overview",  "monitor")}
      {item("incidents", "Incidents", "alert", incidentCount, "red")}
      {item("agent",     "Agent",     "agent", agentState !== "idle" ? "·" : null, "indigo")}
      {item("settings",  "Settings",  "settings")}

      <div style={{ marginTop: 8 }}>
        <div style={{
          fontSize: 11, fontWeight: 600, letterSpacing: "0.06em",
          textTransform: "uppercase", color: "rgba(255,255,255,0.42)",
          padding: "0 10px 6px",
        }}>Pipeline</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {stage("stage:ingest",     "Ingest",     "green")}
          {stage("stage:encode",     "Encode",     agentState !== "idle" ? "red" : "green")}
          {stage("stage:enrichment", "Enrichment", "green")}
          {stage("stage:publish",    "Publish",    "green")}
        </div>
      </div>

      <div style={{ marginTop: "auto", padding: "0 4px" }}>
        <Card padding={10} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Dot tone="indigo" glow={agentState !== "idle"}/>
            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: "#5E5CE6" }}>
              Agent · {agentState}
            </span>
          </div>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.42)" }}>Gemini 3.1 Pro · Dynatrace MCP</div>
        </Card>
      </div>
    </aside>
  );
};

Object.assign(window, { Sidebar });
