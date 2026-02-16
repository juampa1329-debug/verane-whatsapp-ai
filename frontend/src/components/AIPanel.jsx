import React, { useEffect, useMemo, useState } from "react";

export default function AIPanel({ apiBase }) {
  const API = (apiBase || "").replace(/\/$/, "");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

  // settings
  const [settings, setSettings] = useState(null);
  const [draft, setDraft] = useState({
    is_enabled: true,
    provider: "google",
    model: "gemma-3-4b-it",
    system_prompt: "",
    max_tokens: 512,
    temperature: 0.7,
    fallback_provider: "groq",
    fallback_model: "llama-3.1-8b-instant",
    timeout_sec: 25,
    max_retries: 1,

    // ✅ NUEVO (humanización / separación de mensajes)
    reply_chunk_chars: 480,
    reply_delay_ms: 900,
    typing_delay_ms: 450,
  });

  // KB
  const [kbFiles, setKbFiles] = useState([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [kbUploadLoading, setKbUploadLoading] = useState(false);
  const [kbNotes, setKbNotes] = useState("");
  const [kbActiveFilter, setKbActiveFilter] = useState("all"); // all|yes|no

  // QA
  const [qaPhone, setQaPhone] = useState("");
  const [qaText, setQaText] = useState("");
  const [qaLoading, setQaLoading] = useState(false);
  const [qaOut, setQaOut] = useState(null);

  const providers = useMemo(() => ["google", "groq", "mistral", "openrouter"], []);

  // Models (live + fallback)
  const [modelsByProvider, setModelsByProvider] = useState({});
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState("");

  // ===== helpers para soportar modelos string o {id,label,raw} =====
  const normalizeModels = (list) => {
    if (!Array.isArray(list)) return [];
    return list
      .map((m) => {
        if (typeof m === "string") return { value: m, label: m };
        if (m && typeof m === "object") {
          const value = String(m.id || m.raw || "");
          const label = String(m.label || m.id || m.raw || value);
          return value ? { value, label } : null;
        }
        return null;
      })
      .filter(Boolean);
  };

  const providerModels = useMemo(() => {
    const p = (draft.provider || "").toLowerCase();
    const raw = Array.isArray(modelsByProvider[p]) ? modelsByProvider[p] : [];
    return normalizeModels(raw);
  }, [draft.provider, modelsByProvider]);

  const fallbackProviderModels = useMemo(() => {
    const p = (draft.fallback_provider || "").toLowerCase();
    const raw = Array.isArray(modelsByProvider[p]) ? modelsByProvider[p] : [];
    return normalizeModels(raw);
  }, [draft.fallback_provider, modelsByProvider]);

  const loadModels = async (provider) => {
    const p = (provider || "").trim().toLowerCase();
    if (!p) return;

    // cache: si ya están cargados, no pedir otra vez
    if (Array.isArray(modelsByProvider[p]) && modelsByProvider[p].length > 0) return;

    setModelsLoading(true);
    setModelsError("");

    // 1) intenta live
    try {
      const r = await fetch(`${API}/api/ai/models/live?provider=${encodeURIComponent(p)}`);
      const data = await r.json();
      if (r.ok && Array.isArray(data?.models) && data.models.length > 0) {
        setModelsByProvider((prev) => ({ ...prev, [p]: data.models }));
        return;
      }
      throw new Error(data?.detail || "No live models");
    } catch (e) {
      // 2) fallback al whitelist (/api/ai/models)
      try {
        const r2 = await fetch(`${API}/api/ai/models`);
        const data2 = await r2.json();
        const list = data2?.providers?.[p] || [];
        if (Array.isArray(list) && list.length > 0) {
          setModelsByProvider((prev) => ({ ...prev, [p]: list }));
          return;
        }
        setModelsError(`No hay modelos disponibles para ${p}`);
      } catch (e2) {
        setModelsError(`Error cargando modelos: ${String(e2.message || e2)}`);
      }
    } finally {
      setModelsLoading(false);
    }
  };

  const forceReloadModels = async (provider) => {
    const p = (provider || "").trim().toLowerCase();
    if (!p) return;
    setModelsByProvider((prev) => ({ ...prev, [p]: [] }));
    await loadModels(p);
  };

  const clampNum = (v, min, max, fallback) => {
    const n = Number(v);
    if (!Number.isFinite(n)) return fallback;
    return Math.max(min, Math.min(max, n));
  };

  const coalesceSettings = (data) => {
    return {
      is_enabled: !!data.is_enabled,
      provider: data.provider || "google",
      model: data.model || "gemma-3-4b-it",
      system_prompt: data.system_prompt || "",
      max_tokens: Number(data.max_tokens ?? 512),
      temperature: Number(data.temperature ?? 0.7),
      fallback_provider: data.fallback_provider || "groq",
      fallback_model: data.fallback_model || "llama-3.1-8b-instant",
      timeout_sec: Number(data.timeout_sec ?? 25),
      max_retries: Number(data.max_retries ?? 1),

      // ✅ NUEVO (si backend no lo trae, defaults)
      reply_chunk_chars: clampNum(data.reply_chunk_chars ?? 480, 120, 2000, 480),
      reply_delay_ms: clampNum(data.reply_delay_ms ?? 900, 0, 15000, 900),
      typing_delay_ms: clampNum(data.typing_delay_ms ?? 450, 0, 15000, 450),
    };
  };

  const loadSettings = async () => {
    setLoading(true);
    setStatus("");
    try {
      const r = await fetch(`${API}/api/ai/settings`);
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudieron cargar settings");

      setSettings(data);
      setDraft(coalesceSettings(data));
    } catch (e) {
      setStatus(`Error: ${String(e.message || e)}`);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    setStatus("");
    try {
      // ✅ aseguramos números razonables
      const payload = {
        ...draft,
        max_tokens: clampNum(draft.max_tokens, 32, 8192, 512),
        temperature: clampNum(draft.temperature, 0, 2, 0.7),
        timeout_sec: clampNum(draft.timeout_sec, 5, 120, 25),
        max_retries: clampNum(draft.max_retries, 0, 3, 1),

        // ✅ NUEVO
        reply_chunk_chars: clampNum(draft.reply_chunk_chars, 120, 2000, 480),
        reply_delay_ms: clampNum(draft.reply_delay_ms, 0, 15000, 900),
        typing_delay_ms: clampNum(draft.typing_delay_ms, 0, 15000, 450),
      };

      const r = await fetch(`${API}/api/ai/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudieron guardar settings");

      setSettings(data);
      setDraft(coalesceSettings(data));
      setStatus("Guardado ✅");
    } catch (e) {
      setStatus(`Error al guardar: ${String(e.message || e)}`);
    } finally {
      setSaving(false);
      setTimeout(() => setStatus(""), 2500);
    }
  };

  const loadKbFiles = async () => {
    setKbLoading(true);
    try {
      const url = `${API}/api/ai/knowledge/files?active=${encodeURIComponent(kbActiveFilter)}&limit=200`;
      const r = await fetch(url);
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudieron cargar archivos KB");
      setKbFiles(Array.isArray(data) ? data : data || []);
    } catch (e) {
      setStatus(`KB error: ${String(e.message || e)}`);
    } finally {
      setKbLoading(false);
    }
  };

  const uploadKb = async (file) => {
    if (!file) return;
    setKbUploadLoading(true);
    setStatus("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("notes", kbNotes || "");

      const r = await fetch(`${API}/api/ai/knowledge/upload`, {
        method: "POST",
        body: fd,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "Upload KB falló");

      setKbNotes("");
      setStatus("Archivo subido ✅ (si es PDF, se indexa solo)");
      await loadKbFiles();
    } catch (e) {
      setStatus(`Upload error: ${String(e.message || e)}`);
    } finally {
      setKbUploadLoading(false);
      setTimeout(() => setStatus(""), 2500);
    }
  };

  const reindexKb = async (fileId) => {
    if (!fileId) return;
    setStatus("");
    try {
      const r = await fetch(`${API}/api/ai/knowledge/reindex/${encodeURIComponent(fileId)}`, {
        method: "POST",
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "Reindex falló");
      setStatus(`Reindex ✅ chunks=${data?.chunks ?? "?"}`);
      await loadKbFiles();
    } catch (e) {
      setStatus(`Reindex error: ${String(e.message || e)}`);
    } finally {
      setTimeout(() => setStatus(""), 2500);
    }
  };

  const deleteKb = async (fileId) => {
    if (!fileId) return;
    const ok = window.confirm("¿Eliminar este archivo de la KB? (Borra DB + disco)");
    if (!ok) return;

    setStatus("");
    try {
      const r = await fetch(`${API}/api/ai/knowledge/files/${encodeURIComponent(fileId)}`, {
        method: "DELETE",
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "Delete KB falló");
      setStatus("Eliminado ✅");
      await loadKbFiles();
    } catch (e) {
      setStatus(`Delete error: ${String(e.message || e)}`);
    } finally {
      setTimeout(() => setStatus(""), 2500);
    }
  };

  const runQA = async () => {
    const phone = (qaPhone || "").trim();
    const text = (qaText || "").trim();
    if (!phone) {
      setStatus("QA: phone es requerido");
      setTimeout(() => setStatus(""), 2500);
      return;
    }
    setQaLoading(true);
    setQaOut(null);
    setStatus("");
    try {
      const r = await fetch(`${API}/api/ai/process-message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, text, meta: null }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "QA falló");
      setQaOut(data);
    } catch (e) {
      setQaOut({ ok: false, error: String(e.message || e) });
    } finally {
      setQaLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadKbFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kbActiveFilter]);

  // cargar modelos cuando cambie provider
  useEffect(() => {
    if (!draft?.provider) return;
    loadModels(draft.provider);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.provider]);

  // cargar modelos cuando cambie fallback_provider
  useEffect(() => {
    if (!draft?.fallback_provider) return;
    loadModels(draft.fallback_provider);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.fallback_provider]);

  // si el modelo actual no existe en la lista, setear el primero disponible
  useEffect(() => {
    if (!providerModels || providerModels.length === 0) return;
    const exists = providerModels.some((m) => m.value === draft.model);
    if (!draft.model || !exists) {
      setDraft((p) => ({ ...p, model: providerModels[0].value }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providerModels]);

  useEffect(() => {
    if (!fallbackProviderModels || fallbackProviderModels.length === 0) return;
    const exists = fallbackProviderModels.some((m) => m.value === draft.fallback_model);
    if (!draft.fallback_model || !exists) {
      setDraft((p) => ({ ...p, fallback_model: fallbackProviderModels[0].value }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fallbackProviderModels]);

  const humanPreview = useMemo(() => {
    const c = clampNum(draft.reply_chunk_chars, 120, 2000, 480);
    const d = clampNum(draft.reply_delay_ms, 0, 15000, 900);
    const t = clampNum(draft.typing_delay_ms, 0, 15000, 450);
    return `Chunks aprox: ${c} chars • Delay entre mensajes: ${d}ms • “Typing” inicial: ${t}ms`;
  }, [draft.reply_chunk_chars, draft.reply_delay_ms, draft.typing_delay_ms]);

  if (!API) {
    return (
      <div style={panelStyle}>
        <h2 style={{ margin: 0 }}>Ajustes IA</h2>
        <p style={{ opacity: 0.85 }}>
          Falta <code>VITE_API_BASE</code> o <code>apiBase</code>.
        </p>
      </div>
    );
  }

  return (
    <div style={panelStyle}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0 }}>Ajustes IA</h2>
        {status && (
          <span
            style={{
              fontSize: 13,
              opacity: 0.9,
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid rgba(255,255,255,0.15)",
            }}
          >
            {status}
          </span>
        )}
      </div>

      <div style={gridStyle}>
        {/* SETTINGS */}
        <section style={cardStyle}>
          <h3 style={{ marginTop: 0 }}>Configuración</h3>

          {loading ? (
            <div style={{ opacity: 0.8 }}>Cargando...</div>
          ) : (
            <>
              <div style={rowStyle}>
                <label style={labelStyle}>IA habilitada</label>
                <input
                  type="checkbox"
                  checked={!!draft.is_enabled}
                  onChange={(e) => setDraft((p) => ({ ...p, is_enabled: e.target.checked }))}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Provider</label>
                <select value={draft.provider} onChange={(e) => setDraft((p) => ({ ...p, provider: e.target.value }))}>
                  {providers.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              {/* MODELO (SELECT) */}
              <div style={rowStyle}>
                <label style={labelStyle}>Modelo</label>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <select
                    value={draft.model || ""}
                    onChange={(e) => setDraft((p) => ({ ...p, model: e.target.value }))}
                    disabled={modelsLoading && providerModels.length === 0}
                    style={{ width: "100%" }}
                  >
                    {providerModels.length === 0 ? (
                      <option value="">{modelsLoading ? "Cargando modelos..." : "Sin modelos"}</option>
                    ) : (
                      providerModels.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))
                    )}
                  </select>

                  <button
                    type="button"
                    style={{ ...btnGhost, padding: "8px 10px" }}
                    onClick={() => forceReloadModels(draft.provider)}
                    title="Refrescar modelos"
                  >
                    ↻
                  </button>
                </div>

                {modelsError && (
                  <div style={{ gridColumn: "2 / -1", fontSize: 12, color: "#ff6b6b", marginTop: 6 }}>
                    {modelsError}
                  </div>
                )}
              </div>

              <div style={{ ...rowStyle, alignItems: "flex-start" }}>
                <label style={labelStyle}>System prompt</label>
                <textarea
                  value={draft.system_prompt}
                  onChange={(e) => setDraft((p) => ({ ...p, system_prompt: e.target.value }))}
                  placeholder="(opcional) comportamiento del bot..."
                  rows={6}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Max tokens</label>
                <input
                  type="number"
                  min={32}
                  max={8192}
                  value={draft.max_tokens}
                  onChange={(e) => setDraft((p) => ({ ...p, max_tokens: Number(e.target.value || 0) }))}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Temperatura</label>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  max={2}
                  value={draft.temperature}
                  onChange={(e) => setDraft((p) => ({ ...p, temperature: Number(e.target.value || 0) }))}
                />
              </div>

              <hr style={hrStyle} />

              <div style={rowStyle}>
                <label style={labelStyle}>Fallback provider</label>
                <select
                  value={draft.fallback_provider}
                  onChange={(e) => setDraft((p) => ({ ...p, fallback_provider: e.target.value }))}
                >
                  {providers.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              {/* FALLBACK MODEL (SELECT) */}
              <div style={rowStyle}>
                <label style={labelStyle}>Fallback model</label>
                <select
                  value={draft.fallback_model || ""}
                  onChange={(e) => setDraft((p) => ({ ...p, fallback_model: e.target.value }))}
                  disabled={fallbackProviderModels.length === 0}
                >
                  {fallbackProviderModels.length === 0 ? (
                    <option value="">{modelsLoading ? "Cargando..." : "Sin modelos"}</option>
                  ) : (
                    fallbackProviderModels.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Timeout (sec)</label>
                <input
                  type="number"
                  min={5}
                  max={120}
                  value={draft.timeout_sec}
                  onChange={(e) => setDraft((p) => ({ ...p, timeout_sec: Number(e.target.value || 0) }))}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Max retries</label>
                <input
                  type="number"
                  min={0}
                  max={3}
                  value={draft.max_retries}
                  onChange={(e) => setDraft((p) => ({ ...p, max_retries: Number(e.target.value || 0) }))}
                />
              </div>

              {/* ✅ NUEVO: Humanización / chunks */}
              <hr style={hrStyle} />
              <h4 style={{ margin: "6px 0 0 0" }}>Humanización (WhatsApp)</h4>
              <div style={{ fontSize: 12, opacity: 0.8, marginTop: 6 }}>{humanPreview}</div>

              <div style={rowStyle}>
                <label style={labelStyle}>Chars por mensaje</label>
                <input
                  type="number"
                  min={120}
                  max={2000}
                  value={draft.reply_chunk_chars}
                  onChange={(e) => setDraft((p) => ({ ...p, reply_chunk_chars: Number(e.target.value || 0) }))}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Delay entre mensajes (ms)</label>
                <input
                  type="number"
                  min={0}
                  max={15000}
                  value={draft.reply_delay_ms}
                  onChange={(e) => setDraft((p) => ({ ...p, reply_delay_ms: Number(e.target.value || 0) }))}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Typing delay inicial (ms)</label>
                <input
                  type="number"
                  min={0}
                  max={15000}
                  value={draft.typing_delay_ms}
                  onChange={(e) => setDraft((p) => ({ ...p, typing_delay_ms: Number(e.target.value || 0) }))}
                />
              </div>

              <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
                <button onClick={saveSettings} disabled={saving} style={btnPrimary}>
                  {saving ? "Guardando..." : "Guardar settings"}
                </button>
                <button onClick={loadSettings} disabled={saving} style={btnGhost}>
                  Recargar
                </button>
              </div>

              {settings && (
                <div style={{ marginTop: 12, fontSize: 12, opacity: 0.8 }}>
                  Última actualización: {String(settings.updated_at || "")}
                </div>
              )}
            </>
          )}
        </section>

        {/* KNOWLEDGE BASE */}
        <section style={cardStyle}>
          <h3 style={{ marginTop: 0 }}>Knowledge Base</h3>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <select
              value={kbActiveFilter}
              onChange={(e) => setKbActiveFilter(e.target.value)}
              style={{ padding: "8px 10px", borderRadius: 10 }}
            >
              <option value="all">Mostrar: Todos</option>
              <option value="yes">Solo activos</option>
              <option value="no">Solo inactivos</option>
            </select>

            <button onClick={loadKbFiles} disabled={kbLoading} style={btnGhost}>
              {kbLoading ? "Cargando..." : "Refrescar"}
            </button>
          </div>

          <div style={{ marginTop: 12 }}>
            <label style={{ fontSize: 12, opacity: 0.85 }}>Notas (opcional)</label>
            <input
              value={kbNotes}
              onChange={(e) => setKbNotes(e.target.value)}
              placeholder="ej: catálogo 2026, políticas de envíos..."
              style={{ width: "100%", marginTop: 6 }}
            />
          </div>

          <div style={{ marginTop: 10 }}>
            <input
              type="file"
              accept=".pdf,application/pdf,image/*"
              disabled={kbUploadLoading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                uploadKb(f);
                e.target.value = "";
              }}
            />
            <div style={{ fontSize: 12, opacity: 0.75, marginTop: 6 }}>
              PDF se indexa automático. Imágenes quedan guardadas pero sin “visión” por ahora (fase multimodal después).
            </div>
          </div>

          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 8 }}>Archivos ({kbFiles.length})</div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 10,
                maxHeight: 420,
                overflow: "auto",
                paddingRight: 6,
              }}
            >
              {kbFiles.map((f) => (
                <div key={f.id} style={fileRowStyle}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {f.file_name}
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.8 }}>
                      {f.mime_type} • {f.size_bytes} bytes • {f.is_active ? "activo" : "inactivo"}
                    </div>
                    {f.notes ? <div style={{ fontSize: 12, opacity: 0.85, marginTop: 4 }}>📝 {f.notes}</div> : null}
                    <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>upd: {String(f.updated_at || "")}</div>
                  </div>

                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                    <button style={btnGhost} onClick={() => reindexKb(f.id)}>
                      Reindex
                    </button>
                    <button style={btnDanger} onClick={() => deleteKb(f.id)}>
                      Borrar
                    </button>
                  </div>
                </div>
              ))}

              {!kbLoading && kbFiles.length === 0 && <div style={{ opacity: 0.8 }}>No hay archivos KB.</div>}
            </div>
          </div>
        </section>

        {/* QA */}
        <section style={cardStyle}>
          <h3 style={{ marginTop: 0 }}>QA — Probar IA</h3>

          <div style={rowStyle}>
            <label style={labelStyle}>Phone</label>
            <input value={qaPhone} onChange={(e) => setQaPhone(e.target.value)} placeholder="57300..." />
          </div>

          <div style={{ ...rowStyle, alignItems: "flex-start" }}>
            <label style={labelStyle}>Mensaje</label>
            <textarea
              value={qaText}
              onChange={(e) => setQaText(e.target.value)}
              rows={4}
              placeholder="Escribe un mensaje de prueba..."
              style={{ width: "100%", resize: "vertical" }}
            />
          </div>

          <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
            <button onClick={runQA} disabled={qaLoading} style={btnPrimary}>
              {qaLoading ? "Procesando..." : "Procesar"}
            </button>
            <button onClick={() => setQaOut(null)} style={btnGhost}>
              Limpiar
            </button>
          </div>

          {qaOut && <pre style={preStyle}>{JSON.stringify(qaOut, null, 2)}</pre>}

          <div style={{ fontSize: 12, opacity: 0.75, marginTop: 8 }}>
            Usa <code>/api/ai/process-message</code> (endpoint manual de prueba).
          </div>
        </section>
      </div>
    </div>
  );
}

/* ===== styles inline mínimos para no tocar tu CSS (puedes migrarlos a App.css si quieres) ===== */

const panelStyle = {
  width: "100%",
  padding: 18,

  // ✅ FIX: permitir scroll sin hacer zoom out
  height: "calc(100vh - 24px)",
  overflowY: "auto",
  overflowX: "hidden",
  boxSizing: "border-box",
};

const gridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(12, 1fr)",
  gap: 14,
  marginTop: 14,
};

const cardStyle = {
  gridColumn: "span 6",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 16,
  padding: 14,
  background: "rgba(255,255,255,0.03)",
  boxShadow: "0 6px 20px rgba(0,0,0,0.18)",
};

const rowStyle = {
  display: "grid",
  gridTemplateColumns: "160px 1fr",
  gap: 10,
  alignItems: "center",
  marginTop: 10,
};

const labelStyle = {
  fontSize: 13,
  opacity: 0.85,
};

const hrStyle = {
  border: "none",
  borderTop: "1px solid rgba(255,255,255,0.12)",
  margin: "14px 0",
};

const btnPrimary = {
  padding: "10px 12px",
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "rgba(255,255,255,0.10)",
  cursor: "pointer",
};

const btnGhost = {
  padding: "10px 12px",
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.14)",
  background: "transparent",
  cursor: "pointer",
};

const btnDanger = {
  padding: "10px 12px",
  borderRadius: 12,
  border: "1px solid rgba(255,80,80,0.25)",
  background: "rgba(255,80,80,0.10)",
  cursor: "pointer",
};

const fileRowStyle = {
  display: "flex",
  gap: 12,
  alignItems: "center",
  justifyContent: "space-between",
  padding: 12,
  borderRadius: 14,
  border: "1px solid rgba(255,255,255,0.10)",
  background: "rgba(0,0,0,0.10)",
};

const preStyle = {
  marginTop: 12,
  padding: 12,
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.12)",
  background: "rgba(0,0,0,0.20)",
  maxHeight: 320,
  overflow: "auto",
  fontSize: 12,
};
