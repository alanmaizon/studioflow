// Toast.jsx — bottom-right toast stack.

const Toast = ({ toasts }) => {
  return (
    <div style={{
      position: "fixed", right: 24, bottom: 24, zIndex: 60,
      display: "flex", flexDirection: "column-reverse", gap: 8,
      pointerEvents: "none",
    }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          padding: "10px 14px",
          background: "rgba(28,28,30,0.85)",
          backdropFilter: "saturate(180%) blur(20px)",
          WebkitBackdropFilter: "saturate(180%) blur(20px)",
          borderRadius: 12,
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08), inset 0 0 0 1px rgba(255,255,255,0.10), 0 12px 32px rgba(0,0,0,0.48)",
          display: "flex", alignItems: "center", gap: 10,
          minWidth: 280, maxWidth: 360,
          pointerEvents: "auto",
        }}>
          <Dot tone={t.tone || "neutral"} glow={t.tone === "indigo"}/>
          <span style={{ font: "var(--sf-text-body)", color: "rgba(255,255,255,0.95)" }}>{t.msg}</span>
          {t.meta && <span style={{ marginLeft: "auto", font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)" }}>{t.meta}</span>}
        </div>
      ))}
    </div>
  );
};

Object.assign(window, { Toast });
