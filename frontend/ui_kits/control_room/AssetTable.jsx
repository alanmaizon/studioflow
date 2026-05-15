// AssetTable.jsx + AssetRow.jsx (single file for kit).

const AssetRow = ({ asset, selected, onClick, failed }) => {
  return (
    <button
      onClick={onClick}
      style={{
        all: "unset",
        cursor: "pointer",
        display: "grid",
        gridTemplateColumns: "96px 1fr 130px 140px 90px",
        gap: 16, alignItems: "center",
        padding: "10px 14px",
        background: selected ? "rgba(10,132,255,0.08)" : "transparent",
        boxShadow: selected ? "inset 0 0 0 1px rgba(10,132,255,0.30)" : "none",
        borderRadius: 12,
        transition: "background 120ms cubic-bezier(0.4,0,0.2,1)",
      }}
      onMouseEnter={e => { if (!selected) e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
      onMouseLeave={e => { if (!selected) e.currentTarget.style.background = "transparent"; }}
    >
      <div style={{
        width: 96, height: 54, borderRadius: 6,
        background: `linear-gradient(135deg, ${failed ? "#FF453A30" : asset.tint}, #1c1c1e)`,
        position: "relative",
        boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.06)",
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(to top, rgba(0,0,0,0.6), transparent 55%)",
        }}/>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
        <span style={{ font: "500 14px/20px var(--sf-font-sans)", color: "rgba(255,255,255,0.95)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {asset.title}
        </span>
        <span style={{ font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)" }}>
          asset_{asset.id} · {asset.size} · {asset.codec}
        </span>
      </div>

      <div><StatusPill state={failed ? "failed" : asset.state}/></div>

      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {failed ? (
          <span style={{ font: "var(--sf-text-mono)", color: "#FF453A" }}>OOM · 3/3</span>
        ) : asset.state === "encoding" || asset.state === "enriching" ? (
          <>
            <span style={{ font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.95)" }}>{asset.progress}%</span>
            <div style={{ height: 4, background: "rgba(255,255,255,0.08)", borderRadius: 2, overflow: "hidden" }}>
              <div style={{
                height: "100%", width: `${asset.progress}%`,
                background: asset.state === "encoding" ? "#FF9F0A" : "#5E5CE6",
                transition: "width 600ms cubic-bezier(0.4,0,0.2,1)",
              }}/>
            </div>
          </>
        ) : asset.state === "published" ? (
          <span style={{ font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.65)" }}>2 outputs</span>
        ) : (
          <span style={{ font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)" }}>—</span>
        )}
      </div>

      <span style={{ font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)", textAlign: "right" }}>
        {asset.started}
      </span>
    </button>
  );
};

const AssetTable = ({ assets, selectedId, failedId, onSelect }) => {
  return (
    <Card padding={0} style={{ overflow: "hidden" }}>
      {/* Header row */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "96px 1fr 130px 140px 90px",
        gap: 16,
        padding: "10px 14px",
        background: "rgba(255,255,255,0.02)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        font: "600 11px/16px var(--sf-font-sans)",
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: "rgba(255,255,255,0.42)",
      }}>
        <span>Asset</span>
        <span style={{ paddingLeft: 0 }}>Title</span>
        <span>State</span>
        <span>Progress</span>
        <span style={{ textAlign: "right" }}>Started</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: 4 }}>
        {assets.map(a => (
          <AssetRow
            key={a.id}
            asset={a}
            selected={a.id === selectedId}
            failed={a.id === failedId}
            onClick={() => onSelect(a.id)}
          />
        ))}
      </div>
    </Card>
  );
};

Object.assign(window, { AssetTable, AssetRow });
