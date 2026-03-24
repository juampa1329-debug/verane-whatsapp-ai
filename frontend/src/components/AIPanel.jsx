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

    // ✅ humanización / separación de mensajes
    reply_chunk_chars: 480,
    reply_delay_ms: 900,
    typing_delay_ms: 450,
    inbound_cooldown_sec: 6,
    inbound_post_activity_ms: 1400,
    inbound_audio_extra_ms: 2500,

    // ✅ VOZ / TTS
    voice_enabled: false,
    voice_gender: "neutral", // male|female|neutral
    voice_language: "es-CO", // es-CO, es-MX...
    voice_accent: "colombiano",
    voice_style_prompt: "",
    voice_max_notes_per_reply: 1, // 0..5
    voice_prefer_voice: false,
    voice_speaking_rate: 1.0, // 0.5..2.0

    // ✅ NUEVO: selector de proveedor TTS + ids (ElevenLabs)
    voice_tts_provider: "google", // google | elevenlabs | piper
    voice_tts_voice_id: "", // solo para elevenlabs
    voice_tts_model_id: "", // solo para elevenlabs
  });

  // KB
  const [kbFiles, setKbFiles] = useState([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [kbUploadLoading, setKbUploadLoading] = useState(false);
  const [kbNotes, setKbNotes] = useState("");
  const [kbActiveFilter, setKbActiveFilter] = useState("all"); // all|yes|no
  const [webSources, setWebSources] = useState([]);
  const [webLoading, setWebLoading] = useState(false);
  const [webSaving, setWebSaving] = useState(false);
  const [webSyncingId, setWebSyncingId] = useState("");
  const [webActiveFilter, setWebActiveFilter] = useState("all");
  const [webDraft, setWebDraft] = useState({
    url: "",
    source_name: "",
    notes: "",
    is_active: true,
    auto_sync: true,
    sync_interval_min: 360,
    timeout_sec: 20,
  });

  // QA
  const [qaPhone, setQaPhone] = useState("");
  const [qaText, setQaText] = useState("");
  const [qaLoading, setQaLoading] = useState(false);
  const [qaOut, setQaOut] = useState(null);

  // ✅ QA VOZ
  const [ttsText, setTtsText] = useState("");
  const [ttsLoading, setTtsLoading] = useState(false);
  const [ttsStatus, setTtsStatus] = useState("");
  const [ttsAudioUrl, setTtsAudioUrl] = useState("");

  const providers = useMemo(() => ["google", "groq", "mistral", "openrouter"], []);

  // Models (live + fallback)
  const [modelsByProvider, setModelsByProvider] = useState({});
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState("");

  // ✅ ElevenLabs catalog
  const [elVoices, setElVoices] = useState([]);
  const [elModels, setElModels] = useState([]);
  const [elLoading, setElLoading] = useState(false);
  const [elError, setElError] = useState("");

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

  const clampInt = (v, min, max, fallback) => {
    const n = Number(v);
    if (!Number.isFinite(n)) return fallback;
    return Math.max(min, Math.min(max, Math.trunc(n)));
  };

  const loadElevenlabsCatalog = async () => {
    setElLoading(true);
    setElError("");
    try {
      const [rv, rm] = await Promise.all([
        fetch(`${API}/api/ai/tts/elevenlabs/voices`),
        fetch(`${API}/api/ai/tts/elevenlabs/models`),
      ]);

      const dv = await rv.json();
      const dm = await rm.json();

      if (!rv.ok) throw new Error(dv?.detail || "No se pudieron cargar voices de ElevenLabs");
      if (!rm.ok) throw new Error(dm?.detail || "No se pudieron cargar models de ElevenLabs");

      const voices = Array.isArray(dv?.voices) ? dv.voices : [];
      const models = Array.isArray(dm?.models) ? dm.models : [];

      setElVoices(voices);
      setElModels(models);

      // ✅ si no hay seleccionado, setea defaults razonables
      setDraft((p) => {
        const next = { ...p };
        if (!next.voice_tts_voice_id && voices[0]?.id) next.voice_tts_voice_id = voices[0].id;
        if (!next.voice_tts_model_id && models[0]?.id) next.voice_tts_model_id = models[0].id;
        return next;
      });
    } catch (e) {
      setElError(String(e.message || e));
      setElVoices([]);
      setElModels([]);
    } finally {
      setElLoading(false);
    }
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

      // humanización
      reply_chunk_chars: clampNum(data.reply_chunk_chars ?? 480, 120, 2000, 480),
      reply_delay_ms: clampNum(data.reply_delay_ms ?? 900, 0, 15000, 900),
      typing_delay_ms: clampNum(data.typing_delay_ms ?? 450, 0, 15000, 450),
      inbound_cooldown_sec: clampInt(data.inbound_cooldown_sec ?? 6, 0, 30, 6),
      inbound_post_activity_ms: clampInt(data.inbound_post_activity_ms ?? 1400, 0, 15000, 1400),
      inbound_audio_extra_ms: clampInt(data.inbound_audio_extra_ms ?? 2500, 0, 15000, 2500),

      // ✅ VOZ / TTS
      voice_enabled: !!(data.voice_enabled ?? false),
      voice_gender: String(data.voice_gender ?? "neutral") || "neutral",
      voice_language: String(data.voice_language ?? "es-CO") || "es-CO",
      voice_accent: String(data.voice_accent ?? "colombiano") || "colombiano",
      voice_style_prompt: String(data.voice_style_prompt ?? "") || "",
      voice_max_notes_per_reply: clampInt(data.voice_max_notes_per_reply ?? 1, 0, 5, 1),
      voice_prefer_voice: !!(data.voice_prefer_voice ?? false),
      voice_speaking_rate: clampNum(data.voice_speaking_rate ?? 1.0, 0.5, 2.0, 1.0),

      // ✅ NUEVO: selector proveedor TTS + ids
      voice_tts_provider: String(data.voice_tts_provider ?? "google") || "google",
      voice_tts_voice_id: String(data.voice_tts_voice_id ?? "") || "",
      voice_tts_model_id: String(data.voice_tts_model_id ?? "") || "",
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

        // humanización
        reply_chunk_chars: clampNum(draft.reply_chunk_chars, 120, 2000, 480),
        reply_delay_ms: clampNum(draft.reply_delay_ms, 0, 15000, 900),
        typing_delay_ms: clampNum(draft.typing_delay_ms, 0, 15000, 450),
        inbound_cooldown_sec: clampInt(draft.inbound_cooldown_sec, 0, 30, 6),
        inbound_post_activity_ms: clampInt(draft.inbound_post_activity_ms, 0, 15000, 1400),
        inbound_audio_extra_ms: clampInt(draft.inbound_audio_extra_ms, 0, 15000, 2500),

        // voz
        voice_enabled: !!draft.voice_enabled,
        voice_gender: String(draft.voice_gender || "neutral"),
        voice_language: String(draft.voice_language || "es-CO"),
        voice_accent: String(draft.voice_accent || "colombiano"),
        voice_style_prompt: String(draft.voice_style_prompt || ""),
        voice_max_notes_per_reply: clampInt(draft.voice_max_notes_per_reply, 0, 5, 1),
        voice_prefer_voice: !!draft.voice_prefer_voice,
        voice_speaking_rate: clampNum(draft.voice_speaking_rate, 0.5, 2.0, 1.0),

        // ✅ NUEVO: selector proveedor TTS + ids
        voice_tts_provider: String(draft.voice_tts_provider || "google"),
        voice_tts_voice_id: String(draft.voice_tts_voice_id || ""),
        voice_tts_model_id: String(draft.voice_tts_model_id || ""),
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

  const loadWebSources = async () => {
    setWebLoading(true);
    try {
      const url = `${API}/api/ai/knowledge/web-sources?active=${encodeURIComponent(webActiveFilter)}&limit=200`;
      const r = await fetch(url);
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudieron cargar fuentes web");
      setWebSources(Array.isArray(data) ? data : []);
    } catch (e) {
      setStatus(`Web KB error: ${String(e.message || e)}`);
    } finally {
      setWebLoading(false);
    }
  };

  const createWebSource = async () => {
    const payload = {
      url: String(webDraft.url || "").trim(),
      source_name: String(webDraft.source_name || "").trim(),
      notes: String(webDraft.notes || "").trim(),
      is_active: !!webDraft.is_active,
      auto_sync: !!webDraft.auto_sync,
      sync_interval_min: clampInt(webDraft.sync_interval_min, 5, 10080, 360),
      timeout_sec: clampInt(webDraft.timeout_sec, 5, 60, 20),
    };
    if (!payload.url) {
      setStatus("Fuente web: URL requerida");
      setTimeout(() => setStatus(""), 2500);
      return;
    }

    setWebSaving(true);
    setStatus("");
    try {
      const r = await fetch(`${API}/api/ai/knowledge/web-sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudo crear la fuente web");
      setStatus("Fuente web creada ✅");
      setWebDraft((p) => ({ ...p, url: "", source_name: "", notes: "" }));
      await loadWebSources();
    } catch (e) {
      setStatus(`Fuente web error: ${String(e.message || e)}`);
    } finally {
      setWebSaving(false);
      setTimeout(() => setStatus(""), 2500);
    }
  };

  const syncWebSource = async (sourceId) => {
    if (!sourceId) return;
    setWebSyncingId(sourceId);
    setStatus("");
    try {
      const r = await fetch(`${API}/api/ai/knowledge/web-sources/${encodeURIComponent(sourceId)}/sync`, {
        method: "POST",
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudo sincronizar");
      setStatus(`Sync web ✅ chunks=${data?.chunks ?? "?"}`);
      await Promise.all([loadWebSources(), loadKbFiles()]);
    } catch (e) {
      setStatus(`Sync web error: ${String(e.message || e)}`);
    } finally {
      setWebSyncingId("");
      setTimeout(() => setStatus(""), 2500);
    }
  };

  const toggleWebSourceField = async (sourceId, patch) => {
    if (!sourceId) return;
    setStatus("");
    try {
      const r = await fetch(`${API}/api/ai/knowledge/web-sources/${encodeURIComponent(sourceId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch || {}),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudo actualizar fuente web");
      setStatus("Fuente web actualizada ✅");
      await Promise.all([loadWebSources(), loadKbFiles()]);
    } catch (e) {
      setStatus(`Update web error: ${String(e.message || e)}`);
    } finally {
      setTimeout(() => setStatus(""), 2500);
    }
  };

  const deleteWebSource = async (sourceId) => {
    if (!sourceId) return;
    const ok = window.confirm("¿Eliminar esta fuente web? (Borra chunks y archivo cacheado)");
    if (!ok) return;
    setStatus("");
    try {
      const r = await fetch(`${API}/api/ai/knowledge/web-sources/${encodeURIComponent(sourceId)}`, {
        method: "DELETE",
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudo eliminar la fuente web");
      setStatus("Fuente web eliminada ✅");
      await Promise.all([loadWebSources(), loadKbFiles()]);
    } catch (e) {
      setStatus(`Delete web error: ${String(e.message || e)}`);
    } finally {
      setTimeout(() => setStatus(""), 2500);
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
      setStatus("Archivo subido ✅ (PDF/TXT se indexan solos)");
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

  // ✅ TTS TEST
  const runTTS = async () => {
    const text = (ttsText || "").trim();
    if (!text) {
      setTtsStatus("Escribe un texto para probar voz");
      setTimeout(() => setTtsStatus(""), 2500);
      return;
    }

    setTtsLoading(true);
    setTtsStatus("");
    setTtsAudioUrl("");

    try {
      const r = await fetch(`${API}/api/ai/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          // ✅ usa el selector del panel
          provider: draft.voice_tts_provider || "google",
          voice_id: draft.voice_tts_voice_id || "",
          model_id: draft.voice_tts_model_id || "",
          // (si tu backend luego quiere leer ids de elevenlabs desde settings, no hace falta mandarlos aquí)
        }),
      });

      const ct = r.headers.get("content-type") || "";
      if (!r.ok) {
        let msg = "TTS falló";
        try {
          const j = await r.json();
          msg = j?.detail || j?.error || msg;
        } catch { }
        throw new Error(msg);
      }

      if (ct.includes("audio/")) {
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        setTtsAudioUrl(url);
        setTtsStatus("Audio generado ✅");
      } else {
        const j = await r.json();
        if (j?.url) {
          setTtsAudioUrl(j.url);
          setTtsStatus("Audio generado ✅");
        } else {
          setTtsStatus("TTS OK (pero sin audio retornado)");
        }
      }
    } catch (e) {
      setTtsStatus(`TTS: ${String(e.message || e)}`);
    } finally {
      setTtsLoading(false);
      setTimeout(() => setTtsStatus(""), 3500);
    }
  };

  useEffect(() => {
    const p = String(draft.voice_tts_provider || "").toLowerCase();
    if (p === "elevenlabs") {
      loadElevenlabsCatalog();
    } else {
      setElVoices([]);
      setElModels([]);
      setElError("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.voice_tts_provider]);

  useEffect(() => {
    loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadKbFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kbActiveFilter]);

  useEffect(() => {
    loadWebSources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [webActiveFilter]);

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
    const cool = clampInt(draft.inbound_cooldown_sec, 0, 30, 6);
    const post = clampInt(draft.inbound_post_activity_ms, 0, 15000, 1400);
    const audio = clampInt(draft.inbound_audio_extra_ms, 0, 15000, 2500);
    return `Chunks aprox: ${c} chars • Delay entre mensajes: ${d}ms • “Typing” inicial: ${t}ms • Espera entrada: ${cool}s • Post-actividad: ${post}ms • Extra audio: ${audio}ms`;
  }, [
    draft.reply_chunk_chars,
    draft.reply_delay_ms,
    draft.typing_delay_ms,
    draft.inbound_cooldown_sec,
    draft.inbound_post_activity_ms,
    draft.inbound_audio_extra_ms,
  ]);

  const voicePreview = useMemo(() => {
    const rate = clampNum(draft.voice_speaking_rate, 0.5, 2.0, 1.0);
    const mx = clampInt(draft.voice_max_notes_per_reply, 0, 5, 1);
    const ttsProv = (draft.voice_tts_provider || "google").toLowerCase();
    return `Voz: ${draft.voice_enabled ? "ON" : "OFF"} • ${draft.voice_gender} • ${draft.voice_language} • acento=${draft.voice_accent} • rate=${rate} • max notas=${mx} • tts=${ttsProv}`;
  }, [
    draft.voice_enabled,
    draft.voice_gender,
    draft.voice_language,
    draft.voice_accent,
    draft.voice_speaking_rate,
    draft.voice_max_notes_per_reply,
    draft.voice_tts_provider,
  ]);

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

              {/* Humanización / chunks */}
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

              {/* ✅ VOZ / TTS */}
              <div style={rowStyle}>
                <label style={labelStyle}>Cooldown entrada (seg)</label>
                <input
                  type="number"
                  min={0}
                  max={30}
                  value={draft.inbound_cooldown_sec}
                  onChange={(e) => setDraft((p) => ({ ...p, inbound_cooldown_sec: Number(e.target.value || 0) }))}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Espera post-actividad (ms)</label>
                <input
                  type="number"
                  min={0}
                  max={15000}
                  value={draft.inbound_post_activity_ms}
                  onChange={(e) => setDraft((p) => ({ ...p, inbound_post_activity_ms: Number(e.target.value || 0) }))}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Extra cuando es audio (ms)</label>
                <input
                  type="number"
                  min={0}
                  max={15000}
                  value={draft.inbound_audio_extra_ms}
                  onChange={(e) => setDraft((p) => ({ ...p, inbound_audio_extra_ms: Number(e.target.value || 0) }))}
                />
              </div>
              <hr style={hrStyle} />
              <h4 style={{ margin: "6px 0 0 0" }}>Voz / TTS (WhatsApp)</h4>
              <div style={{ fontSize: 12, opacity: 0.8, marginTop: 6 }}>{voicePreview}</div>

              <div style={rowStyle}>
                <label style={labelStyle}>Voz habilitada</label>
                <input
                  type="checkbox"
                  checked={!!draft.voice_enabled}
                  onChange={(e) => setDraft((p) => ({ ...p, voice_enabled: e.target.checked }))}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Preferir nota de voz</label>
                <input
                  type="checkbox"
                  checked={!!draft.voice_prefer_voice}
                  onChange={(e) => setDraft((p) => ({ ...p, voice_prefer_voice: e.target.checked }))}
                />
              </div>

              {/* ✅ NUEVO: selector proveedor TTS */}
              <div style={rowStyle}>
                <label style={labelStyle}>Proveedor TTS</label>
                <select
                  value={draft.voice_tts_provider || "google"}
                  onChange={(e) => setDraft((p) => ({ ...p, voice_tts_provider: e.target.value }))}
                >
                  <option value="google">google</option>
                  <option value="elevenlabs">elevenlabs</option>
                  <option value="piper">piper</option>
                </select>
              </div>

              {/* ✅ NUEVO: ids para ElevenLabs */}
                {String(draft.voice_tts_provider || "").toLowerCase() === "elevenlabs" && (
                  <>
                    {elError && (
                      <div style={{ fontSize: 12, color: "#ff6b6b", marginTop: 8 }}>
                        ElevenLabs: {elError}
                      </div>
                    )}

                    <div style={rowStyle}>
                      <label style={labelStyle}>ElevenLabs Voice</label>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <select
                          value={draft.voice_tts_voice_id || ""}
                          onChange={(e) => setDraft((p) => ({ ...p, voice_tts_voice_id: e.target.value }))}
                          disabled={elLoading}
                          style={{ width: "100%" }}
                        >
                          {elVoices.length === 0 ? (
                            <option value="">{elLoading ? "Cargando voices..." : "Sin voices (usa ID manual)"}</option>
                          ) : (
                            elVoices.map((v) => (
                              <option key={v.id} value={v.id}>
                                {v.label}
                              </option>
                            ))
                          )}
                        </select>

                        <button
                          type="button"
                          style={{ ...btnGhost, padding: "8px 10px" }}
                          onClick={loadElevenlabsCatalog}
                          title="Refrescar ElevenLabs"
                        >
                          ↻
                        </button>
                      </div>
                    </div>

                    {/* Fallback manual si quieres */}
                    <div style={rowStyle}>
                      <label style={labelStyle}>Voice ID (manual)</label>
                      <input
                        value={draft.voice_tts_voice_id}
                        onChange={(e) => setDraft((p) => ({ ...p, voice_tts_voice_id: e.target.value }))}
                        placeholder="Ej: 21m00Tcm4TlvDq8ikWAM"
                      />
                    </div>

                    <div style={rowStyle}>
                      <label style={labelStyle}>ElevenLabs Model</label>
                      <select
                        value={draft.voice_tts_model_id || ""}
                        onChange={(e) => setDraft((p) => ({ ...p, voice_tts_model_id: e.target.value }))}
                        disabled={elLoading}
                      >
                        {elModels.length === 0 ? (
                          <option value="">{elLoading ? "Cargando modelos..." : "Sin modelos (usa ID manual)"}</option>
                        ) : (
                          elModels.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.label}
                            </option>
                          ))
                        )}
                      </select>
                    </div>

                    {/* Fallback manual si quieres */}
                    <div style={rowStyle}>
                      <label style={labelStyle}>Model ID (manual)</label>
                      <input
                        value={draft.voice_tts_model_id}
                        onChange={(e) => setDraft((p) => ({ ...p, voice_tts_model_id: e.target.value }))}
                        placeholder="Ej: eleven_multilingual_v2"
                      />
                    </div>

                    <div style={{ fontSize: 12, opacity: 0.75, marginTop: 6 }}>
                      Guardar settings persistirá estos IDs para que el backend los use en TTS.
                    </div>
                  </>
                )}

              <div style={rowStyle}>
                <label style={labelStyle}>Género</label>
                <select
                  value={draft.voice_gender}
                  onChange={(e) => setDraft((p) => ({ ...p, voice_gender: e.target.value }))}
                >
                  <option value="neutral">neutral</option>
                  <option value="female">female</option>
                  <option value="male">male</option>
                </select>
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Idioma</label>
                <input
                  value={draft.voice_language}
                  onChange={(e) => setDraft((p) => ({ ...p, voice_language: e.target.value }))}
                  placeholder="es-CO"
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Acento (etiqueta)</label>
                <input
                  value={draft.voice_accent}
                  onChange={(e) => setDraft((p) => ({ ...p, voice_accent: e.target.value }))}
                  placeholder="colombiano / mexicano / etc"
                />
              </div>

              <div style={{ ...rowStyle, alignItems: "flex-start" }}>
                <label style={labelStyle}>Prompt de voz</label>
                <textarea
                  value={draft.voice_style_prompt}
                  onChange={(e) => setDraft((p) => ({ ...p, voice_style_prompt: e.target.value }))}
                  rows={4}
                  placeholder="Ej: Habla cálido, cercano, con acento paisa suave. Pausas cortas. No uses jerga técnica..."
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Máx notas por respuesta</label>
                <input
                  type="number"
                  min={0}
                  max={5}
                  value={draft.voice_max_notes_per_reply}
                  onChange={(e) => setDraft((p) => ({ ...p, voice_max_notes_per_reply: Number(e.target.value || 0) }))}
                />
              </div>

              <div style={rowStyle}>
                <label style={labelStyle}>Velocidad (0.5–2.0)</label>
                <input
                  type="number"
                  step="0.1"
                  min={0.5}
                  max={2.0}
                  value={draft.voice_speaking_rate}
                  onChange={(e) => setDraft((p) => ({ ...p, voice_speaking_rate: Number(e.target.value || 0) }))}
                />
              </div>

              {/* ✅ prueba de voz */}
              <div style={{ marginTop: 10, padding: 12, borderRadius: 12, border: "1px solid rgba(255,255,255,0.10)" }}>
                <div style={{ fontWeight: 600, marginBottom: 8 }}>Probar voz (TTS)</div>
                {ttsStatus && (
                  <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 8 }}>
                    {ttsStatus}
                  </div>
                )}

                <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 8 }}>
                  Proveedor actual: <code>{draft.voice_tts_provider || "google"}</code>
                </div>

                <textarea
                  value={ttsText}
                  onChange={(e) => setTtsText(e.target.value)}
                  rows={3}
                  placeholder="Escribe un texto para generar audio..."
                  style={{ width: "100%", resize: "vertical" }}
                />
                <div style={{ display: "flex", gap: 10, marginTop: 10, alignItems: "center", flexWrap: "wrap" }}>
                  <button onClick={runTTS} disabled={ttsLoading} style={btnPrimary}>
                    {ttsLoading ? "Generando..." : "Generar audio"}
                  </button>
                  {ttsAudioUrl ? (
                    <audio controls src={ttsAudioUrl} />
                  ) : (
                    <span style={{ fontSize: 12, opacity: 0.75 }}>
                      (Necesita backend <code>/api/ai/tts</code>)
                    </span>
                  )}
                </div>
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
              accept=".pdf,application/pdf,text/plain,.txt,image/*"
              disabled={kbUploadLoading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                uploadKb(f);
                e.target.value = "";
              }}
            />
            <div style={{ fontSize: 12, opacity: 0.75, marginTop: 6 }}>
              PDF y TXT se indexan automático. Imágenes quedan guardadas pero sin “visión” por ahora (fase multimodal después).
            </div>
          </div>

          <div style={{ marginTop: 14 }}>
            <hr style={hrStyle} />
            <h4 style={{ margin: "0 0 8px 0" }}>Fuentes Web (Crawl)</h4>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <select
                value={webActiveFilter}
                onChange={(e) => setWebActiveFilter(e.target.value)}
                style={{ padding: "8px 10px", borderRadius: 10 }}
              >
                <option value="all">Mostrar: Todas</option>
                <option value="yes">Solo activas</option>
                <option value="no">Solo inactivas</option>
              </select>
              <button onClick={loadWebSources} disabled={webLoading} style={btnGhost}>
                {webLoading ? "Cargando..." : "Refrescar fuentes web"}
              </button>
            </div>

            <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
              <input
                value={webDraft.url}
                onChange={(e) => setWebDraft((p) => ({ ...p, url: e.target.value }))}
                placeholder="https://tutienda.com/pagina-o-blog"
              />
              <input
                value={webDraft.source_name}
                onChange={(e) => setWebDraft((p) => ({ ...p, source_name: e.target.value }))}
                placeholder="Nombre corto de la fuente (opcional)"
              />
              <input
                value={webDraft.notes}
                onChange={(e) => setWebDraft((p) => ({ ...p, notes: e.target.value }))}
                placeholder="Notas (opcional)"
              />
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <label style={{ fontSize: 12, opacity: 0.85 }}>
                  Intervalo (min)
                  <input
                    type="number"
                    min={5}
                    max={10080}
                    value={webDraft.sync_interval_min}
                    onChange={(e) => setWebDraft((p) => ({ ...p, sync_interval_min: Number(e.target.value || 0) }))}
                    style={{ marginLeft: 8, width: 100 }}
                  />
                </label>
                <label style={{ fontSize: 12, opacity: 0.85 }}>
                  Timeout (seg)
                  <input
                    type="number"
                    min={5}
                    max={60}
                    value={webDraft.timeout_sec}
                    onChange={(e) => setWebDraft((p) => ({ ...p, timeout_sec: Number(e.target.value || 0) }))}
                    style={{ marginLeft: 8, width: 100 }}
                  />
                </label>
                <label style={{ fontSize: 12, opacity: 0.9 }}>
                  <input
                    type="checkbox"
                    checked={!!webDraft.is_active}
                    onChange={(e) => setWebDraft((p) => ({ ...p, is_active: e.target.checked }))}
                    style={{ marginRight: 6 }}
                  />
                  Activa
                </label>
                <label style={{ fontSize: 12, opacity: 0.9 }}>
                  <input
                    type="checkbox"
                    checked={!!webDraft.auto_sync}
                    onChange={(e) => setWebDraft((p) => ({ ...p, auto_sync: e.target.checked }))}
                    style={{ marginRight: 6 }}
                  />
                  Auto-sync
                </label>
                <button onClick={createWebSource} disabled={webSaving} style={btnPrimary}>
                  {webSaving ? "Creando..." : "Añadir fuente web"}
                </button>
              </div>
            </div>

            <div style={{ marginTop: 10, display: "grid", gap: 8, maxHeight: 260, overflow: "auto", paddingRight: 6 }}>
              {webSources.map((w) => (
                <div key={w.id} style={fileRowStyle}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {w.source_name || w.url}
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.84, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {w.url}
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.78, marginTop: 3 }}>
                      estado={w.last_status || "never"} • última sync={String(w.last_synced_at || "nunca")} • intervalo={w.sync_interval_min}m
                    </div>
                    {!!w.last_error && (
                      <div style={{ fontSize: 12, color: "#ff9494", marginTop: 3 }}>
                        {String(w.last_error || "").slice(0, 180)}
                      </div>
                    )}
                    <div style={{ display: "flex", gap: 8, marginTop: 6, flexWrap: "wrap" }}>
                      <label style={{ fontSize: 12, opacity: 0.85 }}>
                        Intervalo (min):
                        <input
                          type="number"
                          min={5}
                          max={10080}
                          defaultValue={w.sync_interval_min}
                          onBlur={(e) => {
                            const next = clampInt(e.target.value, 5, 10080, 360);
                            if (Number(next) !== Number(w.sync_interval_min)) {
                              toggleWebSourceField(w.id, { sync_interval_min: next });
                            }
                          }}
                          style={{ marginLeft: 6, width: 90 }}
                        />
                      </label>
                      <label style={{ fontSize: 12, opacity: 0.85 }}>
                        Timeout:
                        <input
                          type="number"
                          min={5}
                          max={60}
                          defaultValue={w.timeout_sec}
                          onBlur={(e) => {
                            const next = clampInt(e.target.value, 5, 60, 20);
                            if (Number(next) !== Number(w.timeout_sec)) {
                              toggleWebSourceField(w.id, { timeout_sec: next });
                            }
                          }}
                          style={{ marginLeft: 6, width: 80 }}
                        />
                      </label>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                    <button
                      style={btnGhost}
                      onClick={() => syncWebSource(w.id)}
                      disabled={webSyncingId === w.id}
                    >
                      {webSyncingId === w.id ? "Sincronizando..." : "Sync ahora"}
                    </button>
                    <button
                      style={btnGhost}
                      onClick={() => toggleWebSourceField(w.id, { is_active: !w.is_active })}
                    >
                      {w.is_active ? "Pausar" : "Activar"}
                    </button>
                    <button
                      style={btnGhost}
                      onClick={() => toggleWebSourceField(w.id, { auto_sync: !w.auto_sync })}
                    >
                      {w.auto_sync ? "Auto ON" : "Auto OFF"}
                    </button>
                    <button style={btnDanger} onClick={() => deleteWebSource(w.id)}>
                      Borrar
                    </button>
                  </div>
                </div>
              ))}
              {!webLoading && webSources.length === 0 && (
                <div style={{ fontSize: 12, opacity: 0.8 }}>No hay fuentes web registradas.</div>
              )}
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

/* ===== styles inline mínimos ===== */

const panelStyle = {
  width: "100%",
  padding: 14,
  height: "100%",
  overflowY: "auto",
  overflowX: "hidden",
  boxSizing: "border-box",
};

const gridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: 14,
  marginTop: 14,
};

const cardStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 16,
  padding: 14,
  background: "rgba(255,255,255,0.03)",
  boxShadow: "0 6px 20px rgba(0,0,0,0.18)",
};

const rowStyle = {
  display: "grid",
  gridTemplateColumns: "minmax(120px, 180px) minmax(0, 1fr)",
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
