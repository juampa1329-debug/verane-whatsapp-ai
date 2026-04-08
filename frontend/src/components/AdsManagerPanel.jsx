import React, { useCallback, useEffect, useMemo, useState } from "react";
import useViewport from "../hooks/useViewport";

const API_DEFAULT = import.meta.env.VITE_API_BASE || "";

const box = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  background: "rgba(255,255,255,0.02)",
  padding: 12,
};

const chip = {
  padding: "8px 12px",
  borderRadius: 999,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 700,
};

const actionBtn = {
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.2)",
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
  fontSize: 12,
};

const input = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.16)",
  background: "rgba(255,255,255,0.02)",
  color: "inherit",
};

const CHANNELS = [
  { id: "facebook", label: "Facebook" },
  { id: "instagram", label: "Instagram" },
  { id: "tiktok", label: "TikTok" },
];

const MODULES = [
  { id: "ads", label: "Campanas Ads" },
  { id: "comments", label: "Comentarios" },
  { id: "dm", label: "Mensajeria Directa" },
  { id: "automation", label: "IA Trafficker" },
  { id: "audit", label: "Auditoria" },
];

const COMMENT_STATUSES = [
  { id: "all", label: "Todos" },
  { id: "new", label: "Nuevos" },
  { id: "review", label: "En revision" },
  { id: "replied", label: "Respondidos" },
  { id: "resolved", label: "Resueltos" },
  { id: "ignored", label: "Ignorados" },
  { id: "error", label: "Error" },
];

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
  const item = COMMENT_STATUSES.find((x) => x.id === String(status || "").toLowerCase());
  if (item) return item.label;
  return String(status || "nuevo");
}

async function fetchJson(url, options = {}) {
  const r = await fetch(url, options);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(data?.detail || data?.error || `HTTP ${r.status}`);
  }
  return data || {};
}

function ModuleIntro({ channel, moduleId }) {
  const text = useMemo(() => {
    if (moduleId === "ads") {
      return "Control de campanas publicitarias con aprobacion humana, presupuesto, objetivo, audiencias y reglas de seguridad.";
    }
    if (moduleId === "comments") {
      return "Bandeja para responder comentarios de publicaciones y anuncios, con sugerencia IA y triggers automáticos por palabras clave.";
    }
    if (moduleId === "dm") {
      return "Bandeja de mensajes directos por red social con soporte de adjuntos, historial y handoff humano.";
    }
    if (moduleId === "automation") {
      return "Panel de instrucciones para IA trafficker: metas, limites de CPA/CPL, tests A/B y ventanas horarias.";
    }
    return "Trazabilidad de acciones IA y usuario: cambios de presupuesto, publicaciones, respuestas y alertas.";
  }, [moduleId]);

  return (
    <div style={box}>
      <h3 style={{ marginTop: 0, marginBottom: 8 }}>
        {channel} - {MODULES.find((m) => m.id === moduleId)?.label}
      </h3>
      <p style={{ marginTop: 0, opacity: 0.86, fontSize: 13 }}>{text}</p>
      <div style={{ display: "grid", gap: 8 }}>
        <div style={{ fontSize: 12, opacity: 0.78 }}>Estado: modulo preparado para escalar por canal.</div>
        <div style={{ fontSize: 12, opacity: 0.78 }}>Permisos: lectura y escritura por token por red social.</div>
        <div style={{ fontSize: 12, opacity: 0.78 }}>Seguridad: auditoria y aprobacion para acciones criticas.</div>
      </div>
    </div>
  );
}

function CommentsModule({ apiBase, channel, isMobile }) {
  const API = String(apiBase || API_DEFAULT || "").replace(/\/$/, "");

  const [comments, setComments] = useState([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedComment, setSelectedComment] = useState(null);
  const [thread, setThread] = useState([]);
  const [loading, setLoading] = useState(false);
  const [threadLoading, setThreadLoading] = useState(false);
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");
  const [replyText, setReplyText] = useState("");
  const [sendingReply, setSendingReply] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [triggers, setTriggers] = useState([]);
  const [loadingTriggers, setLoadingTriggers] = useState(false);
  const [savingTrigger, setSavingTrigger] = useState(false);
  const [triggerName, setTriggerName] = useState("Auto respuesta comentarios");
  const [triggerKeywords, setTriggerKeywords] = useState("");
  const [triggerMode, setTriggerMode] = useState("any");
  const [triggerUseAI, setTriggerUseAI] = useState(true);
  const [triggerReply, setTriggerReply] = useState("");
  const [triggerCooldown, setTriggerCooldown] = useState(45);

  const loadComments = useCallback(async () => {
    if (!API) return;
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams({
        channel,
        status,
        q: query,
        limit: "150",
        offset: "0",
      });
      const data = await fetchJson(`${API}/api/social/comments?${qs.toString()}`);
      const list = Array.isArray(data?.comments) ? data.comments : [];
      setComments(list);
      setTotal(Number(data?.total || 0));
      if (!list.length) {
        setSelectedId(null);
        setSelectedComment(null);
        setThread([]);
      } else if (!list.some((x) => x.id === selectedId)) {
        setSelectedId(list[0].id);
      }
    } catch (e) {
      setError(String(e.message || e));
      setComments([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [API, channel, status, query, selectedId]);

  const loadTriggers = useCallback(async () => {
    if (!API) return;
    setLoadingTriggers(true);
    try {
      const data = await fetchJson(`${API}/api/triggers?channel=${encodeURIComponent(channel)}`);
      const rows = Array.isArray(data?.triggers) ? data.triggers : [];
      const commentOnly = rows.filter((r) => String(r?.event_type || "").toLowerCase().startsWith("comment"));
      setTriggers(commentOnly);
    } catch {
      setTriggers([]);
    } finally {
      setLoadingTriggers(false);
    }
  }, [API, channel]);

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

  useEffect(() => {
    const timer = setTimeout(() => {
      loadComments();
    }, 220);
    return () => clearTimeout(timer);
  }, [loadComments]);

  useEffect(() => {
    loadTriggers();
  }, [loadTriggers]);

  useEffect(() => {
    if (selectedId) loadThread(selectedId);
  }, [selectedId, loadThread]);

  const setCommentStatus = async (nextStatus) => {
    if (!selectedId || !API) return;
    try {
      await fetchJson(`${API}/api/social/comments/${encodeURIComponent(selectedId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      setNotice(`Estado actualizado a ${statusLabel(nextStatus)}`);
      await Promise.all([loadComments(), loadThread(selectedId)]);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const requestSuggestion = async () => {
    if (!selectedId || !API) return;
    setSuggesting(true);
    setError("");
    try {
      const data = await fetchJson(`${API}/api/social/comments/${encodeURIComponent(selectedId)}/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instructions: triggerUseAI ? triggerReply : "" }),
      });
      const suggestion = String(data?.suggestion || "").trim();
      if (suggestion) setReplyText(suggestion);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSuggesting(false);
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
    if (channel === "tiktok") {
      setError("Auto respuesta de comentarios en TikTok aun no esta disponible en este backend.");
      return;
    }
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
    if (!triggerUseAI && !String(triggerReply || "").trim()) {
      setError("Si no usas IA, agrega texto de respuesta.");
      return;
    }

    setSavingTrigger(true);
    setError("");
    try {
      const payload = {
        name,
        channel,
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
          actions: [
            {
              type: "reply_comment",
              mode: triggerUseAI ? "ai" : "text",
              use_ai: !!triggerUseAI,
              reply_text: triggerUseAI ? "" : String(triggerReply || "").trim(),
              ai_prompt: triggerUseAI ? String(triggerReply || "").trim() : "",
            },
          ],
        },
      };

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
        body: JSON.stringify({ is_active: !row.is_active, channel }),
      });
      await loadTriggers();
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ ...box, paddingBottom: 10 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
          {COMMENT_STATUSES.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setStatus(s.id)}
              style={{
                ...chip,
                padding: "6px 10px",
                fontSize: 11,
                background: status === s.id ? "rgba(46, 204, 113, 0.16)" : "transparent",
                borderColor: status === s.id ? "rgba(46, 204, 113, 0.35)" : "rgba(255,255,255,0.16)",
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr auto", gap: 8 }}>
          <input
            style={input}
            placeholder="Buscar comentario, autor o id..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button style={actionBtn} type="button" onClick={loadComments}>
            Recargar ({total})
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "300px 1fr", gap: 12, minHeight: 360 }}>
        <div style={{ ...box, minHeight: 0, maxHeight: isMobile ? "none" : 520, overflowY: "auto" }}>
          {loading ? <div style={{ fontSize: 12, opacity: 0.8 }}>Cargando comentarios...</div> : null}
          {!loading && !comments.length ? <div style={{ fontSize: 12, opacity: 0.8 }}>No hay comentarios para estos filtros.</div> : null}
          <div style={{ display: "grid", gap: 8 }}>
            {comments.map((c) => {
              const active = selectedId === c.id;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setSelectedId(c.id)}
                  style={{
                    textAlign: "left",
                    ...actionBtn,
                    borderColor: active ? "rgba(52, 152, 219, 0.5)" : "rgba(255,255,255,0.14)",
                    background: active ? "rgba(52, 152, 219, 0.12)" : "rgba(255,255,255,0.01)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                    <strong style={{ fontSize: 12 }}>{c.author_name || c.author_id || "Usuario"}</strong>
                    <span style={{ fontSize: 10, color: statusColor(c.status) }}>{statusLabel(c.status)}</span>
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.86, marginTop: 4, whiteSpace: "pre-wrap" }}>
                    {String(c.message || "").slice(0, 120) || "(sin texto)"}
                  </div>
                  <div style={{ fontSize: 10, opacity: 0.66, marginTop: 4 }}>
                    #{c.external_comment_id} · respuestas: {Number(c.replies_count || 0)}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ ...box, minHeight: 0, maxHeight: isMobile ? "none" : 520, overflowY: "auto" }}>
          {!selectedComment && !threadLoading ? <div style={{ fontSize: 12, opacity: 0.8 }}>Selecciona un comentario.</div> : null}
          {threadLoading ? <div style={{ fontSize: 12, opacity: 0.8 }}>Cargando hilo...</div> : null}
          {selectedComment ? (
            <div style={{ display: "grid", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <div>
                  <strong>{selectedComment.author_name || selectedComment.author_id || "Usuario"}</strong>
                  <div style={{ fontSize: 11, opacity: 0.7 }}>Canal: {selectedComment.channel} · ID: {selectedComment.external_comment_id}</div>
                </div>
                <select
                  style={{ ...input, width: 170, padding: "7px 9px" }}
                  value={String(selectedComment.status || "new")}
                  onChange={(e) => setCommentStatus(e.target.value)}
                >
                  {COMMENT_STATUSES.filter((s) => s.id !== "all").map((s) => (
                    <option key={s.id} value={s.id}>{s.label}</option>
                  ))}
                </select>
              </div>

              <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10, background: "rgba(255,255,255,0.02)" }}>
                <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 6 }}>Comentario principal</div>
                <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{selectedComment.message || "(sin texto)"}</div>
              </div>

              <div style={{ display: "grid", gap: 8 }}>
                <div style={{ fontSize: 12, opacity: 0.75 }}>Hilo ({thread.length})</div>
                <div style={{ maxHeight: 210, overflowY: "auto", display: "grid", gap: 8 }}>
                  {thread.map((m) => (
                    <div
                      key={m.id}
                      style={{
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 10,
                        padding: 8,
                        background: m.direction === "out" ? "rgba(46, 204, 113, 0.1)" : "rgba(255,255,255,0.02)",
                      }}
                    >
                      <div style={{ fontSize: 11, opacity: 0.75 }}>
                        {m.direction === "out" ? "Tu equipo / IA" : (m.author_name || m.author_id || "Usuario")} · {m.direction}
                      </div>
                      <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{m.message || "(sin texto)"}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: "grid", gap: 8 }}>
                <textarea
                  style={{ ...input, minHeight: 96 }}
                  placeholder="Escribe respuesta manual..."
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                />
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button style={actionBtn} type="button" onClick={requestSuggestion} disabled={suggesting || !selectedId}>
                    {suggesting ? "Generando..." : "Sugerir con IA"}
                  </button>
                  <button
                    style={{
                      ...actionBtn,
                      background: "rgba(46, 204, 113, 0.2)",
                      borderColor: "rgba(46, 204, 113, 0.35)",
                    }}
                    type="button"
                    onClick={sendReply}
                    disabled={sendingReply || !selectedId || channel === "tiktok"}
                  >
                    {sendingReply ? "Enviando..." : "Responder comentario"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div style={box}>
        <h3 style={{ marginTop: 0, marginBottom: 8 }}>Triggers de Comentarios</h3>
        <div style={{ fontSize: 12, opacity: 0.78, marginBottom: 10 }}>
          Regla recomendada: palabras clave + respuesta IA, con enfriamiento para evitar spam.
        </div>
        {channel === "tiktok" ? (
          <div style={{ fontSize: 12, color: "#fbbf24", marginBottom: 10 }}>
            TikTok queda en modo lectura para comentarios hasta habilitar endpoint oficial de respuesta.
          </div>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 8, marginBottom: 10 }}>
          <input
            style={input}
            placeholder="Nombre del trigger"
            value={triggerName}
            onChange={(e) => setTriggerName(e.target.value)}
          />
          <input
            style={input}
            placeholder="Palabras clave (coma)"
            value={triggerKeywords}
            onChange={(e) => setTriggerKeywords(e.target.value)}
          />
          <select style={input} value={triggerMode} onChange={(e) => setTriggerMode(e.target.value)}>
            <option value="any">Match por cualquiera</option>
            <option value="all">Match por todas</option>
          </select>
          <input
            style={input}
            type="number"
            min="0"
            placeholder="Enfriamiento (min)"
            value={triggerCooldown}
            onChange={(e) => setTriggerCooldown(e.target.value)}
          />
          <select style={input} value={triggerUseAI ? "ai" : "text"} onChange={(e) => setTriggerUseAI(e.target.value === "ai")}>
            <option value="ai">Respuesta con IA</option>
            <option value="text">Respuesta fija</option>
          </select>
          <input
            style={input}
            placeholder={triggerUseAI ? "Instrucciones para IA (opcional)" : "Texto fijo de respuesta"}
            value={triggerReply}
            onChange={(e) => setTriggerReply(e.target.value)}
          />
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
          <button
            style={{
              ...actionBtn,
              background: "rgba(52, 152, 219, 0.18)",
              borderColor: "rgba(52, 152, 219, 0.38)",
            }}
            type="button"
            onClick={createCommentTrigger}
            disabled={savingTrigger || channel === "tiktok"}
          >
            {savingTrigger ? "Guardando..." : "Crear trigger de comentarios"}
          </button>
          <button style={actionBtn} type="button" onClick={loadTriggers} disabled={loadingTriggers}>
            {loadingTriggers ? "Cargando..." : "Recargar triggers"}
          </button>
        </div>

        <div style={{ display: "grid", gap: 8 }}>
          {triggers.length === 0 ? (
            <div style={{ fontSize: 12, opacity: 0.75 }}>No hay triggers de comentarios para este canal.</div>
          ) : (
            triggers.map((t) => (
              <div key={t.id} style={{ border: "1px solid rgba(255,255,255,0.14)", borderRadius: 10, padding: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                  <strong style={{ fontSize: 13 }}>{t.name}</strong>
                  <button style={actionBtn} type="button" onClick={() => toggleTrigger(t)}>
                    {t.is_active ? "Desactivar" : "Activar"}
                  </button>
                </div>
                <div style={{ fontSize: 11, opacity: 0.72, marginTop: 4 }}>
                  evento: {t.event_type} · tipo: {t.trigger_type} · cooldown: {t.cooldown_minutes} min
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {error ? <div style={{ color: "#ffb4b4", fontSize: 12 }}>{error}</div> : null}
      {notice ? <div style={{ color: "#a8f0c5", fontSize: 12 }}>{notice}</div> : null}
    </div>
  );
}

export default function AdsManagerPanel({ apiBase = "" }) {
  const { isMobile } = useViewport();
  const [channel, setChannel] = useState("facebook");
  const [moduleId, setModuleId] = useState("comments");

  const cols = isMobile ? "1fr" : "1fr 1fr";

  return (
    <div
      className="placeholder-view custom-scrollbar"
      style={{ alignItems: "stretch", flexDirection: "column", justifyContent: "flex-start", width: "100%", minHeight: 0, overflowY: "auto", padding: 12 }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, gap: 8, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0 }}>Ads Manager</h2>
        <span style={{ fontSize: 12, opacity: 0.8 }}>Modulo social y publicidad separado de CRM WhatsApp</span>
      </div>

      <div style={{ ...box, marginBottom: 12 }}>
        <div style={{ fontSize: 12, opacity: 0.82, marginBottom: 10 }}>
          Canales sociales independientes por red. Comentarios, DM y Ads comparten auditoria y gobierno IA.
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
          {CHANNELS.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setChannel(c.id)}
              style={{
                ...chip,
                background: channel === c.id ? "rgba(52, 152, 219, 0.18)" : "transparent",
                borderColor: channel === c.id ? "rgba(52, 152, 219, 0.45)" : "rgba(255,255,255,0.18)",
              }}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {MODULES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setModuleId(m.id)}
              style={{
                ...chip,
                background: moduleId === m.id ? "rgba(46, 204, 113, 0.18)" : "transparent",
                borderColor: moduleId === m.id ? "rgba(46, 204, 113, 0.42)" : "rgba(255,255,255,0.18)",
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {moduleId === "comments" ? (
        <CommentsModule apiBase={apiBase} channel={channel} isMobile={isMobile} />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: cols, gap: 12 }}>
          <ModuleIntro channel={CHANNELS.find((c) => c.id === channel)?.label || channel} moduleId={moduleId} />
          <div style={box}>
            <h3 style={{ marginTop: 0, marginBottom: 8 }}>Checklist siguiente fase</h3>
            <div style={{ display: "grid", gap: 8, fontSize: 13 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" disabled />
                Conexion OAuth por red social
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" disabled />
                Webhooks de mensajes, comentarios y eventos ads
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" disabled />
                Politicas de aprobacion para acciones IA
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" disabled />
                Trazabilidad en modulo de auditoria
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
