import React, { useEffect, useState } from "react";

const cardStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 14,
  background: "rgba(255,255,255,0.02)",
};

function StatCard({ label, value, sub }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, opacity: 0.75 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, marginTop: 6 }}>{value}</div>
      {sub ? <div style={{ fontSize: 12, opacity: 0.75, marginTop: 4 }}>{sub}</div> : null}
    </div>
  );
}

export default function DashboardPanel({ apiBase }) {
  const API = (apiBase || "").replace(/\/$/, "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [overview, setOverview] = useState(null);
  const [funnel, setFunnel] = useState([]);
  const [campaigns, setCampaigns] = useState(null);
  const [remarketing, setRemarketing] = useState(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [o, f, c, r] = await Promise.all([
        fetch(`${API}/api/dashboard/overview?range=7d`),
        fetch(`${API}/api/dashboard/funnel`),
        fetch(`${API}/api/dashboard/campaigns?range=30d`),
        fetch(`${API}/api/dashboard/remarketing`),
      ]);

      const [od, fd, cd, rd] = await Promise.all([o.json(), f.json(), c.json(), r.json()]);
      if (!o.ok) throw new Error(od?.detail || "No se pudo cargar overview");
      if (!f.ok) throw new Error(fd?.detail || "No se pudo cargar funnel");
      if (!c.ok) throw new Error(cd?.detail || "No se pudo cargar campañas");
      if (!r.ok) throw new Error(rd?.detail || "No se pudo cargar remarketing");

      setOverview(od?.kpis || {});
      setFunnel(Array.isArray(fd?.steps) ? fd.steps : []);
      setCampaigns(cd?.metrics || {});
      setRemarketing(rd || {});
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading && !overview) {
    return <div className="placeholder-view">Cargando dashboard...</div>;
  }

  return (
    <div className="placeholder-view" style={{ alignItems: "stretch" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <h2 style={{ margin: 0 }}>Dashboard</h2>
        <button onClick={load} style={{ padding: "8px 12px", borderRadius: 10, cursor: "pointer" }}>Actualizar</button>
      </div>

      {error ? (
        <div style={{ ...cardStyle, borderColor: "rgba(231,76,60,0.5)", marginBottom: 12 }}>
          Error: {error}
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
        <StatCard label="Conversaciones activas" value={overview?.active_conversations ?? 0} sub="Últimos 7 días" />
        <StatCard label="Clientes nuevos" value={overview?.new_customers ?? 0} sub="Primer contacto" />
        <StatCard label="No leídos" value={overview?.unread_conversations ?? 0} sub="Inbox pendiente" />
        <StatCard label="Takeover ON" value={overview?.takeover_on ?? 0} sub="Chats en humano" />
        <StatCard label="Campañas vivas" value={overview?.campaigns_live ?? 0} sub="Running/Scheduled" />
        <StatCard label="Response rate" value={`${overview?.response_rate_pct ?? 0}%`} sub="OUT vs IN" />
      </div>

      <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 10 }}>
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0 }}>Funnel comercial</h3>
          <div style={{ display: "grid", gap: 8 }}>
            {(funnel || []).map((s) => (
              <div key={s.id} style={{ display: "flex", justifyContent: "space-between", gap: 8, borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: 6 }}>
                <span>{s.label}</span>
                <span style={{ fontFamily: "monospace" }}>{s.value} ({s.pct_prev}%)</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: "grid", gap: 10 }}>
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Campañas (30d)</h3>
            <div style={{ fontSize: 13, display: "grid", gap: 4 }}>
              <div>Sent: {campaigns?.sent ?? 0}</div>
              <div>Delivered: {campaigns?.delivered ?? 0}</div>
              <div>Read: {campaigns?.read ?? 0}</div>
              <div>Replied: {campaigns?.replied ?? 0}</div>
              <div>Failed: {campaigns?.failed ?? 0}</div>
            </div>
          </div>

          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Remarketing</h3>
            <div style={{ fontSize: 13, display: "grid", gap: 4 }}>
              <div>Flows: {remarketing?.flows_total ?? 0}</div>
              <div>Activos: {remarketing?.active_flows ?? 0}</div>
              <div>Pasos: {remarketing?.steps_total ?? 0}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

