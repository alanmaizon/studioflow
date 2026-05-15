// PipelineSummary.jsx — stage tiles row.

const Sparkline = ({ points = [], color = "#0A84FF", height = 24 }) => {
  if (!points.length) return null;
  const max = Math.max(...points), min = Math.min(...points);
  const range = Math.max(1, max - min);
  const w = 100;
  const step = w / (points.length - 1);
  const path = points.map((p, i) => `${i ? "L" : "M"} ${(i * step).toFixed(2)} ${(height - ((p - min) / range) * (height - 2) - 1).toFixed(2)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" style={{ width: "100%", height, display: "block" }}>
      <path d={path} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
    </svg>
  );
};

const PipelineStage = ({ service, fail }) => {
  const dotTone = fail ? "red" : service.health === "degraded" ? "amber" : "green";
  return (
    <Card padding={14} style={{
      display: "flex", flexDirection: "column", gap: 6,
      ...(fail ? {
        background: "rgba(255,69,58,0.10)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 0 0 1px rgba(255,69,58,0.30)",
      } : {})
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <Dot tone={dotTone} glow={fail}/>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(255,255,255,0.65)" }}>
          {service.name}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{
          font: "600 28px/32px var(--sf-font-display)",
          letterSpacing: "-0.01em",
          color: fail ? "#FF453A" : "#fff",
          fontVariantNumeric: "tabular-nums",
        }}>{service.count}</span>
        <span style={{ fontSize: 12, color: fail ? "#FF453A" : "rgba(255,255,255,0.42)" }}>
          {fail ? "OOM killed · 3 retries" : service.meta}
        </span>
      </div>
      <Sparkline
        points={service.spark || [4, 6, 5, 7, 6, 8, 7, 9, 8, fail ? 18 : 9]}
        color={fail ? "#FF453A" : service.health === "degraded" ? "#FF9F0A" : "#0A84FF"}
        height={20}
      />
    </Card>
  );
};

const PipelineSummary = ({ services, envState }) => {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
      {services.map(s => (
        <PipelineStage key={s.id} service={s} fail={s.id === "encode" && envState !== "healthy" && envState !== "recovered"}/>
      ))}
    </div>
  );
};

Object.assign(window, { PipelineSummary, PipelineStage, Sparkline });
