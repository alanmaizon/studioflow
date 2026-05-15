// IncidentCard.jsx — agent's structured hypothesis card.

const IncidentCard = ({ remediation, onApprove, onReject, onViewTraces }) => {
  return (
    <GlassPanel strong style={{ padding: 18 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
        <Dot tone="indigo" glow/>
        <span style={{ font: "600 11px/16px var(--sf-font-sans)", letterSpacing: "0.06em", textTransform: "uppercase", color: "#5E5CE6" }}>
          Agent · proposed
        </span>
        <span style={{ marginLeft: "auto", font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.42)" }}>
          {remediation.problemId} · confidence {remediation.confidence}
        </span>
      </div>

      <div style={{
        font: "600 20px/26px var(--sf-font-display)",
        letterSpacing: "-0.005em",
        color: "#fff",
      }}>
        Rollback <code style={{ font: "500 19px/26px var(--sf-font-mono)", color: "#fff" }}>encode</code>
        {" "}to <code style={{ font: "500 19px/26px var(--sf-font-mono)", color: "#fff" }}>abc123</code>
        {" "}&amp; scale memory 1→4 GiB
      </div>

      <div style={{ font: "400 14px/20px var(--sf-font-sans)", color: "rgba(255,255,255,0.65)", marginTop: 8 }}>
        Hypothesis: encode service OOM-killed under 4K concurrency. Correlated with the{" "}
        <code style={{ font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.95)" }}>enable-4k</code>{" "}
        deploy 47 minutes ago.
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 12 }}>
        <Evidence>· trace <Link>7d92f1a3</Link> · <strong>oom_killed=true</strong> · 14:32:08 UTC+01</Evidence>
        <Evidence>· trace <Link>a4e5b1c0</Link> · rss <strong>3.94 GiB / 4.00 GiB</strong> · 14:34:51 UTC+01</Evidence>
        <Evidence>· commit <Link>abc123</Link> · enable-4k · +concurrency=8, +4K codec path</Evidence>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <Button variant="primary" size="md" onClick={onApprove}>Approve remediation</Button>
        <Button variant="secondary" size="md" onClick={onReject}>Reject</Button>
        <Button variant="ghost" size="md" onClick={onViewTraces}>View 3 traces</Button>
      </div>
    </GlassPanel>
  );
};

const Evidence = ({ children }) => (
  <div style={{ font: "var(--sf-text-mono)", color: "rgba(255,255,255,0.65)" }}>{children}</div>
);
const Link = ({ children }) => (
  <a href="#" onClick={e => e.preventDefault()} style={{ color: "#0A84FF", textDecoration: "none" }}>{children}</a>
);

Object.assign(window, { IncidentCard });
