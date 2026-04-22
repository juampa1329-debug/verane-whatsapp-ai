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
const scheduleModeOptions = [
  { value: "draft", label: "Guardar como draft" },
  { value: "scheduled", label: "Programar para envio" },
];

function emptyCreateForm() {
  return {
    name: "",
    meta_template_name: "",
    meta_template_language: "",
    meta_template_category: "",
    meta_template_body: "",
    segment_id: "",
    scheduled_at: "",
    mode: "draft",
    is_mockup: true,
  };
}

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

function extractTemplateTokens(body) {
  const txt = String(body || "");
  const seen = new Set();
  const out = [];
  const regex = /\{\{\s*([^{}]+?)\s*\}\}/g;
  let match = regex.exec(txt);
  while (match) {
    const token = String(match[1] || "").trim();
    if (token && !seen.has(token)) {
      seen.add(token);
      out.push(token);
    }
    match = regex.exec(txt);
  }
  return out;
}

function buildMockRecipients(total = 202) {
  const base = [];
  const start = 573010000000;
  for (let i = 0; i < total; i += 1) {
    const phone = String(start + i);
    const status = i < 118 ? "read" : i < 195 ? "delivered" : i < 198 ? "sent" : "failed";
    const sentAt = new Date(Date.now() - (total - i) * 60000);
    base.push({
      recipient_id: i + 1,
      chat_id: phone,
      name: i % 3 === 0 ? `Cliente ${i + 1}` : "",
      status,
      sent_at: sentAt.toISOString(),
      delivered_at: status === "read" || status === "delivered" ? new Date(sentAt.getTime() + 8000).toISOString() : null,
      opened_at: status === "read" ? new Date(sentAt.getTime() + 19000).toISOString() : null,
      replied_at: null,
      failed_at: status === "failed" ? new Date(sentAt.getTime() + 6000).toISOString() : null,
      message_id: `wamid.mock.${i + 1}.${Date.now()}`,
      error: status === "failed" ? "Error mockup de prueba (sin envio real)." : "",
    });
  }
  return base;
}

function buildMockReportPayload(campaign, stats, { page = 1, perPage = 10, search = "", recipientStatus = "all" } = {}) {
  const rows = Array.isArray(campaign?.__mockRecipients) ? campaign.__mockRecipients : [];
  const q = String(search || "").trim().toLowerCase();
  const st = String(recipientStatus || "all").toLowerCase();
  let filtered = rows;
  if (st !== "all") {
    filtered = filtered.filter((r) => String(r?.status || "").toLowerCase() === st);
  }
  if (q) {
    filtered = filtered.filter((r) => {
      const chatId = String(r?.chat_id || "").toLowerCase();
      const name = String(r?.name || "").toLowerCase();
      const messageId = String(r?.message_id || "").toLowerCase();
      return chatId.includes(q) || name.includes(q) || messageId.includes(q);
    });
  }

  const total = Number(stats?.total || rows.length || 0);
  const safePerPage = Math.max(1, Number(perPage || 10));
  const safePage = Math.max(1, Number(page || 1));
  const offset = (safePage - 1) * safePerPage;
  const paged = filtered.slice(offset, offset + safePerPage).map((r, idx) => ({ ...r, index: offset + idx + 1 }));
  const pages = Math.max(1, Math.ceil(filtered.length / safePerPage));

  return {
    campaign: {
      id: campaign?.id,
      name: campaign?.name || "Mockup broadcast",
      objective: campaign?.objective || "",
      status: campaign?.status || "draft",
      scheduled_at: campaign?.scheduled_at || null,
      launched_at: null,
      channel: "whatsapp",
      template_id: null,
      template_name: campaign?.template_name || "",
      meta_template_name: campaign?.meta_template_name || "",
      meta_template_language: campaign?.meta_template_language || "",
      meta_template_category: campaign?.meta_template_category || "",
      meta_template_body: campaign?.meta_template_body || "",
      segment_id: null,
      segment_name: campaign?.segment_name || "Mock segment",
    },
    rules_summary: {
      included_labels: ["mock", "prueba"],
      excluded_labels: [],
      country: "CO",
      custom_field_value: "N/A",
      added_after: "N/A",
      added_before: "N/A",
      assign_label_after_broadcast: "N/A",
      recent_subscriber_filter: false,
    },
    metrics: {
      status: campaign?.status || "draft",
      targeted: total,
      message_count: 1,
      processed: Number(stats?.processed || 0),
      processed_pct: Number(stats?.processed_pct || 0),
      sent: Number(stats?.sent || 0),
      sent_pct: Number(stats?.sent_pct || 0),
      delivered: Number(stats?.delivered || 0),
      delivered_pct: Number(stats?.delivered_pct || 0),
      opened: Number(stats?.read || 0),
      opened_pct: Number(stats?.read_rate_pct || 0),
      unreached: Number(stats?.failed || 0),
      unreached_pct: pct(Number(stats?.failed || 0), total),
      pending: Number(stats?.pending || 0),
      processing: Number(stats?.processing || 0),
      failed: Number(stats?.failed || 0),
    },
    recipients: {
      page: safePage,
      per_page: safePerPage,
      total,
      filtered_total: filtered.length,
      pages,
      items: paged,
    },
  };
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

  const [createOpen, setCreateOpen] = useState(false);
  const [createSaving, setCreateSaving] = useState(false);
  const [createForm, setCreateForm] = useState(emptyCreateForm);
  const [metaTemplates, setMetaTemplates] = useState([]);
  const [segments, setSegments] = useState([]);
  const [loadingCreateDeps, setLoadingCreateDeps] = useState(false);
  const [mockCampaigns, setMockCampaigns] = useState([]);
  const [mockStatsByCampaign, setMockStatsByCampaign] = useState({});

  const filteredCampaigns = useMemo(() => {
    const allRows = [...(mockCampaigns || []), ...(campaigns || [])];
    const q = String(search || "").trim().toLowerCase();
    if (!q) return allRows;
    return allRows.filter((c) => {
      const name = String(c?.name || "").toLowerCase();
      const objective = String(c?.objective || "").toLowerCase();
      const tpl = String(c?.template_name || "").toLowerCase();
      return name.includes(q) || objective.includes(q) || tpl.includes(q) || String(c?.id || "").includes(q);
    });
  }, [campaigns, mockCampaigns, search]);

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

  const loadCreateDependencies = useCallback(async () => {
    setLoadingCreateDeps(true);
    setError("");
    try {
      const [tplResp, segResp] = await Promise.all([
        fetch(`${API}/api/broadcast/meta/templates?limit=300`),
        fetch(`${API}/api/customers/segments`),
      ]);
      const [tplData, segData] = await Promise.all([parseApiResponseSafe(tplResp), parseApiResponseSafe(segResp)]);
      if (!tplResp.ok) throw new Error(asErrorMessage(tplData));
      if (!segResp.ok) throw new Error(asErrorMessage(segData));
      const tplRows = (Array.isArray(tplData?.templates) ? tplData.templates : []).filter(
        (t) => String(t?.status || "").toLowerCase() === "approved"
      );
      const segRows = Array.isArray(segData?.segments) ? segData.segments : [];
      setMetaTemplates(tplRows);
      setSegments(segRows);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoadingCreateDeps(false);
    }
  }, [API]);

  const openCreateModal = async () => {
    setCreateOpen(true);
    setCreateForm(emptyCreateForm());
    await loadCreateDependencies();
  };

  const closeCreateModal = () => {
    setCreateOpen(false);
    setCreateForm(emptyCreateForm());
  };

  const loadReport = useCallback(
    async ({ campaignId, page = reportPage, perPage = reportPerPage, q = reportSearch, st = reportStatus } = {}) => {
      const id = Number(campaignId || reportCampaignId || 0);
      if (!id) return;
      if (id < 0) {
        const mockRow = (mockCampaigns || []).find((c) => Number(c?.id || 0) === id) || null;
        const mockStats = mockStatsByCampaign[id] || {};
        if (mockRow) {
          const mockPayload = buildMockReportPayload(mockRow, mockStats, {
            page,
            perPage,
            search: q,
            recipientStatus: st,
          });
          setReportData(mockPayload);
          return;
        }
      }
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
    [API, reportCampaignId, reportPage, reportPerPage, reportSearch, reportStatus, mockCampaigns, mockStatsByCampaign]
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

  const createCampaign = async () => {
    const name = String(createForm.name || "").trim();
    const tplName = String(createForm.meta_template_name || "").trim();
    if (!name) {
      setError("Debes indicar nombre de campana.");
      return;
    }
    if (!tplName) {
      setError("Debes seleccionar una plantilla Meta aprobada.");
      return;
    }

    const selectedTemplate = (metaTemplates || []).find((t) => String(t?.name || "").trim() === tplName) || null;
    if (!selectedTemplate) {
      setError("No se encontro la plantilla seleccionada en Meta.");
      return;
    }

    const mode = String(createForm.mode || "draft").toLowerCase();
    const shouldSchedule = mode === "scheduled";
    const scheduledRaw = String(createForm.scheduled_at || "").trim();
    if (shouldSchedule && !scheduledRaw) {
      setError("Debes seleccionar fecha y hora para una campana programada.");
      return;
    }

    const scheduledAtIso = shouldSchedule ? new Date(scheduledRaw).toISOString() : null;
    if (shouldSchedule && (!scheduledAtIso || scheduledAtIso === "Invalid Date")) {
      setError("Fecha de programacion invalida.");
      return;
    }

    setCreateSaving(true);
    setError("");
    try {
      if (createForm.is_mockup) {
        const mockId = -Date.now();
        const mockRecipients = buildMockRecipients(202);
        const mockRow = {
          id: mockId,
          name,
          objective: `[MOCKUP] ${String(selectedTemplate?.body_text || "").slice(0, 120)}`,
          status: shouldSchedule ? "scheduled" : "draft",
          scheduled_at: scheduledAtIso,
          launched_at: null,
          channel: "whatsapp",
          template_name: "",
          meta_template_name: String(selectedTemplate?.name || ""),
          meta_template_language: String(selectedTemplate?.language || "es"),
          meta_template_category: String(selectedTemplate?.category || "MARKETING"),
          meta_template_body: String(selectedTemplate?.body_text || ""),
          __mock: true,
          __mockRecipients: mockRecipients,
        };
        const mockStats = {
          total: 202,
          pending: 0,
          processing: 0,
          sent: 3,
          delivered: 77,
          read: 118,
          replied: 0,
          failed: 4,
          sent_pct: 100,
          delivered_pct: 97,
          read_rate_pct: 61,
          reply_rate_pct: 0,
          coverage_pct: 100,
          processed: 202,
          processed_pct: 100,
        };

        setMockCampaigns((prev) => [mockRow, ...prev]);
        setMockStatsByCampaign((prev) => ({ ...prev, [mockId]: mockStats }));
        setStatus("Mockup creado (sin envio real, sin costo).");
        closeCreateModal();
        return;
      }

      const payload = {
        name,
        objective: `[META_TEMPLATE] ${String(selectedTemplate?.name || "")}`,
        segment_id: createForm.segment_id ? Number(createForm.segment_id) : null,
        template_id: null,
        meta_template_name: String(selectedTemplate?.name || ""),
        meta_template_language: String(selectedTemplate?.language || "es"),
        meta_template_category: String(selectedTemplate?.category || "MARKETING"),
        meta_template_body: String(selectedTemplate?.body_text || ""),
        status: shouldSchedule ? "scheduled" : "draft",
        scheduled_at: shouldSchedule ? scheduledAtIso : null,
        channel: "whatsapp",
      };
      const r = await fetch(`${API}/api/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await parseApiResponseSafe(r);
      if (!r.ok) throw new Error(asErrorMessage(d));
      setStatus("Campana creada. Quedo registrada con plantilla Meta.");
      closeCreateModal();
      await loadCampaigns();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setCreateSaving(false);
    }
  };

  const exportCsv = async (campaignId) => {
    const id = Number(campaignId || 0);
    if (!id) return;
    setBusy(id, "csv", true);
    setError("");
    try {
      if (id < 0) {
        const mockRow = (mockCampaigns || []).find((c) => Number(c?.id || 0) === id) || null;
        const mockStats = mockStatsByCampaign[id] || {};
        if (!mockRow) throw new Error("Mockup no encontrado.");
        const payload = buildMockReportPayload(mockRow, mockStats, { page: 1, perPage: 1000, search: "", recipientStatus: "all" });
        const items = Array.isArray(payload?.recipients?.items) ? payload.recipients.items : [];
        const lines = [
          ["#", "Chat ID", "Nombre", "Status", "Sent at", "Delivered at", "Opened at", "Failed at", "Message ID", "Error"].join(","),
          ...items.map((r) =>
            [
              r.index,
              r.chat_id,
              String(r.name || "").replace(/,/g, " "),
              r.status,
              fmtDate(r.sent_at),
              fmtDate(r.delivered_at),
              fmtDate(r.opened_at),
              fmtDate(r.failed_at),
              String(r.message_id || "").replace(/,/g, " "),
              String(r.error || "").replace(/,/g, " "),
            ].join(",")
          ),
        ];
        const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
        const name = String(mockRow?.name || `mock_${Math.abs(id)}`).replace(/[^a-zA-Z0-9_-]+/g, "_");
        downloadBlob(blob, `${name}_report_mock.csv`);
        setStatus(`CSV mock exportado: ${name}_report_mock.csv`);
        return;
      }

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
      if (id < 0) {
        setStatus("Mockup: reenviar fallidos simulado (sin envio real).");
        return;
      }

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
    const row = [...(mockCampaigns || []), ...(campaigns || [])].find((c) => Number(c?.id || 0) === id);
    const label = String(row?.name || `#${id}`);
    const ok = window.confirm(`Se eliminara la campana "${label}" y sus destinatarios.\n\nDeseas continuar?`);
    if (!ok) return;
    setBusy(id, "delete", true);
    setError("");
    try {
      if (id < 0) {
        setMockCampaigns((prev) => prev.filter((c) => Number(c?.id || 0) !== id));
        setMockStatsByCampaign((prev) => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
        if (reportOpen && reportCampaignId === id) setReportOpen(false);
        setStatus(`Mockup eliminado: ${label}`);
        return;
      }

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
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" style={primaryBtn} onClick={openCreateModal}>
              + Crear campana
            </button>
            <button type="button" style={smallBtn} onClick={loadCampaigns} disabled={loading}>
              {loading ? "Cargando..." : "Recargar"}
            </button>
          </div>
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
                  const stats = id < 0 ? mockStatsByCampaign[id] || {} : statsByCampaign[id] || {};
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

      {createOpen ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 96,
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
              width: "min(980px, 100%)",
              maxHeight: "92vh",
              overflow: "auto",
              borderRadius: 14,
              border: "1px solid rgba(148,163,184,0.35)",
              background: "linear-gradient(180deg, rgba(15,23,42,0.98), rgba(2,6,23,0.98))",
              boxShadow: "0 30px 60px rgba(0,0,0,0.45)",
              padding: 14,
              display: "grid",
              gap: 12,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <div>
                <h3 style={{ margin: 0 }}>Crear campana masiva</h3>
                <div style={{ marginTop: 4, fontSize: 12, opacity: 0.78 }}>
                  Configura campana con plantilla Meta aprobada. Puedes crear mockup sin costo real.
                </div>
              </div>
              <button type="button" style={smallBtn} onClick={closeCreateModal}>
                Cerrar
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 8 }}>
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Nombre de campana *</div>
                <input
                  style={input}
                  placeholder="Promo mayo mayorista"
                  value={createForm.name}
                  onChange={(e) => setCreateForm((p) => ({ ...p, name: e.target.value }))}
                />
              </label>
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Plantilla Meta aprobada *</div>
                <select
                  style={input}
                  value={createForm.meta_template_name}
                  onChange={(e) => {
                    const nextName = e.target.value;
                    const tpl = (metaTemplates || []).find((t) => String(t?.name || "").trim() === String(nextName || "").trim()) || null;
                    setCreateForm((p) => ({
                      ...p,
                      meta_template_name: nextName,
                      meta_template_language: String(tpl?.language || ""),
                      meta_template_category: String(tpl?.category || ""),
                      meta_template_body: String(tpl?.body_text || ""),
                    }));
                  }}
                  disabled={loadingCreateDeps}
                >
                  <option value="">{loadingCreateDeps ? "Cargando plantillas..." : "Seleccionar plantilla"}</option>
                  {(metaTemplates || []).map((t) => (
                    <option key={`${t.id || t.name}`} value={t.name}>
                      {t.name} ({String(t.category || "").toUpperCase()} / {String(t.language || "").toLowerCase()})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Segmento de audiencia</div>
                <select
                  style={input}
                  value={createForm.segment_id}
                  onChange={(e) => setCreateForm((p) => ({ ...p, segment_id: e.target.value }))}
                  disabled={loadingCreateDeps}
                >
                  <option value="">Sin segmento (usar logica por defecto)</option>
                  {(segments || []).map((s) => (
                    <option key={s.id} value={String(s.id)}>
                      {s.name || `Segmento ${s.id}`}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Modo</div>
                <select style={input} value={createForm.mode} onChange={(e) => setCreateForm((p) => ({ ...p, mode: e.target.value }))}>
                  {scheduleModeOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
              {String(createForm.mode || "") === "scheduled" ? (
                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Fecha y hora programada *</div>
                  <input
                    style={input}
                    type="datetime-local"
                    value={createForm.scheduled_at}
                    onChange={(e) => setCreateForm((p) => ({ ...p, scheduled_at: e.target.value }))}
                  />
                </label>
              ) : null}
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
              <input
                type="checkbox"
                checked={!!createForm.is_mockup}
                onChange={(e) => setCreateForm((p) => ({ ...p, is_mockup: e.target.checked }))}
              />
              Crear como mockup de prueba (sin envio real ni costo)
            </label>

            <div style={card}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
                <strong>Vista de plantilla</strong>
                {createForm.meta_template_category ? (
                  <span style={{ border: "1px solid rgba(125,211,252,0.35)", borderRadius: 999, padding: "2px 8px", fontSize: 11 }}>
                    {String(createForm.meta_template_category || "").toUpperCase()}
                  </span>
                ) : null}
                {createForm.meta_template_language ? (
                  <span style={{ border: "1px solid rgba(255,255,255,0.2)", borderRadius: 999, padding: "2px 8px", fontSize: 11 }}>
                    {String(createForm.meta_template_language || "").toLowerCase()}
                  </span>
                ) : null}
              </div>
              <div style={{ fontSize: 12, opacity: 0.84, whiteSpace: "pre-wrap" }}>
                {String(createForm.meta_template_body || "").trim() || "Selecciona una plantilla para ver su contenido."}
              </div>
              <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
                {extractTemplateTokens(createForm.meta_template_body).length ? (
                  extractTemplateTokens(createForm.meta_template_body).map((tk) => (
                    <span key={tk} style={{ border: "1px solid rgba(148,163,184,0.35)", borderRadius: 999, padding: "2px 8px", fontSize: 11 }}>
                      {"{{"}{tk}{"}}"}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: 11, opacity: 0.7 }}>Sin variables detectadas en esta plantilla.</span>
                )}
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" style={primaryBtn} onClick={createCampaign} disabled={createSaving}>
                {createSaving ? "Guardando..." : createForm.is_mockup ? "Crear mockup de prueba" : "Crear campana"}
              </button>
              <button type="button" style={smallBtn} onClick={() => setCreateForm(emptyCreateForm())} disabled={createSaving}>
                Limpiar
              </button>
            </div>
          </div>
        </div>
      ) : null}

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
