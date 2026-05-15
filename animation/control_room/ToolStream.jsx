// ToolStream.jsx — live agent tool-call log.

const ToolStream = ({ lines }) => {
  return (
    <Card padding={0} style={{ background: "#141414", overflow: "hidden" }}>
      <div style={{
        padding: "10px 14px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <Icon name="activity" size={14} style={{ color: "#5E5CE6" }}/>
        <span style={{ font: "600 11px/16px var(--sf-font-sans)", letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(255,255,255,0.65)" }}>
          Tool stream
        </span>
        <span style={{ marginLeft: "auto", font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)" }}>
          {lines.length} call{lines.length === 1 ? "" : "s"}
        </span>
      </div>
      <div style={{ padding: "6px 14px 10px", display: "flex", flexDirection: "column", gap: 0 }}>
        {lines.length === 0 && (
          <div style={{ font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)", padding: "8px 0" }}>
            Agent idle. Waiting for a Dynatrace problem to surface.
          </div>
        )}
        {lines.map((line, i) => (
          <div key={i} style={{
            display: "grid",
            gridTemplateColumns: "62px 1fr auto",
            gap: 10, padding: "6px 0",
            borderBottom: i < lines.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none",
            font: "var(--sf-text-mono)",
          }}>
            <span style={{ color: "rgba(255,255,255,0.42)" }}>{line.t}</span>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              <span style={{ color: "#5E5CE6" }}>{line.tool}</span>
              <span style={{ color: "rgba(255,255,255,0.65)" }}> ({line.args})</span>
            </span>
            <span style={{
              color: line.resultTone === "wait" ? "#FF9F0A" :
                     line.resultTone === "err"  ? "#FF453A" : "#30D158",
            }}>{line.result}</span>
          </div>
        ))}
      </div>
    </Card>
  );
};

Object.assign(window, { ToolStream });
