// Inspector.jsx — right-side panel; shows agent state during an incident, or asset detail.

const Inspector = ({ envState, remediation, toolLines, selectedAsset, onApprove, onReject, onClose }) => {
  const showAgent = envState !== "healthy" && envState !== "recovered";

  return (
    <aside style={{
      width: 380, flex: "0 0 380px",
      padding: "0 24px 24px 0",
      display: "flex", flexDirection: "column", gap: 12,
      overflowY: "auto",
    }}>
      {showAgent && (
        <>
          <SectionHeader>Agent activity</SectionHeader>
          {envState !== "incident-detected" && (
            <IncidentCard
              remediation={remediation}
              onApprove={onApprove}
              onReject={onReject}
              onViewTraces={() => {}}
            />
          )}
          <ToolStream lines={toolLines}/>
          {envState === "recovered" && (
            <PostIncidentSummary/>
          )}
        </>
      )}
      {!showAgent && envState === "recovered" && (
        <PostIncidentSummary/>
      )}
      {!showAgent && selectedAsset && (
        <AssetInspector asset={selectedAsset} onClose={onClose}/>
      )}
      {!showAgent && !selectedAsset && envState !== "recovered" && (
        <EmptyInspector/>
      )}
    </aside>
  );
};

const SectionHeader = ({ children }) => (
  <div style={{
    font: "600 11px/16px var(--sf-font-sans)",
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    color: "rgba(255,255,255,0.42)",
    padding: "8px 4px 0",
  }}>{children}</div>
);

const EmptyInspector = () => (
  <Card padding={20} style={{ textAlign: "center" }}>
    <Icon name="agent" size={28} style={{ color: "rgba(255,255,255,0.22)" }}/>
    <div style={{ font: "500 14px/20px var(--sf-font-sans)", color: "rgba(255,255,255,0.65)", marginTop: 10 }}>
      No active incidents
    </div>
    <div style={{ font: "var(--sf-text-caption)", color: "rgba(255,255,255,0.42)", marginTop: 4 }}>
      Select an asset, or run the chaos script.
    </div>
  </Card>
);

const PostIncidentSummary = () => (
  <Card padding={16} style={{ background: "rgba(48,209,88,0.08)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 0 0 1px rgba(48,209,88,0.30)" }}>
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <Dot tone="green"/>
      <span style={{ font: "600 11px/16px var(--sf-font-sans)", letterSpacing: "0.06em", textTransform: "uppercase", color: "#30D158" }}>
        Recovered
      </span>
      <span style={{ marginLeft: "auto", font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)" }}>
        PRB-7281 · closed
      </span>
    </div>
    <div style={{ font: "var(--sf-text-h3)", color: "#fff", marginTop: 8 }}>Post-incident · 4m 12s</div>
    <div style={{ font: "var(--sf-text-body)", color: "rgba(255,255,255,0.65)", marginTop: 6 }}>
      Rolled back encode to <code style={{ font: "var(--sf-text-mono)", color: "#fff" }}>abc123</code>,
      scaled memory to 4 GiB. 1 asset re-queued. Dynatrace problem auto-closed.
    </div>
  </Card>
);

const AssetInspector = ({ asset, onClose }) => (
  <Card padding={0}>
    <div style={{
      position: "relative",
      height: 160,
      background: `linear-gradient(135deg, ${asset.tint}, #1c1c1e)`,
      borderRadius: "14px 14px 0 0",
    }}>
      <button onClick={onClose} style={{
        position: "absolute", top: 10, right: 10,
        width: 28, height: 28, borderRadius: 8,
        background: "rgba(0,0,0,0.4)", color: "#fff",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.10)",
        cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}><Icon name="x" size={14}/></button>
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(to top, rgba(0,0,0,0.7), transparent 50%)",
        borderRadius: "14px 14px 0 0",
      }}/>
      <div style={{ position: "absolute", left: 14, bottom: 12, right: 14 }}>
        <StatusPill state={asset.state}/>
        <div style={{ font: "600 17px/22px var(--sf-font-display)", color: "#fff", marginTop: 6 }}>
          {asset.title}
        </div>
      </div>
    </div>
    <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
      <Row k="Asset ID" v={`asset_${asset.id}`} mono/>
      <Row k="Codec" v={asset.codec} mono/>
      <Row k="Size" v={asset.size}/>
      <Row k="Started" v={`${asset.started} UTC+01`}/>
      <Row k="Duration" v={asset.duration}/>
      <Row k="Stage" v={asset.state}/>
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        <Button variant="secondary" size="sm" icon="activity">View traces</Button>
        <Button variant="ghost" size="sm">Open asset</Button>
      </div>
    </div>
  </Card>
);

const Row = ({ k, v, mono }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
    <span style={{ font: "var(--sf-text-caption)", color: "rgba(255,255,255,0.42)" }}>{k}</span>
    <span style={{ font: mono ? "var(--sf-text-mono)" : "var(--sf-text-body)", color: "rgba(255,255,255,0.95)" }}>{v}</span>
  </div>
);

Object.assign(window, { Inspector });
