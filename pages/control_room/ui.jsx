// ui.jsx — small primitives shared across the kit.
// Loaded as a Babel script; exports to window so other kit files can use them.

const Icon = ({ name, size = 18, className = "", style }) => {
  // Inline Lucide-style icons. 1.5 stroke, 24 viewBox.
  const paths = {
    upload:    <g><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></g>,
    video:     <g><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></g>,
    zap:       <g><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></g>,
    activity:  <g><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></g>,
    alert:     <g><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></g>,
    check:     <g><polyline points="20 6 9 17 4 12"/></g>,
    rollback:  <g><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></g>,
    monitor:   <g><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></g>,
    agent:     <g><path d="M12 2a10 10 0 1 0 10 10"/><circle cx="12" cy="12" r="3"/></g>,
    settings:  <g><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></g>,
    search:    <g><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></g>,
    chevron:   <g><polyline points="9 18 15 12 9 6"/></g>,
    x:         <g><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></g>,
    cmd:       <g><path d="M18 3a3 3 0 0 0-3 3v3M6 3a3 3 0 0 1 3 3v3M6 21a3 3 0 0 1 3-3h3M18 21a3 3 0 0 0-3-3h-3M9 9h6v6H9zM15 9h3a3 3 0 1 0-3-3v3M9 9V6a3 3 0 1 0-3 3h3M9 15v3a3 3 0 1 1-3-3h3M15 15h3a3 3 0 1 1-3 3v-3"/></g>,
    sparkle:   <g><path d="M12 2l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/></g>,
    play:      <g><polygon points="6 4 20 12 6 20 6 4" fill="currentColor"/></g>,
    pause:     <g><rect x="5" y="4" width="5" height="16" fill="currentColor"/><rect x="14" y="4" width="5" height="16" fill="currentColor"/></g>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
         className={className} style={style} aria-hidden="true">
      {paths[name] || null}
    </svg>
  );
};

const Dot = ({ tone = "neutral", size = 8, glow = false, style }) => {
  const c = {
    green:   "#30D158",
    amber:   "#FF9F0A",
    red:     "#FF453A",
    indigo:  "#5E5CE6",
    neutral: "rgba(235,235,245,0.6)",
  }[tone];
  return <span style={{
    display: "inline-block",
    width: size, height: size,
    borderRadius: "50%",
    background: c,
    boxShadow: glow ? `0 0 12px ${c}` : "none",
    flex: `0 0 ${size}px`,
    ...style,
  }}/>;
};

const StatusPill = ({ state }) => {
  const map = {
    ingested:  { c: "#fff",     fill: "rgba(255,255,255,0.08)", border: "rgba(255,255,255,0.10)" },
    encoding:  { c: "#FF9F0A",  fill: "rgba(255,159,10,0.16)",  border: "rgba(255,159,10,0.30)" },
    enriching: { c: "#5E5CE6",  fill: "rgba(94,92,230,0.16)",   border: "rgba(94,92,230,0.30)" },
    review:    { c: "#fff",     fill: "rgba(255,255,255,0.08)", border: "rgba(255,255,255,0.10)" },
    published: { c: "#30D158",  fill: "rgba(48,209,88,0.16)",   border: "rgba(48,209,88,0.30)" },
    failed:    { c: "#FF453A",  fill: "rgba(255,69,58,0.16)",   border: "rgba(255,69,58,0.30)" },
  }[state] || { c: "#fff", fill: "rgba(255,255,255,0.08)", border: "rgba(255,255,255,0.10)" };
  return (
    <span style={{
      padding: "3px 10px",
      fontSize: 11, fontWeight: 600, letterSpacing: "0.06em",
      textTransform: "uppercase",
      borderRadius: 999,
      border: `1px solid ${map.border}`,
      background: map.fill,
      color: map.c,
      display: "inline-flex", alignItems: "center", gap: 6,
      whiteSpace: "nowrap",
    }}>{state}</span>
  );
};

const Pill = ({ tone = "neutral", children, style }) => {
  const map = {
    neutral: { c: "#fff",     fill: "rgba(255,255,255,0.08)", border: "rgba(255,255,255,0.10)" },
    accent:  { c: "#0A84FF",  fill: "rgba(10,132,255,0.18)",  border: "rgba(10,132,255,0.32)" },
    amber:   { c: "#FF9F0A",  fill: "rgba(255,159,10,0.16)",  border: "rgba(255,159,10,0.30)" },
    red:     { c: "#FF453A",  fill: "rgba(255,69,58,0.16)",   border: "rgba(255,69,58,0.30)" },
    indigo:  { c: "#5E5CE6",  fill: "rgba(94,92,230,0.16)",   border: "rgba(94,92,230,0.30)" },
    green:   { c: "#30D158",  fill: "rgba(48,209,88,0.16)",   border: "rgba(48,209,88,0.30)" },
  }[tone];
  return (
    <span style={{
      padding: "2px 8px",
      fontSize: 11, fontWeight: 600, letterSpacing: "0.06em",
      textTransform: "uppercase",
      borderRadius: 999,
      border: `1px solid ${map.border}`,
      background: map.fill,
      color: map.c,
      display: "inline-flex", alignItems: "center", gap: 6,
      whiteSpace: "nowrap",
      ...style,
    }}>{children}</span>
  );
};

const Button = ({ variant = "secondary", size = "md", icon, children, onClick, disabled, style, ...rest }) => {
  const sizes = {
    sm: { h: 28, px: 10, font: 12, radius: 8 },
    md: { h: 32, px: 14, font: 13, radius: 10 },
    lg: { h: 40, px: 18, font: 14, radius: 12 },
  }[size];
  const variants = {
    primary:     { bg: "#0A84FF", color: "#fff", shadow: "inset 0 1px 0 rgba(255,255,255,0.18)" },
    secondary:   { bg: "#2c2c2e", color: "rgba(255,255,255,0.95)", shadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 0 0 1px rgba(255,255,255,0.08)" },
    ghost:       { bg: "transparent", color: "rgba(255,255,255,0.85)", shadow: "none" },
    destructive: { bg: "#FF453A", color: "#fff", shadow: "inset 0 1px 0 rgba(255,255,255,0.18)" },
  }[variant];
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        height: sizes.h, padding: `0 ${sizes.px}px`,
        borderRadius: sizes.radius,
        fontWeight: 600, fontSize: sizes.font, fontFamily: "var(--sf-font-sans)",
        background: variants.bg, color: variants.color, boxShadow: variants.shadow,
        border: 0, cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.4 : 1,
        transition: "filter 120ms cubic-bezier(0.4,0,0.2,1), transform 80ms cubic-bezier(0.4,0,0.2,1)",
        ...style,
      }}
      onMouseDown={e => e.currentTarget.style.filter = "brightness(0.95)"}
      onMouseUp={e => e.currentTarget.style.filter = ""}
      onMouseLeave={e => e.currentTarget.style.filter = ""}
      {...rest}
    >
      {icon && <Icon name={icon} size={14}/>}
      {children}
    </button>
  );
};

const GlassPanel = ({ children, style, strong = false }) => (
  <div style={{
    background: strong ? "rgba(28,28,30,0.85)" : "rgba(28,28,30,0.6)",
    backdropFilter: "saturate(180%) blur(40px)",
    WebkitBackdropFilter: "saturate(180%) blur(40px)",
    borderRadius: 18,
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08), inset 0 0 0 1px rgba(255,255,255,0.10), 0 12px 32px rgba(0,0,0,0.48)",
    ...style,
  }}>{children}</div>
);

const Card = ({ children, style, padding = 16 }) => (
  <div style={{
    background: "#1c1c1e",
    borderRadius: 14,
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 0 0 1px rgba(255,255,255,0.08)",
    padding,
    ...style,
  }}>{children}</div>
);

const Kbd = ({ children }) => (
  <span style={{
    fontFamily: "var(--sf-font-mono)", fontSize: 11, fontWeight: 600,
    padding: "2px 6px",
    background: "rgba(255,255,255,0.06)",
    color: "rgba(255,255,255,0.65)",
    borderRadius: 4,
    border: "1px solid rgba(255,255,255,0.08)",
  }}>{children}</span>
);

Object.assign(window, { Icon, Dot, StatusPill, Pill, Button, GlassPanel, Card, Kbd });
