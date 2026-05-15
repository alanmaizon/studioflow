// TopBar.jsx — sticky glass top bar.

const TopBar = ({ envState, onChaos, onReset, time }) => {
  const envLabel = {
    healthy: { dot: "green", text: "demo · healthy" },
    "incident-detected": { dot: "red", text: "demo · incident" },
    "agent-diagnosing":  { dot: "indigo", text: "demo · agent" },
    "awaiting-approval": { dot: "amber", text: "demo · awaiting" },
    "remediating":       { dot: "indigo", text: "demo · remediating" },
    "recovered":         { dot: "green", text: "demo · recovered" },
  }[envState];

  return (
    <div style={{
      position: "sticky", top: 0, zIndex: 10,
      height: 56,
      background: "rgba(0,0,0,0.6)",
      backdropFilter: "saturate(180%) blur(20px)",
      WebkitBackdropFilter: "saturate(180%) blur(20px)",
      borderBottom: "1px solid rgba(255,255,255,0.08)",
      display: "flex", alignItems: "center",
      padding: "0 24px", gap: 16,
    }}>
      {/* logo lockup */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, color: "#fff" }}>
        <svg width="22" height="22" viewBox="0 0 64 64" fill="none">
          <rect x="6"  y="18" width="6" height="28" rx="2" fill="currentColor"/>
          <rect x="18" y="10" width="6" height="44" rx="2" fill="currentColor" opacity="0.86"/>
          <rect x="30" y="22" width="6" height="20" rx="2" fill="currentColor" opacity="0.72"/>
          <rect x="42" y="14" width="6" height="36" rx="2" fill="currentColor" opacity="0.58"/>
          <line x1="2" y1="32" x2="62" y2="32" stroke="currentColor" strokeWidth="1.5" opacity="0.95"/>
        </svg>
        <span style={{ font: "600 15px/22px var(--sf-font-sans)", letterSpacing: "-0.01em" }}>StudioFlow</span>
        <span style={{ color: "rgba(255,255,255,0.42)" }}>·</span>
        <span style={{ font: "500 13px/18px var(--sf-font-sans)", color: "rgba(255,255,255,0.65)" }}>Control Room</span>
      </div>

      {/* search */}
      <div style={{
        flex: 1, maxWidth: 480, marginLeft: 24,
        height: 32, padding: "0 12px",
        background: "rgba(255,255,255,0.04)",
        borderRadius: 10,
        boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.08)",
        display: "flex", alignItems: "center", gap: 8,
        color: "rgba(255,255,255,0.42)",
        fontSize: 13,
      }}>
        <Icon name="search" size={14}/>
        <span>Search assets, traces, services</span>
        <span style={{ marginLeft: "auto" }}><Kbd>⌘ K</Kbd></span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginLeft: "auto" }}>
        <Pill tone={envLabel.dot === "green" ? "green" : envLabel.dot === "red" ? "red" : envLabel.dot === "amber" ? "amber" : "indigo"}>
          <Dot tone={envLabel.dot}/> {envLabel.text}
        </Pill>
        <span style={{ font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)" }}>{time}</span>

        {envState === "healthy"
          ? <Button variant="destructive" icon="zap" size="sm" onClick={onChaos}>Run chaos</Button>
          : <Button variant="secondary" size="sm" onClick={onReset}>Reset demo</Button>}

        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          background: "linear-gradient(135deg,#5E5CE6,#0A84FF)",
          color: "#fff", fontSize: 12, fontWeight: 600,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>CR</div>
      </div>
    </div>
  );
};

Object.assign(window, { TopBar });
