// ApprovalGate.jsx — modal sheet for confirming a remediation plan.

const ApprovalGate = ({ open, remediation, onApprove, onReject }) => {
  if (!open) return null;
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 50,
      background: "rgba(0,0,0,0.5)",
      backdropFilter: "saturate(180%) blur(6px)",
      WebkitBackdropFilter: "saturate(180%) blur(6px)",
      display: "flex", alignItems: "flex-end", justifyContent: "center",
    }}>
      <div style={{
        width: "min(680px, calc(100% - 48px))",
        margin: "0 24px 32px",
      }}>
        <GlassPanel strong style={{ padding: 22, boxShadow: "inset 0 1px 0 rgba(255,255,255,0.10), inset 0 0 0 1px rgba(255,255,255,0.12), 0 24px 60px rgba(0,0,0,0.6)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <Dot tone="amber" glow/>
            <span style={{ font: "600 11px/16px var(--sf-font-sans)", letterSpacing: "0.06em", textTransform: "uppercase", color: "#FF9F0A" }}>
              Approval required
            </span>
            <span style={{ marginLeft: "auto", font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)" }}>
              {remediation.problemId} · waiting
            </span>
          </div>

          <div style={{ font: "600 22px/28px var(--sf-font-display)", letterSpacing: "-0.005em", color: "#fff" }}>
            You are about to execute {remediation.actions.length} actions on the{" "}
            <code style={{ font: "500 21px/28px var(--sf-font-mono)" }}>encode</code> service.
          </div>
          <div style={{ font: "var(--sf-text-caption)", color: "rgba(255,255,255,0.65)", marginTop: 6 }}>
            This cannot be undone in one click.
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 16 }}>
            {remediation.actions.map(a => (
              <div key={a.id} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "10px 12px",
                background: "rgba(255,255,255,0.04)",
                borderRadius: 10,
                boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.06)",
              }}>
                <span style={{
                  width: 20, height: 20, borderRadius: 5,
                  background: "#0A84FF", color: "#fff",
                  fontSize: 11, fontWeight: 700,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  flex: "0 0 20px",
                }}>{a.id}</span>
                <span style={{ font: "var(--sf-text-body)", color: "rgba(255,255,255,0.95)" }}>
                  {a.label}{" "}
                  <code style={{ font: "var(--sf-text-mono)", fontWeight: 600, color: "#fff" }}>{a.target}</code>
                </span>
                <span style={{ marginLeft: "auto", font: "var(--sf-text-caption)", color: "rgba(255,255,255,0.42)" }}>{a.duration}</span>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 16 }}>
            <Button variant="primary" size="lg" onClick={onApprove}>Approve · run both</Button>
            <Button variant="secondary" size="lg" onClick={onReject}>Reject</Button>
            <span style={{ marginLeft: "auto", font: "var(--sf-text-caption)", color: "rgba(255,255,255,0.42)" }}>
              <Kbd>⌘ ↵</Kbd> approve · <Kbd>esc</Kbd> reject
            </span>
          </div>
        </GlassPanel>
      </div>
    </div>
  );
};

Object.assign(window, { ApprovalGate });
