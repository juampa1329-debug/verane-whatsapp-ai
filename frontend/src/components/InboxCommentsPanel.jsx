import React, { useCallback, useEffect, useMemo, useState } from "react";

const CHANNEL_TABS = [
  { id: "all", label: "Todos", short: "ALL" },
  { id: "whatsapp", label: "WhatsApp", short: "WA" },
  { id: "facebook", label: "Facebook", short: "FB" },
  { id: "instagram", label: "Instagram", short: "IG" },
  { id: "tiktok", label: "TikTok", short: "TT" },
];

const COMMENT_STATUSES = [
  { id: "all", label: "Todos" },
  { id: "new", label: "Nuevos" },
  { id: "review", label: "Revision" },
  { id: "replied", label: "Respondidos" },
  { id: "resolved", label: "Resueltos" },
  { id: "ignored", label: "Ignorados" },
  { id: "error", label: "Error" },
];

function normalizeChannel(raw, fallback = "all") {
  const token = String(raw || "").trim().toLowerCase();
  if (["all", "whatsapp", "facebook", "instagram", "tiktok"].includes(token)) return token;
  return fallback;
}

function statusColor(status) {
  const token = String(status || "").toLowerCase();
  if (token === "new") return "#22c55e";
  if (token === "review") return "#f59e0b";
  if (token === "replied") return "#38bdf8";
  if (token === "resolved") return "#a78bfa";
  if (token === "ignored") return "#9ca3af";
  if (token === "error") return "#ef4444";
  return "#94a3b8";
}

function statusLabel(status) {
  const row = COMMENT_STATUSES.find((x) => x.id === String(status || "").toLowerCase());
  return row?.label || String(status || "nuevo");
}

function channelMeta(channel) {
  return CHANNEL_TABS.find((x) => x.id === normalizeChannel(channel, "facebook")) || CHANNEL_TABS[0];
}

async function fetchJson(url, options = {}) {
  const r = await fetch(url, options);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data?.detail || data?.error || `HTTP ${r.status}`);
  return data || {};
}

function cardStyle(active = false) {
  return {
    border: `1px solid ${active ? "rgba(56, 189, 248, 0.38)" : "rgba(255,255,255,0.14)"}`,
    borderRadius: 12,
    background: active ? "rgba(56, 189, 248, 0.1)" : "rgba(255,255,255,0.02)",
    padding: 10,
    textAlign: "left",
    color: "inherit",
    cursor: "pointer",
  };
}

export default function InboxCommentsPanel({ apiBase }) {
  const API = String(apiBase || "").replace(/\/$/, "");

  const [channel, setChannel] = useState("all");
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");

  const [comments, setComments] = useState([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedComment, setSelectedComment] = useState(null);
  const [thread, setThread] = useState([]);
  const [loading, setLoading] = useState(false);
  const [threadLoading, setThreadLoading] = useState(false);

  const [replyText, setReplyText] = useState("");
  const [sendingReply, setSendingReply] = useState(false);
  const [suggestingReply, setSuggestingReply] = useState(false);

  const [triggers, setTriggers] = useState([]);
  const [loadingTriggers, setLoadingTriggers] = useState(false);
  const [savingTrigger, setSavingTrigger] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  const [triggerName, setTriggerName] = useState("Auto respuesta comentarios");
  const [triggerKeywords, setTriggerKeywords] = useState("");
  const [triggerMode, setTriggerMode] = useState("any");
  const [triggerStrategy, setTriggerStrategy] = useState("template"); // template|ai|text
  const [triggerTemplateId, setTriggerTemplateId] = useState("");
  const [triggerReply, setTriggerReply] = useState("");
  const [triggerCooldown, setTriggerCooldown] = useState(45);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const triggerChannel = useMemo(() => {
    const ch = normalizeChannel(channel, "all");
    if (ch === "all" || ch === "whatsapp") return "facebook";
    return ch;
  }, [channel]);

  const loadComments = useCallback(async () => {
    if (!API) return;
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams({
        channel: normalizeChannel(channel, "all"),
        status,
        q: query,
        limit: "200",
        offset: "0",
      });
      const data = await fetchJson(`${API}/api/social/comments?${qs.toString()}`);
      const rows = Array.isArray(data?.comments) ? data.comments : [];
      setComments(rows);
      setTotal(Number(data?.total || 0));
      if (!rows.length) {
        setSelectedId(null);
        setSelectedComment(null);
        setThread([]);
      } else if (!rows.some((x) => x.id === selectedId)) {
        setSelectedId(rows[0].id);
      }
    } catch (e) {
      setError(String(e.message || e));
      setComments([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [API, channel, status, query, selectedId]);

  const loadThread = useCallback(async (id) => {
    if (!API || !id) return;
    setThreadLoading(true);
    setError("");
    try {
      const data = await fetchJson(`${API}/api/social/comments/${encodeURIComponent(id)}`);
      setSelectedComment(data?.comment || null);
      setThread(Array.isArray(data?.thread) ? data.thread : []);
    } catch (e) {
      setError(String(e.message || e));
      setSelectedComment(null);
      setThread([]);
    } finally {
      setThreadLoading(false);
    }
  }, [API]);

  const loadTriggers = useCallback(async () => {
    if (!API) return;
    setLoadingTriggers(true);
    try {
      const data = await fetchJson(`${API}/api/triggers?channel=${encodeURIComponent(triggerChannel)}`);
      const rows = Array.isArray(data?.triggers) ? data.triggers : [];
      setTriggers(rows.filter((x) => String(x?.event_type || "").toLowerCase().startsWith("comment")));
    } catch {
      setTriggers([]);
    } finally {
      setLoadingTriggers(false);
    }
  }, [API, triggerChannel]);

  const loadTemplates = useCallback(async () => {
    if (!API) return;
    setLoadingTemplates(true);
    try {
      const data = await fetchJson(`${API}/api/templates?channel=${encodeURIComponent(triggerChannel)}&status=all`);
      const rows = Array.isArray(data?.templates) ? data.templates : [];
      setTemplates(rows);
      if (rows.length && !rows.some((t) => String(t.id) === String(triggerTemplateId))) {
        setTriggerTemplateId(String(rows[0].id));
      }
      if (!rows.length) setTriggerTemplateId("");
    } catch {
      setTemplates([]);
      setTriggerTemplateId("");
    } finally {
      setLoadingTemplates(false);
    }
  }, [API, triggerChannel, triggerTemplateId]);

  useEffect(() => {
    const timer = setTimeout(loadComments, 200);
    return () => clearTimeout(timer);
  }, [loadComments]);

  useEffect(() => {
    if (selectedId) loadThread(selectedId);
  }, [selectedId, loadThread]);

  useEffect(() => {
    loadTriggers();
    loadTemplates();
  }, [loadTriggers, loadTemplates]);

  const updateCommentStatus = async (nextStatus) => {
    if (!selectedId || !API) return;
    try {
      await fetchJson(`${API}/api/social/comments/${encodeURIComponent(selectedId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      setNotice(`Estado actualizado: ${statusLabel(nextStatus)}`);
      await Promise.all([loadComments(), loadThread(selectedId)]);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const suggestReply = async () => {
    if (!selectedId || !API) return;
    setSuggestingReply(true);
    setError("");
    try {
      const data = await fetchJson(`${API}/api/social/comments/${encodeURIComponent(selectedId)}/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instructions: "" }),
      });
      const text = String(data?.suggestion || "").trim();
      if (text) setReplyText(text);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSuggestingReply(false);
    }
  };

  const sendReply = async () => {
    if (!selectedId || !API) return;
    const txt = String(replyText || "").trim();
    if (!txt) {
      setError("Escribe una respuesta o usa sugerencia IA.");
      return;
    }
    setSendingReply(true);
    setError("");
    try {
      await fetchJson(`${API}/api/social/comments/${encodeURIComponent(selectedId)}/reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: txt, use_ai: false }),
      });
      setReplyText("");
      setNotice("Respuesta enviada.");
      await Promise.all([loadComments(), loadThread(selectedId)]);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSendingReply(false);
    }
  };

  const createCommentTrigger = async () => {
    if (!API) return;
    const name = String(triggerName || "").trim();
    const words = String(triggerKeywords || "")
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

    if (!name) {
      setError("Nombre del trigger requerido.");
      return;
    }
    if (!words.length) {
      setError("Debes agregar al menos una palabra clave.");
      return;
    }
    if (triggerStrategy === "template" && !triggerTemplateId) {
      setError("Selecciona una plantilla para responder comentarios.");
      return;
    }
    if (triggerStrategy === "text" && !String(triggerReply || "").trim()) {
      setError("Agrega el texto fijo de respuesta.");
      return;
    }

    const selectedTemplate = templates.find((x) => String(x.id) === String(triggerTemplateId));
    const action =
      triggerStrategy === "ai"
        ? {
            type: "reply_comment",
            mode: "ai",
            use_ai: true,
            ai_prompt: String(triggerReply || "").trim(),
            reply_text: "",
          }
        : triggerStrategy === "template"
          ? {
              type: "reply_comment",
              mode: "template",
              use_ai: false,
              template_id: Number(triggerTemplateId),
              template_name: String(selectedTemplate?.name || "").trim(),
            }
          : {
              type: "reply_comment",
              mode: "text",
              use_ai: false,
              reply_text: String(triggerReply || "").trim(),
            };

    const payload = {
      name,
      channel: triggerChannel,
      event_type: "comment_in",
      trigger_type: "comment_flow",
      flow_event: "received",
      cooldown_minutes: Math.max(0, Number(triggerCooldown || 0)),
      is_active: true,
      assistant_enabled: false,
      assistant_message_type: "text",
      priority: 100,
      block_ai: false,
      stop_on_match: true,
      only_when_no_takeover: false,
      conditions_json: {
        match: "all",
        conditions: [{ type: "comment_keywords", mode: triggerMode, words }],
      },
      action_json: {
        actions: [action],
      },
    };

    setSavingTrigger(true);
    setError("");
    try {
      await fetchJson(`${API}/api/triggers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setNotice("Trigger de comentarios creado.");
      await loadTriggers();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSavingTrigger(false);
    }
  };

  const toggleTrigger = async (row) => {
    if (!API || !row?.id) return;
    try {
      await fetchJson(`${API}/api/triggers/${encodeURIComponent(row.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !row.is_active, channel: triggerChannel }),
      });
      await loadTriggers();
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  return (
    <div className="inbox-comments-layout custom-scrollbar">
      <div className="inbox-comments-toolbar">
        <div className="inbox-channel-tabs">
          {CHANNEL_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`inbox-channel-tab ${channel === tab.id ? "active" : ""}`}
              onClick={() => setChannel(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="inbox-comment-status-row">
          {COMMENT_STATUSES.map((row) => (
            <button
              key={row.id}
              type="button"
              className={`inbox-comment-status-chip ${status === row.id ? "active" : ""}`}
              onClick={() => setStatus(row.id)}
            >
              {row.label}
            </button>
          ))}
        </div>

        <div className="inbox-comment-search-row">
          <input
            className="inbox-comment-search"
            placeholder="Buscar comentario, autor o ID..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="button" className="inbox-comment-btn" onClick={loadComments}>
            Recargar ({total})
          </button>
        </div>
      </div>

      <div className="inbox-comments-main">
        <div className="inbox-comments-list custom-scrollbar">
          {loading ? <div className="inbox-comments-hint">Cargando comentarios...</div> : null}
          {!loading && !comments.length ? <div className="inbox-comments-hint">No hay comentarios para estos filtros.</div> : null}
          {comments.map((row) => {
            const selected = selectedId === row.id;
            const meta = channelMeta(row.channel);
            return (
              <button
                key={row.id}
                type="button"
                style={cardStyle(selected)}
                onClick={() => setSelectedId(row.id)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                  <strong style={{ fontSize: 12 }}>{row.author_name || row.author_id || "Usuario"}</strong>
                  <span style={{ fontSize: 10, color: statusColor(row.status) }}>{statusLabel(row.status)}</span>
                </div>
                <div style={{ fontSize: 12, opacity: 0.86, marginTop: 4, whiteSpace: "pre-wrap" }}>
                  {String(row.message || "").slice(0, 140) || "(sin texto)"}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
                  <span className={`channel-chip channel-${normalizeChannel(row.channel, "facebook")}`}>{meta.short}</span>
                  <span style={{ fontSize: 10, opacity: 0.66 }}>
                    #{row.external_comment_id} | respuestas: {Number(row.replies_count || 0)}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        <div className="inbox-comments-thread custom-scrollbar">
          {!selectedComment && !threadLoading ? <div className="inbox-comments-hint">Selecciona un comentario.</div> : null}
          {threadLoading ? <div className="inbox-comments-hint">Cargando hilo...</div> : null}
          {selectedComment ? (
            <div style={{ display: "grid", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <div>
                  <strong>{selectedComment.author_name || selectedComment.author_id || "Usuario"}</strong>
                  <div style={{ fontSize: 11, opacity: 0.72 }}>
                    Canal: {channelMeta(selectedComment.channel).label} | ID: {selectedComment.external_comment_id}
                  </div>
                </div>
                <select
                  className="inbox-comment-select"
                  value={String(selectedComment.status || "new")}
                  onChange={(e) => updateCommentStatus(e.target.value)}
                >
                  {COMMENT_STATUSES.filter((x) => x.id !== "all").map((x) => (
                    <option key={x.id} value={x.id}>{x.label}</option>
                  ))}
                </select>
              </div>

              <div className="inbox-comment-root">
                <div style={{ fontSize: 11, opacity: 0.72, marginBottom: 6 }}>Comentario principal</div>
                <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{selectedComment.message || "(sin texto)"}</div>
              </div>

              <div style={{ display: "grid", gap: 8 }}>
                <div style={{ fontSize: 12, opacity: 0.75 }}>Hilo ({thread.length})</div>
                <div className="inbox-comment-thread-scroll custom-scrollbar">
                  {thread.map((item) => (
                    <div
                      key={item.id}
                      style={{
                        border: "1px solid rgba(255,255,255,0.12)",
                        borderRadius: 10,
                        padding: 8,
                        marginBottom: 8,
                        background: item.direction === "out" ? "rgba(46, 204, 113, 0.12)" : "rgba(255,255,255,0.02)",
                      }}
                    >
                      <div style={{ fontSize: 11, opacity: 0.74 }}>
                        {item.direction === "out" ? "Equipo / IA" : (item.author_name || item.author_id || "Usuario")}
                      </div>
                      <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{item.message || "(sin texto)"}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: "grid", gap: 8 }}>
                <textarea
                  className="inbox-comment-textarea"
                  placeholder="Escribe respuesta manual..."
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                />
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button type="button" className="inbox-comment-btn" onClick={suggestReply} disabled={suggestingReply || !selectedId}>
                    {suggestingReply ? "Generando..." : "Sugerir con IA"}
                  </button>
                  <button
                    type="button"
                    className="inbox-comment-btn primary"
                    onClick={sendReply}
                    disabled={sendingReply || !selectedId}
                  >
                    {sendingReply ? "Enviando..." : "Responder comentario"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="inbox-comment-trigger-card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <h3 style={{ margin: 0, fontSize: 14 }}>Triggers de Comentarios</h3>
          <span style={{ fontSize: 11, opacity: 0.75 }}>
            Canal trigger: {channelMeta(triggerChannel).label}
          </span>
        </div>
        <div style={{ fontSize: 12, opacity: 0.78, marginTop: 6 }}>
          Puedes usar plantilla por canal, IA o texto fijo.
        </div>

        <div className="inbox-comment-trigger-grid">
          <input
            className="inbox-comment-search"
            placeholder="Nombre del trigger"
            value={triggerName}
            onChange={(e) => setTriggerName(e.target.value)}
          />
          <input
            className="inbox-comment-search"
            placeholder="Palabras clave (separadas por coma)"
            value={triggerKeywords}
            onChange={(e) => setTriggerKeywords(e.target.value)}
          />
          <select className="inbox-comment-select" value={triggerMode} onChange={(e) => setTriggerMode(e.target.value)}>
            <option value="any">Match por cualquiera</option>
            <option value="all">Match por todas</option>
          </select>
          <input
            className="inbox-comment-search"
            type="number"
            min="0"
            placeholder="Cooldown (min)"
            value={triggerCooldown}
            onChange={(e) => setTriggerCooldown(e.target.value)}
          />
          <select className="inbox-comment-select" value={triggerStrategy} onChange={(e) => setTriggerStrategy(e.target.value)}>
            <option value="template">Responder con plantilla</option>
            <option value="ai">Responder con IA</option>
            <option value="text">Responder con texto fijo</option>
          </select>
          {triggerStrategy === "template" ? (
            <select
              className="inbox-comment-select"
              value={triggerTemplateId}
              onChange={(e) => setTriggerTemplateId(e.target.value)}
              disabled={loadingTemplates}
            >
              <option value="">{loadingTemplates ? "Cargando plantillas..." : "Selecciona plantilla"}</option>
              {templates.map((tpl) => (
                <option key={tpl.id} value={tpl.id}>{tpl.name}</option>
              ))}
            </select>
          ) : (
            <input
              className="inbox-comment-search"
              placeholder={triggerStrategy === "ai" ? "Instrucciones para IA (opcional)" : "Texto fijo de respuesta"}
              value={triggerReply}
              onChange={(e) => setTriggerReply(e.target.value)}
            />
          )}
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
          <button type="button" className="inbox-comment-btn primary" onClick={createCommentTrigger} disabled={savingTrigger}>
            {savingTrigger ? "Guardando..." : "Crear trigger"}
          </button>
          <button type="button" className="inbox-comment-btn" onClick={loadTriggers} disabled={loadingTriggers}>
            {loadingTriggers ? "Cargando..." : "Recargar triggers"}
          </button>
          <button type="button" className="inbox-comment-btn" onClick={loadTemplates} disabled={loadingTemplates}>
            {loadingTemplates ? "Cargando..." : "Recargar plantillas"}
          </button>
        </div>

        <div style={{ display: "grid", gap: 8, marginTop: 10 }}>
          {!triggers.length ? (
            <div className="inbox-comments-hint">No hay triggers de comentarios para este canal.</div>
          ) : (
            triggers.map((t) => (
              <div key={t.id} className="inbox-comment-trigger-item">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                  <strong style={{ fontSize: 13 }}>{t.name}</strong>
                  <button type="button" className="inbox-comment-btn" onClick={() => toggleTrigger(t)}>
                    {t.is_active ? "Desactivar" : "Activar"}
                  </button>
                </div>
                <div style={{ fontSize: 11, opacity: 0.72, marginTop: 4 }}>
                  evento: {t.event_type} | tipo: {t.trigger_type} | cooldown: {t.cooldown_minutes} min
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {error ? <div className="inbox-comments-error">{error}</div> : null}
      {notice ? <div className="inbox-comments-ok">{notice}</div> : null}
    </div>
  );
}

