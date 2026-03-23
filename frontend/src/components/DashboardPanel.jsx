import React, { useEffect, useMemo, useState } from "react";

const shell = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 14,
  background: "rgba(255,255,255,0.02)",
  padding: 14,
};

const section = {
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 12,
  background: "rgba(255,255,255,0.02)",
  padding: 14,
};

const tiny = {
  fontSize: 12,
  opacity: 0.78,
};

const softBtn = {
  padding: "7px 10px",
  borderRadius: 9,
  border: "1px solid rgba(255,255,255,0.16)",
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
};

function pct(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n)) return 0;
  if (n < 0) return 0;
  if (n > 100) return 100;
  return n;
}

function StatCard({ label, value, sub, accent = "rgba(255,255,255,0.08)" }) {
  return (
    <div
      style={{
        ...section,
        padding: 12,
        background: `linear-gradient(160deg, ${accent}, rgba(255,255,255,0.02))`,
      }}
    >
      <div style={{ ...tiny, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 800, lineHeight: 1.1 }}>{value}</div>
      {sub ? <div style={{ ...tiny, marginTop: 6 }}>{sub}</div> : null}
    </div>
  );
}

function ProgressRow({ label, value, pctValue, tone = "#8ad9ff", suffix = "%" }) {
  const barPct = pct(pctValue);
  return (
    <div style={{ display: "grid", gap: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <div style={{ fontSize: 13 }}>{label}</div>
        <div style={{ fontSize: 12, opacity: 0.86 }}>
          {value}
          {suffix}
        </div>
      </div>
      <div style={{ height: 8, borderRadius: 999, background: "rgba(255,255,255,0.1)", overflow: "hidden" }}>
        <div style={{ width: `${barPct}%`, height: "100%", background: tone }} />
      </div>
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
  const [range, setRange] = useState("30d");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [o, f, c, r] = await Promise.all([
        fetch(`${API}/api/dashboard/overview?range=${encodeURIComponent(range)}`),
        fetch(`${API}/api/dashboard/funnel`),
        fetch(`${API}/api/dashboard/campaigns?range=${encodeURIComponent(range)}`),
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
  }, [range]);

  const funnelMax = useMemo(() => {
    const values = (funnel || []).map((s) => Number(s.value || 0)).filter((v) => Number.isFinite(v) && v > 0);
    return values.length ? Math.max(...values) : 0;
  }, [funnel]);

  const campaignDelivery = pct(campaigns?.delivery_rate_pct ?? 0);
  const campaignRead = pct(campaigns?.read_rate_pct ?? 0);
  const campaignReply = pct(campaigns?.reply_rate_pct ?? 0);

  const insights = useMemo(() => {
    const rows = [];
    const unread = Number(overview?.unread_conversations || 0);
    const live = Number(overview?.campaigns_live || 0);
    const response = Number(overview?.response_rate_pct || 0);
    const failed = Number(campaigns?.failed || 0);
    const activeFlows = Number(remarketing?.active_flows || 0);

    if (unread > 20) rows.push(`Tienes ${unread} conversaciones no leídas; prioriza inbox para evitar caída de conversión.`);
    if (response < 60) rows.push(`Response rate en ${response.toFixed(1)}%; revisa tiempos de respuesta y cobertura de plantillas.`);
    if (failed > 0) rows.push(`Hubo ${failed} envíos fallidos en campañas; conviene revisar estado de números/plantillas.`);
    if (activeFlows === 0) rows.push("No hay flows de remarketing activos; hay oportunidad de recuperar leads tibios.");
    if (live === 0) rows.push("No hay campañas en ejecución; considera activar una campaña base semanal.");
    if (!rows.length) rows.push("Salud general estable: métricas sin alertas críticas en este corte.");
    return rows.slice(0, 4);
  }, [overview, campaigns, remarketing]);

  if (loading && !overview) {
    return <div className="placeholder-view">Cargando dashboard...</div>;
  }

  return (
    <div className="placeholder-view" style={{ alignItems: "stretch", padding: 12 }}>
      <div style={{ ...shell, width: "100%", display: "grid", gap: 12, overflow: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <div>
            <h2 style={{ margin: 0 }}>Dashboard</h2>
            <div style={tiny}>Vista operativa y comercial ({range})</div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div style={{ display: "flex", gap: 6 }}>
              {["7d", "30d", "90d"].map((opt) => (
                <button
                  key={opt}
                  onClick={() => setRange(opt)}
                  style={{
                    ...softBtn,
                    background: range === opt ? "rgba(255,255,255,0.16)" : "transparent",
                  }}
                >
                  {opt}
                </button>
              ))}
            </div>
            <button onClick={load} style={softBtn}>Actualizar</button>
          </div>
        </div>

        {error ? (
          <div style={{ ...section, borderColor: "rgba(231,76,60,0.5)", color: "#ffb4b4" }}>
            Error: {error}
          </div>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 10 }}>
          <StatCard label="Conversaciones activas" value={overview?.active_conversations ?? 0} sub={`Rango ${range}`} accent="rgba(56,189,248,0.14)" />
          <StatCard label="Clientes nuevos" value={overview?.new_customers ?? 0} sub="Primer contacto IN" accent="rgba(52,211,153,0.14)" />
          <StatCard label="No leídos" value={overview?.unread_conversations ?? 0} sub="Pendientes en inbox" accent="rgba(251,191,36,0.14)" />
          <StatCard label="Takeover ON" value={overview?.takeover_on ?? 0} sub="Chats en humano" accent="rgba(244,114,182,0.14)" />
          <StatCard label="Campañas vivas" value={overview?.campaigns_live ?? 0} sub="Running/Scheduled" accent="rgba(167,139,250,0.14)" />
          <StatCard label="Response rate" value={`${overview?.response_rate_pct ?? 0}%`} sub="OUT vs IN" accent="rgba(96,165,250,0.14)" />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.35fr 1fr", gap: 10 }}>
          <div style={section}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <h3 style={{ margin: 0 }}>Funnel comercial</h3>
              <span style={tiny}>Conversión por etapa</span>
            </div>
            <div style={{ display: "grid", gap: 10 }}>
              {(funnel || []).map((s) => {
                const current = Number(s.value || 0);
                const bar = funnelMax > 0 ? (current / funnelMax) * 100 : 0;
                return (
                  <div key={s.id} style={{ display: "grid", gap: 5 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <div style={{ fontSize: 13 }}>{s.label}</div>
                      <div style={{ fontSize: 12, opacity: 0.86 }}>
                        {current} | {pct(s.pct_prev)}%
                      </div>
                    </div>
                    <div style={{ height: 9, borderRadius: 999, background: "rgba(255,255,255,0.1)", overflow: "hidden" }}>
                      <div style={{ width: `${pct(bar)}%`, height: "100%", background: "linear-gradient(90deg, #34d399, #60a5fa)" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            <div style={section}>
              <h3 style={{ marginTop: 0 }}>Rendimiento campañas</h3>
              <div style={{ ...tiny, marginBottom: 10 }}>Base: sent {campaigns?.sent ?? 0} | failed {campaigns?.failed ?? 0}</div>
              <div style={{ display: "grid", gap: 10 }}>
                <ProgressRow label="Delivery rate" value={campaignDelivery.toFixed(1)} pctValue={campaignDelivery} tone="#60a5fa" />
                <ProgressRow label="Read rate" value={campaignRead.toFixed(1)} pctValue={campaignRead} tone="#34d399" />
                <ProgressRow label="Reply rate" value={campaignReply.toFixed(1)} pctValue={campaignReply} tone="#fbbf24" />
              </div>
              <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <div style={{ ...section, padding: 10 }}>
                  <div style={tiny}>Delivered</div>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>{campaigns?.delivered ?? 0}</div>
                </div>
                <div style={{ ...section, padding: 10 }}>
                  <div style={tiny}>Replied</div>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>{campaigns?.replied ?? 0}</div>
                </div>
              </div>
            </div>

            <div style={section}>
              <h3 style={{ marginTop: 0 }}>Remarketing</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8 }}>
                <div style={{ ...section, padding: 10 }}>
                  <div style={tiny}>Flows</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{remarketing?.flows_total ?? 0}</div>
                </div>
                <div style={{ ...section, padding: 10 }}>
                  <div style={tiny}>Activos</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{remarketing?.active_flows ?? 0}</div>
                </div>
                <div style={{ ...section, padding: 10 }}>
                  <div style={tiny}>Pasos</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{remarketing?.steps_total ?? 0}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div style={section}>
          <h3 style={{ marginTop: 0 }}>Insights rápidos</h3>
          <div style={{ display: "grid", gap: 8 }}>
            {insights.map((txt, idx) => (
              <div key={`${idx}-${txt}`} style={{ fontSize: 13, opacity: 0.9, borderLeft: "3px solid rgba(255,255,255,0.22)", paddingLeft: 10 }}>
                {txt}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

