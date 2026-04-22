import React, { useCallback, useEffect, useMemo, useState } from "react";

const card = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  background: "rgba(255,255,255,0.02)",
  padding: 12,
};

const input = {
  width: "100%",
  padding: "9px 10px",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "rgba(0,0,0,0.2)",
  color: "inherit",
};

const smallBtn = {
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.16)",
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
};

const primaryBtn = {
  ...smallBtn,
  border: "1px solid rgba(46, 204, 113, 0.45)",
  background: "rgba(46, 204, 113, 0.18)",
  color: "#d4ffe6",
};

const dangerBtn = {
  ...smallBtn,
  border: "1px solid rgba(255,120,120,0.45)",
  color: "#ffc2c2",
};

const campaignStatusOptions = [
  { value: "all", label: "Todos" },
  { value: "draft", label: "Draft" },
  { value: "scheduled", label: "Scheduled" },
  { value: "running", label: "Running" },
  { value: "paused", label: "Paused" },
  { value: "completed", label: "Completed" },
  { value: "archived", label: "Archived" },
];

const recipientStatusOptions = [
  { value: "all", label: "Todos" },
  { value: "pending", label: "Pending" },
  { value: "processing", label: "Processing" },
  { value: "sent", label: "Sent" },
  { value: "delivered", label: "Delivered" },
  { value: "read", label: "Read" },
  { value: "replied", label: "Replied" },
  { value: "failed", label: "Failed" },
];

const perPageOptions = [10, 25, 50, 100];

function asErrorMessage(errLike) {
  try {
    if (!errLike) return "Error inesperado";
    if (typeof errLike === "string") return errLike;
    if (typeof errLike?.detail === "string") return errLike.detail;
    if (typeof errLike?.message === "string") return errLike.message;
  } catch (_) {
    // no-op
  }
  return "Error inesperado";
}

async function parseApiResponseSafe(response) {
  const raw = await response.text();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch (_) {
    return { detail: raw };
  }
}

function pct(value, total) {
  const n = Number(value || 0);
  const t = Number(total || 0);
  if (t <= 0) return 0;
  return Math.max(0, Math.min(100, (n / t) * 100));
}

function fmtDate(v) {
  if (!v) return "-";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleString("es-CO", { year: "2-digit", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function actionIcon(kind) {
  const shared = { width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" };
  if (kind === "report") {
    return (
      <svg {...shared}>
        <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    );
  }
  if (kind === "csv") {
    return (
      <svg {...shared}>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
        <path d="M14 2v6h6" />
        <path d="M8 13h8M8 17h8" />
      </svg>
    );
  }
  if (kind === "retry") {
    return (
      <svg {...shared}>
        <path d="M3 10v5h5" />
        <path d="M21 14v-5h-5" />
        <path d="M20 10a8 8 0 0 0-13.5-3.5L3 10" />
        <path d="M4 14a8 8 0 0 0 13.5 3.5L21 14" />
      </svg>
    );
  }
  return (
    <svg {...shared}>
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  );
}

function progressBlock({ label, value, total, color = "#22c55e", subtitle }) {
  const p = pct(value, total);
  return (
    <div style={{ minWidth: 160 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, fontSize: 12, marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ opacity: 0.8 }}>
          {Number(value || 0)}/{Number(total || 0)}
        </span>
      </div>
      <div style={{ height: 7, background: "rgba(148,163,184,0.25)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ width: `${p}%`, height: "100%", background: color }} />
      </div>
      {subtitle ? <div style={{ marginTop: 4, fontSize: 11, opacity: 0.75 }}>{subtitle}</div> : null}
    </div>
  );
}

function statusBadge(status) {
  const s = String(status || "").toLowerCase();
  if (s === "completed") return { color: "#86efac", bg: "rgba(34,197,94,0.18)" };
  if (s === "running") return { color: "#7dd3fc", bg: "rgba(56,189,248,0.2)" };
  if (s === "scheduled") return { color: "#fcd34d", bg: "rgba(251,191,36,0.2)" };
  if (s === "paused") return { color: "#fca5a5", bg: "rgba(248,113,113,0.2)" };
  if (s === "archived") return { color: "#cbd5e1", bg: "rgba(148,163,184,0.2)" };
  return { color: "#d1d5db", bg: "rgba(148,163,184,0.14)" };
}

export default function BroadcastCampaignPanel({ apiBase, isMobile = false }) {
  const API = (apiBase || "").replace(/\/$/, "");

  const [campaignStatus, setCampaignStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [campaigns, setCampaigns] = useState([]);
  const [statsByCampaign, setStatsByCampaign] = useState({});
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busyMap, setBusyMap] = useState({});

  const [reportOpen, setReportOpen] = useState(false);
  const [reportCampaignId, setReportCampaignId] = useState(0);
  const [reportData, setReportData] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportSearch, setReportSearch] = useState("");
  const [reportStatus, setReportStatus] = useState("all");
  const [reportPage, setReportPage] = useState(1);
  const [reportPerPage, setReportPerPage] = useState(10);

  const filteredCampaigns = useMemo(() => {
    const q = String(search || "").trim().toLowerCase();
    if (!q) return campaigns;
    return (campaigns || []).filter((c) => {
      const name = String(c?.name || "").toLowerCase();
      const objective = String(c?.objective || "").toLowerCase();
      const tpl = String(c?.template_name || "").toLowerCase();
      return name.includes(q) || objective.includes(q) || tpl.includes(q) || String(c?.id || "").includes(q);
    });
  }, [campaigns, search]);

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/api/campaigns?status=${encodeURIComponent(campaignStatus)}&channel=whatsapp`);
      const d = await parseApiResponseSafe(r);
      if (!r.ok) throw new Error(asErrorMessage(d));
      const rows = Array.isArray(d?.campaigns) ? d.campaigns : [];
      setCampaigns(rows);

      const statsPairs = await Promise.all(
        rows.map(async (c) => {
          const id = Number(c?.id || 0);
          if (!id) return [id, null];
          try {
            const sr = await fetch(`${API}/api/campaigns/${encodeURIComponent(id)}/stats`);
            const sd = await parseApiResponseSafe(sr);
            if (!sr.ok) return [id, null];
            return [id, sd || null];
          } catch (_) {
            return [id, null];
          }
        })
      );

      const nextStats = {};
      for (const [id, payload] of statsPairs) {
        if (id > 0 && payload && typeof payload === "object") nextStats[id] = payload;
      }
      setStatsByCampaign(nextStats);
      setStatus("Campanas cargadas.");
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }, [API, campaignStatus]);

  const loadReport = useCallback(
    async ({ campaignId, page = reportPage, perPage = reportPerPage, q = reportSearch, st = reportStatus } = {}) => {
      const id = Number(campaignId || reportCampaignId || 0);
      if (!id) return;
      setReportLoading(true);
      setError("");
      try {
        const url = `${API}/api/campaigns/${encodeURIComponent(id)}/report?status=${encodeURIComponent(st)}&search=${encodeURIComponent(q)}&page=${encodeURIComponent(page)}&per_page=${encodeURIComponent(perPage)}`;
        const r = await fetch(url);
        const d = await parseApiResponseSafe(r);
        if (!r.ok) throw new Error(asErrorMessage(d));
        setReportData(d || null);
      } catch (e) {
        setError(String(e.message || e));
      } finally {
        setReportLoading(false);
      }
    },
    [API, reportCampaignId, reportPage, reportPerPage, reportSearch, reportStatus]
  );

  useEffect(() => {
    loadCampaigns();
  }, [loadCampaigns]);

  useEffect(() => {
    if (!reportOpen || !reportCampaignId) return;
    loadReport({ campaignId: reportCampaignId, page: reportPage, perPage: reportPerPage });
  }, [reportOpen, reportCampaignId, reportPage, reportPerPage, loadReport]);

  const setBusy = (id, action, value) => {
    const key = `${id}:${action}`;
    setBusyMap((prev) => ({ ...prev, [key]: value }));
  };
  const isBusy = (id, action) => !!busyMap[`${id}:${action}`];

  const openReport = async (campaignId) => {
    const id = Number(campaignId || 0);
    if (!id) return;
    setReportCampaignId(id);
    setReportPage(1);
    setReportPerPage(10);
    setReportSearch("");
    setReportStatus("all");
    setReportOpen(true);
    await loadReport({ campaignId: id, page: 1, perPage: 10, q: "", st: "all" });
  };

  const exportCsv = async (campaignId) => {
    const id = Number(campaignId || 0);
    if (!id) return;
    setBusy(id, "csv", true);
    setError("");
    try {
      const r = await fetch(`${API}/api/campaigns/${encodeURIComponent(id)}/export.csv?status=all&search=`);
      if (!r.ok) {
        const d = await parseApiResponseSafe(r);
        throw new Error(asErrorMessage(d));
      }
      const blob = await r.blob();
      const row = (campaigns || []).find((c) => Number(c?.id || 0) === id);
      const name = String(row?.name || `campaign_${id}`).replace(/[^a-zA-Z0-9_-]+/g, "_");
      downloadBlob(blob, `${name}_report.csv`);
      setStatus(`CSV exportado: ${name}_report.csv`);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(id, "csv", false);
    }
  };

  const resendFailed = async (campaignId) => {
    const id = Number(campaignId || 0);
    if (!id) return;
    setBusy(id, "retry", true);
    setError("");
    try {
      const r = await fetch(`${API}/api/campaigns/${encodeURIComponent(id)}/resend-failed?run_now=true&batch_size=150`, { method: "POST" });
      const d = await parseApiResponseSafe(r);
      if (!r.ok) throw new Error(asErrorMessage(d));
      const requeued = Number(d?.requeued || 0);
      setStatus(requeued > 0 ? `Reenvio iniciado para ${requeued} destinatarios fallidos.` : "No habia destinatarios fallidos para reenviar.");
      await loadCampaigns();
      if (reportOpen && reportCampaignId === id) {
        await loadReport({ campaignId: id });
      }
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(id, "retry", false);
    }
  };

  const removeCampaign = async (campaignId) => {
    const id = Number(campaignId || 0);
    if (!id) return;
    const row = (campaigns || []).find((c) => Number(c?.id || 0) === id);
    const label = String(row?.name || `#${id}`);
    const ok = window.confirm(`Se eliminara la campana "${label}" y sus destinatarios.\n\nDeseas continuar?`);
    if (!ok) return;
    setBusy(id, "delete", true);
    setError("");
    try {
      const r = await fetch(`${API}/api/campaigns/${encodeURIComponent(id)}`, { method: "DELETE" });
      const d = await parseApiResponseSafe(r);
      if (!r.ok) throw new Error(asErrorMessage(d));
      if (reportOpen && reportCampaignId === id) setReportOpen(false);
      setStatus(`Campana eliminada: ${label}`);
      await loadCampaigns();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(id, "delete", false);
    }
  };

  const applyReportFilters = async () => {
    setReportPage(1);
    await loadReport({ campaignId: reportCampaignId, page: 1, perPage: reportPerPage, q: reportSearch, st: reportStatus });
  };

  const reportMetrics = reportData?.metrics || {};
  const reportRecipients = reportData?.recipients || {};
  const reportItems = Array.isArray(reportRecipients?.items) ? reportRecipients.items : [];
  const reportCampaign = reportData?.campaign || {};
  const reportRules = reportData?.rules_summary || {};

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={card}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>WhatsApp Broadcasting</h3>
            <div style={{ marginTop: 4, fontSize: 12, opacity: 0.78 }}>Listado de campanas para lanzar, reportar y gestionar resultados.</div>
          </div>
          <button type="button" style={smallBtn} onClick={loadCampaigns} disabled={loading}>
            {loading ? "Cargando..." : "Recargar"}
          </button>
        </div>
      </div>

      {error ? (
        <div style={{ ...card, borderColor: "rgba(231,76,60,0.35)", background: "rgba(231,76,60,0.1)", color: "#ffb7b7", fontSize: 12 }}>
          {error}
        </div>
      ) : null}
      {status ? (
        <div style={{ ...card, borderColor: "rgba(46,204,113,0.35)", background: "rgba(46,204,113,0.1)", color: "#c7ffe0", fontSize: 12 }}>
          {status}
        </div>
      ) : null}

      <div style={card}>
        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "220px 1fr", gap: 8, marginBottom: 10 }}>
          <select style={input} value={campaignStatus} onChange={(e) => setCampaignStatus(e.target.value)}>
            {campaignStatusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                Estado: {opt.label}
              </option>
            ))}
          </select>
          <input style={input} placeholder="Buscar por nombre, objetivo o ID..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>

        <div className="custom-scrollbar" style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 1120 }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.14)" }}>
                <th style={{ padding: "10px 8px" }}>#</th>
                <th style={{ padding: "10px 8px" }}>Campaign name</th>
                <th style={{ padding: "10px 8px" }}>Status</th>
                <th style={{ padding: "10px 8px" }}>Actions</th>
                <th style={{ padding: "10px 8px" }}>Processed</th>
                <th style={{ padding: "10px 8px" }}>Delivered</th>
                <th style={{ padding: "10px 8px" }}>Opened</th>
                <th style={{ padding: "10px 8px" }}>Unreached</th>
                <th style={{ padding: "10px 8px" }}>Scheduled at</th>
              </tr>
            </thead>
            <tbody>
              {filteredCampaigns.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ padding: 14, opacity: 0.74 }}>
                    No hay campanas para este filtro.
                  </td>
                </tr>
              ) : (
                filteredCampaigns.map((c, idx) => {
                  const id = Number(c?.id || 0);
                  const stats = statsByCampaign[id] || {};
                  const total = Number(stats?.total || 0);
                  const pending = Number(stats?.pending || 0);
                  const processing = Number(stats?.processing || 0);
                  const sentOnly = Number(stats?.sent || 0);
                  const deliveredOnly = Number(stats?.delivered || 0);
                  const readOnly = Number(stats?.read || 0);
                  const repliedOnly = Number(stats?.replied || 0);
                  const failed = Number(stats?.failed || 0);
                  const sentTotal = sentOnly + deliveredOnly + readOnly + repliedOnly;
                  const deliveredTotal = deliveredOnly + readOnly + repliedOnly;
                  const openedTotal = readOnly + repliedOnly;
                  const processedTotal = Math.max(0, total - pending - processing);
                  const badge = statusBadge(c?.status);
                  return (
                    <tr key={`bc-${id || idx}`} style={{ borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                      <td style={{ padding: "10px 8px", verticalAlign: "top" }}>{idx + 1}</td>
                      <td style={{ padding: "10px 8px", verticalAlign: "top" }}>
                        <div style={{ fontWeight: 700 }}>{c?.name || "(sin nombre)"}</div>
                        <div style={{ marginTop: 4, fontSize: 12, opacity: 0.78 }}>
                          ID: {id || "-"} | Template: {c?.template_name || "-"}
                        </div>
                      </td>
                      <td style={{ padding: "10px 8px", verticalAlign: "top" }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 6, borderRadius: 999, padding: "4px 10px", background: badge.bg, color: badge.color, fontSize: 12 }}>
                          <span style={{ width: 7, height: 7, borderRadius: "50%", background: badge.color }} />
                          {String(c?.status || "-").toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: "10px 8px", verticalAlign: "top" }}>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          <button type="button" title="Ver reporte" style={smallBtn} onClick={() => openReport(id)} disabled={isBusy(id, "report")}>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>{actionIcon("report")} Reporte</span>
                          </button>
                          <button type="button" title="Exportar CSV" style={smallBtn} onClick={() => exportCsv(id)} disabled={isBusy(id, "csv")}>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>{actionIcon("csv")} CSV</span>
                          </button>
                          <button type="button" title="Reenviar fallidos" style={primaryBtn} onClick={() => resendFailed(id)} disabled={isBusy(id, "retry")}>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>{actionIcon("retry")} Reenviar fallidos</span>
                          </button>
                          <button type="button" title="Eliminar campana" style={dangerBtn} onClick={() => removeCampaign(id)} disabled={isBusy(id, "delete")}>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>{actionIcon("delete")} Borrar</span>
                          </button>
                        </div>
                      </td>
                      <td style={{ padding: "10px 8px", verticalAlign: "top" }}>
                        {progressBlock({
                          label: `Processed (${Math.round(pct(processedTotal, total))}%)`,
                          value: processedTotal,
                          total,
                          color: "#14b8a6",
                          subtitle: `${processedTotal}/${total}`,
                        })}
                      </td>
                      <td style={{ padding: "10px 8px", verticalAlign: "top" }}>
                        {progressBlock({
                          label: `Delivered (${Math.round(pct(deliveredTotal, sentTotal))}%)`,
                          value: deliveredTotal,
                          total: sentTotal || total,
                          color: "#22c55e",
                          subtitle: `${deliveredTotal}/${sentTotal || total}`,
                        })}
                      </td>
                      <td style={{ padding: "10px 8px", verticalAlign: "top" }}>
                        {progressBlock({
                          label: `Opened (${Math.round(pct(openedTotal, deliveredTotal))}%)`,
                          value: openedTotal,
                          total: deliveredTotal || total,
                          color: "#f59e0b",
                          subtitle: `${openedTotal}/${deliveredTotal || total}`,
                        })}
                      </td>
                      <td style={{ padding: "10px 8px", verticalAlign: "top" }}>
                        {progressBlock({
                          label: `Unreached (${Math.round(pct(failed, total))}%)`,
                          value: failed,
                          total,
                          color: "#94a3b8",
                          subtitle: `${failed}/${total}`,
                        })}
                      </td>
                      <td style={{ padding: "10px 8px", verticalAlign: "top", whiteSpace: "nowrap" }}>
                        {fmtDate(c?.scheduled_at)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {reportOpen ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 95,
            background: "rgba(2,6,23,0.52)",
            backdropFilter: "blur(4px)",
            padding: isMobile ? 8 : 18,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <div
            className="custom-scrollbar"
            style={{
              width: "min(1480px, 100%)",
              maxHeight: "92vh",
              overflow: "auto",
              borderRadius: 14,
              border: "1px solid rgba(148,163,184,0.35)",
              background: "linear-gradient(180deg, rgba(15,23,42,0.98), rgba(2,6,23,0.98))",
              boxShadow: "0 30px 60px rgba(0,0,0,0.45)",
            }}
          >
            <div style={{ position: "sticky", top: 0, zIndex: 4, background: "rgba(2,6,23,0.95)", padding: 14, borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                <div>
                  <h3 style={{ margin: 0 }}>Informe de campana</h3>
                  <div style={{ marginTop: 4, fontSize: 12, opacity: 0.78 }}>
                    {reportCampaign?.name || "-"} ({String(reportCampaign?.status || "").toUpperCase() || "-"})
                  </div>
                </div>
                <button type="button" style={smallBtn} onClick={() => setReportOpen(false)}>
                  Cerrar
                </button>
              </div>
            </div>

            <div style={{ padding: 14, display: "grid", gap: 12 }}>
              <div style={{ ...card, display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(3, minmax(0, 1fr))", gap: 8 }}>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Template</div>
                  <div style={{ fontWeight: 700 }}>{reportCampaign?.template_name || "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Included labels</div>
                  <div style={{ fontWeight: 700 }}>{Array.isArray(reportRules?.included_labels) && reportRules.included_labels.length ? reportRules.included_labels.join(", ") : "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Excluded labels</div>
                  <div style={{ fontWeight: 700 }}>{Array.isArray(reportRules?.excluded_labels) && reportRules.excluded_labels.length ? reportRules.excluded_labels.join(", ") : "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Country</div>
                  <div style={{ fontWeight: 700 }}>{reportRules?.country || "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Custom field has value</div>
                  <div style={{ fontWeight: 700 }}>{reportRules?.custom_field_value || "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Asignar etiqueta despues de difusion</div>
                  <div style={{ fontWeight: 700 }}>{reportRules?.assign_label_after_broadcast || "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Anadido despues</div>
                  <div style={{ fontWeight: 700 }}>{reportRules?.added_after || "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Anadido antes</div>
                  <div style={{ fontWeight: 700 }}>{reportRules?.added_before || "N/A"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Recent subscriber filter</div>
                  <div style={{ fontWeight: 700 }}>{reportRules?.recent_subscriber_filter ? "Si" : "No"}</div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(3, minmax(0, 1fr))", gap: 8 }}>
                <div style={{ ...card, textAlign: "center" }}>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Status</div>
                  <div style={{ marginTop: 6, fontSize: 20, fontWeight: 700 }}>{String(reportMetrics?.status || "-").toUpperCase()}</div>
                </div>
                <div style={{ ...card, textAlign: "center" }}>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Targeted</div>
                  <div style={{ marginTop: 6, fontSize: 20, fontWeight: 700 }}>{Number(reportMetrics?.targeted || 0)}</div>
                </div>
                <div style={{ ...card, textAlign: "center" }}>
                  <div style={{ fontSize: 12, opacity: 0.72 }}>Message count</div>
                  <div style={{ marginTop: 6, fontSize: 20, fontWeight: 700 }}>{Number(reportMetrics?.message_count || 0)}</div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(4, minmax(0, 1fr))", gap: 8 }}>
                <div style={card}>
                  {progressBlock({
                    label: "Processed",
                    value: Number(reportMetrics?.processed || 0),
                    total: Number(reportMetrics?.targeted || 0),
                    color: "#14b8a6",
                    subtitle: `Sent ${Math.round(Number(reportMetrics?.sent_pct || 0))}%`,
                  })}
                </div>
                <div style={card}>
                  {progressBlock({
                    label: "Delivered",
                    value: Number(reportMetrics?.delivered || 0),
                    total: Number(reportMetrics?.sent || reportMetrics?.targeted || 0),
                    color: "#22c55e",
                    subtitle: `${Math.round(Number(reportMetrics?.delivered_pct || 0))}%`,
                  })}
                </div>
                <div style={card}>
                  {progressBlock({
                    label: "Opened",
                    value: Number(reportMetrics?.opened || 0),
                    total: Number(reportMetrics?.delivered || reportMetrics?.targeted || 0),
                    color: "#f59e0b",
                    subtitle: `${Math.round(Number(reportMetrics?.opened_pct || 0))}%`,
                  })}
                </div>
                <div style={card}>
                  {progressBlock({
                    label: "Unreached",
                    value: Number(reportMetrics?.unreached || 0),
                    total: Number(reportMetrics?.targeted || 0),
                    color: "#94a3b8",
                    subtitle: `${Math.round(Number(reportMetrics?.unreached_pct || 0))}%`,
                  })}
                </div>
              </div>

              <div style={card}>
                <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 220px 130px auto", gap: 8, marginBottom: 10 }}>
                  <input style={input} placeholder="Buscar..." value={reportSearch} onChange={(e) => setReportSearch(e.target.value)} />
                  <select style={input} value={reportStatus} onChange={(e) => setReportStatus(e.target.value)}>
                    {recipientStatusOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        Recipient status: {opt.label}
                      </option>
                    ))}
                  </select>
                  <select style={input} value={String(reportPerPage)} onChange={(e) => setReportPerPage(Number(e.target.value) || 10)}>
                    {perPageOptions.map((n) => (
                      <option key={n} value={n}>
                        Mostrar {n}
                      </option>
                    ))}
                  </select>
                  <button type="button" style={primaryBtn} onClick={applyReportFilters} disabled={reportLoading}>
                    {reportLoading ? "Cargando..." : "Aplicar"}
                  </button>
                </div>

                <div className="custom-scrollbar" style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 1220 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.14)", textAlign: "left" }}>
                        <th style={{ padding: "9px 8px" }}>#</th>
                        <th style={{ padding: "9px 8px" }}>Chat ID</th>
                        <th style={{ padding: "9px 8px" }}>Name</th>
                        <th style={{ padding: "9px 8px" }}>Status</th>
                        <th style={{ padding: "9px 8px" }}>Sent at</th>
                        <th style={{ padding: "9px 8px" }}>Delivered at</th>
                        <th style={{ padding: "9px 8px" }}>Opened at</th>
                        <th style={{ padding: "9px 8px" }}>Failed at</th>
                        <th style={{ padding: "9px 8px" }}>Message ID</th>
                        <th style={{ padding: "9px 8px" }}>Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportItems.length === 0 ? (
                        <tr>
                          <td colSpan={10} style={{ padding: 12, opacity: 0.72 }}>
                            No hay registros en este filtro.
                          </td>
                        </tr>
                      ) : (
                        reportItems.map((r) => (
                          <tr key={`rp-${r.recipient_id}-${r.index}`} style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                            <td style={{ padding: "10px 8px", whiteSpace: "nowrap" }}>{r.index}</td>
                            <td style={{ padding: "10px 8px", whiteSpace: "nowrap", color: "#2dd4bf" }}>{r.chat_id || "-"}</td>
                            <td style={{ padding: "10px 8px" }}>{r.name || "-"}</td>
                            <td style={{ padding: "10px 8px", textTransform: "capitalize" }}>{String(r.status || "-")}</td>
                            <td style={{ padding: "10px 8px", whiteSpace: "nowrap" }}>{fmtDate(r.sent_at)}</td>
                            <td style={{ padding: "10px 8px", whiteSpace: "nowrap" }}>{fmtDate(r.delivered_at)}</td>
                            <td style={{ padding: "10px 8px", whiteSpace: "nowrap" }}>{fmtDate(r.opened_at)}</td>
                            <td style={{ padding: "10px 8px", whiteSpace: "nowrap" }}>{fmtDate(r.failed_at)}</td>
                            <td style={{ padding: "10px 8px", maxWidth: 280, wordBreak: "break-all", fontSize: 12, opacity: 0.85 }}>{r.message_id || "-"}</td>
                            <td style={{ padding: "10px 8px", maxWidth: 260, wordBreak: "break-word", fontSize: 12, color: r.error ? "#fca5a5" : "inherit" }}>{r.error || "-"}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>

                <div style={{ marginTop: 10, display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <div style={{ fontSize: 12, opacity: 0.78 }}>
                    Mostrando {reportItems.length} de {Number(reportRecipients?.filtered_total || 0)} (total campana {Number(reportRecipients?.total || 0)})
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <button type="button" style={smallBtn} disabled={reportPage <= 1 || reportLoading} onClick={() => setReportPage((p) => Math.max(1, p - 1))}>
                      Anterior
                    </button>
                    <span style={{ fontSize: 12 }}>Pagina {Number(reportRecipients?.page || reportPage)} / {Number(reportRecipients?.pages || 1)}</span>
                    <button
                      type="button"
                      style={smallBtn}
                      disabled={reportLoading || Number(reportRecipients?.page || reportPage) >= Number(reportRecipients?.pages || 1)}
                      onClick={() => setReportPage((p) => p + 1)}
                    >
                      Siguiente
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

