import React, { useEffect, useMemo, useRef, useState } from "react";
import EmojiPickerButton from "./EmojiPickerButton";

const box = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  background: "rgba(255,255,255,0.02)",
  padding: 12,
};

const input = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "transparent",
  color: "inherit",
};

const smallBtn = {
  padding: "7px 10px",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.16)",
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
};

const dangerBtn = {
  ...smallBtn,
  border: "1px solid rgba(255,120,120,0.55)",
  color: "#ffb7b7",
};

const TEMPLATE_STATUS_OPTIONS = [
  { value: "draft", label: "Borrador" },
  { value: "approved", label: "Aprobada" },
  { value: "archived", label: "Archivada" },
];

const TEMPLATE_RENDER_MODE_OPTIONS = [
  { value: "chat", label: "Chat" },
  { value: "plain", label: "Plano" },
];

function emptyTemplateForm() {
  return {
    id: null,
    name: "",
    category: "general",
    status: "draft",
    render_mode: "chat",
    body: "",
  };
}

function emptyBlock(kind = "text") {
  if (kind === "image") {
    return { kind: "image", media_id: "", image_url: "", caption: "", delay_ms: 0, insert_key: "customer_name" };
  }
  if (kind === "video") {
    return { kind: "video", media_id: "", video_url: "", caption: "", delay_ms: 0, insert_key: "customer_name" };
  }
  if (kind === "audio") {
    return { kind: "audio", media_id: "", audio_url: "", delay_ms: 0, insert_key: "customer_name" };
  }
  return { kind: "text", text: "", delay_ms: 0, insert_key: "customer_name" };
}

function renderText(text, vars) {
  let out = String(text || "");
  Object.entries(vars || {}).forEach(([k, v]) => {
    out = out.split(`{{${k}}}`).join(String(v ?? ""));
  });
  return out;
}

function normalizeTemplateBlocks(rawBlocks, bodyFallback = "") {
  const out = [];
  const blocks = Array.isArray(rawBlocks) ? rawBlocks : [];

  blocks.forEach((b) => {
    if (!b || typeof b !== "object") return;
    const kind = String(b.kind || b.type || "text").toLowerCase();
    const delayMs = Number.isFinite(Number(b.delay_ms)) ? Math.max(0, Number(b.delay_ms)) : 0;

    if (kind === "image" || kind === "video" || kind === "audio") {
      const mediaId = String(b.media_id || "").trim();
      const mediaUrl = String(
        (kind === "image" ? b.image_url : kind === "video" ? b.video_url : b.audio_url)
        || b.media_url
        || b.url
        || ""
      ).trim();
      const caption = String(b.caption || "");
      if (!mediaId && !mediaUrl) return;
      if (kind === "image") {
        out.push({ kind: "image", media_id: mediaId, image_url: mediaUrl, caption, delay_ms: delayMs, insert_key: "customer_name" });
        return;
      }
      if (kind === "video") {
        out.push({ kind: "video", media_id: mediaId, video_url: mediaUrl, caption, delay_ms: delayMs, insert_key: "customer_name" });
        return;
      }
      out.push({ kind: "audio", media_id: mediaId, audio_url: mediaUrl, delay_ms: delayMs, insert_key: "customer_name" });
      return;
    }

    const txt = String(b.text || b.content || b.body || "");
    if (!txt.trim()) return;
    out.push({ kind: "text", text: txt, delay_ms: delayMs, insert_key: "customer_name" });
  });

  if (out.length === 0 && String(bodyFallback || "").trim()) {
    out.push({ kind: "text", text: String(bodyFallback), delay_ms: 0, insert_key: "customer_name" });
  }

  if (out.length === 0) out.push(emptyBlock("text"));
  return out;
}

function paramsRowsFromJson(raw, fallbackKeys = []) {
  const rows = [];
  const obj = raw && typeof raw === "object" ? raw : {};

  Object.entries(obj).forEach(([key, value]) => {
    rows.push({ key: String(key || ""), example: String(value ?? "") });
  });

  fallbackKeys.forEach((k) => {
    const key = String(k || "").trim();
    if (!key) return;
    if (!rows.some((r) => r.key === key)) rows.push({ key, example: "" });
  });

  if (!rows.length) rows.push({ key: "customer_name", example: "Juan Perez" });
  return rows;
}

function buildEditorSignature(form, blocks, params) {
  const normalizedForm = {
    name: String(form?.name || "").trim(),
    category: String(form?.category || "general").trim().toLowerCase() || "general",
    status: String(form?.status || "draft").trim().toLowerCase() || "draft",
    render_mode: String(form?.render_mode || "chat").trim().toLowerCase() || "chat",
    body: String(form?.body || ""),
  };

  const normalizedBlocks = (blocks || []).map((b) => ({
    kind: String(b?.kind || "text").toLowerCase(),
    text: String(b?.text || ""),
    media_id: String(b?.media_id || ""),
    image_url: String(b?.image_url || ""),
    video_url: String(b?.video_url || ""),
    audio_url: String(b?.audio_url || ""),
    caption: String(b?.caption || ""),
    delay_ms: Number(b?.delay_ms || 0),
  }));

  const normalizedParams = (params || []).map((p) => ({
    key: String(p?.key || "").trim(),
    example: String(p?.example || ""),
  }));

  return JSON.stringify({ form: normalizedForm, blocks: normalizedBlocks, params: normalizedParams });
}

function buildEditorStateFromTemplate(tpl) {
  if (!tpl) {
    return {
      form: emptyTemplateForm(),
      blocks: [emptyBlock("text")],
      params: [{ key: "customer_name", example: "Juan Perez" }],
    };
  }

  return {
    form: {
      id: tpl.id,
      name: tpl.name || "",
      category: tpl.category || "general",
      status: tpl.status || "draft",
      render_mode: tpl.render_mode || "chat",
      body: tpl.body || "",
    },
    blocks: normalizeTemplateBlocks(tpl.blocks_json, tpl.body || ""),
    params: paramsRowsFromJson(tpl.params_json, tpl.variables_json || []),
  };
}

function fmtDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

function statusLabel(value) {
  const key = String(value || "").toLowerCase();
  return TEMPLATE_STATUS_OPTIONS.find((s) => s.value === key)?.label || key || "-";
}

export default function TemplateBuilderPanel({
  apiBase,
  templates,
  onTemplatesReload,
  onError,
  onStatus,
}) {
  const API = (apiBase || "").replace(/\/$/, "");
  const initialEditor = useMemo(() => buildEditorStateFromTemplate(null), []);

  const [paramsCatalog, setParamsCatalog] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState(null);
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [templateSearch, setTemplateSearch] = useState("");
  const [templateStatusFilter, setTemplateStatusFilter] = useState("all");

  const [templateForm, setTemplateForm] = useState(initialEditor.form);
  const [templateBlocks, setTemplateBlocks] = useState(initialEditor.blocks);
  const [paramRows, setParamRows] = useState(initialEditor.params);
  const [showChatPreview, setShowChatPreview] = useState(true);
  const [draggingBlockIndex, setDraggingBlockIndex] = useState(null);
  const [dragOverBlockIndex, setDragOverBlockIndex] = useState(null);
  const [baselineSignature, setBaselineSignature] = useState(() => buildEditorSignature(initialEditor.form, initialEditor.blocks, initialEditor.params));
  const [recordingBlockIndex, setRecordingBlockIndex] = useState(null);
  const mediaRecorderRef = useRef(null);
  const recordingStreamRef = useRef(null);
  const recordingChunksRef = useRef([]);

  useEffect(() => {
    const loadCatalog = async () => {
      try {
        const r = await fetch(`${API}/api/templates/params/catalog`);
        const d = await r.json();
        if (!r.ok) throw new Error(d?.detail || "No se pudo cargar catalogo de parametros");
        setParamsCatalog(Array.isArray(d?.params) ? d.params : []);
      } catch (e) {
        onError?.(String(e.message || e));
      }
    };
    loadCatalog();
  }, [API, onError]);

  useEffect(() => {
    return () => {
      try {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
          mediaRecorderRef.current.stop();
        }
      } catch (_) {
        // no-op
      }
      if (recordingStreamRef.current) {
        recordingStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      mediaRecorderRef.current = null;
      recordingStreamRef.current = null;
      recordingChunksRef.current = [];
    };
  }, []);

  const selectedTemplate = useMemo(() => {
    if (!selectedTemplateId) return null;
    return (templates || []).find((t) => t.id === selectedTemplateId) || null;
  }, [templates, selectedTemplateId]);

  const filteredTemplates = useMemo(() => {
    const q = String(templateSearch || "").trim().toLowerCase();
    return (templates || []).filter((t) => {
      const st = String(t.status || "").toLowerCase();
      if (templateStatusFilter !== "all" && st !== templateStatusFilter) return false;
      if (!q) return true;
      const haystack = `${t.name || ""} ${t.category || ""} ${t.body || ""}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [templateSearch, templateStatusFilter, templates]);

  const previewVars = useMemo(() => {
    const out = {};
    (paramRows || []).forEach((r) => {
      const k = String(r?.key || "").trim();
      if (!k) return;
      out[k] = String(r?.example || "");
    });
    return out;
  }, [paramRows]);

  const previewBlocks = useMemo(() => {
    return (templateBlocks || []).map((b) => {
      const kind = String(b.kind || "text").toLowerCase();
      if (kind === "image" || kind === "video" || kind === "audio") {
        const mediaUrl = String(
          (kind === "image" ? b.image_url : kind === "video" ? b.video_url : b.audio_url)
          || b.media_url
          || ""
        );
        const out = {
          kind,
          media_id: String(b.media_id || ""),
          delay_ms: Number(b.delay_ms || 0),
        };
        if (kind === "image") out.image_url = mediaUrl;
        if (kind === "video") out.video_url = mediaUrl;
        if (kind === "audio") out.audio_url = mediaUrl;
        if (kind === "image" || kind === "video") {
          out.caption = renderText(String(b.caption || ""), previewVars);
        }
        return out;
      }
      return {
        kind: "text",
        text: renderText(String(b.text || ""), previewVars),
        delay_ms: Number(b.delay_ms || 0),
      };
    });
  }, [templateBlocks, previewVars]);

  const payload = useMemo(() => {
    const paramsObj = {};
    (paramRows || []).forEach((r) => {
      const key = String(r?.key || "").trim();
      if (!key) return;
      paramsObj[key] = String(r?.example || "");
    });

    const blocks = (templateBlocks || [])
      .map((b) => {
        const kind = String(b.kind || "text").toLowerCase();
        const delayMs = Number.isFinite(Number(b.delay_ms)) ? Math.max(0, Number(b.delay_ms)) : 0;
        if (kind === "image" || kind === "video" || kind === "audio") {
          const mediaId = String(b.media_id || "").trim();
          const mediaUrl = String(
            (kind === "image" ? b.image_url : kind === "video" ? b.video_url : b.audio_url)
            || b.media_url
            || ""
          ).trim();
          const out = {
            kind,
            media_id: mediaId,
            delay_ms: delayMs,
          };
          if (kind === "image") out.image_url = mediaUrl;
          if (kind === "video") out.video_url = mediaUrl;
          if (kind === "audio") out.audio_url = mediaUrl;
          if (kind === "image" || kind === "video") out.caption = String(b.caption || "");
          return out;
        }
        return {
          kind: "text",
          text: String(b.text || ""),
          delay_ms: delayMs,
        };
      })
      .filter((b) => {
        if (b.kind === "image") return !!(b.media_id || b.image_url);
        if (b.kind === "video") return !!(b.media_id || b.video_url);
        if (b.kind === "audio") return !!(b.media_id || b.audio_url);
        return !!String(b.text || "").trim();
      });

    return {
      name: String(templateForm.name || "").trim(),
      category: String(templateForm.category || "general").trim().toLowerCase() || "general",
      status: String(templateForm.status || "draft").trim().toLowerCase() || "draft",
      render_mode: String(templateForm.render_mode || "chat").trim().toLowerCase() || "chat",
      body: String(templateForm.body || "").trim(),
      variables_json: Object.keys(paramsObj),
      params_json: paramsObj,
      blocks_json: blocks,
    };
  }, [paramRows, templateBlocks, templateForm]);

  const currentSignature = useMemo(
    () => buildEditorSignature(templateForm, templateBlocks, paramRows),
    [templateForm, templateBlocks, paramRows]
  );
  const isDirty = currentSignature !== baselineSignature;

  const applyEditorState = (nextEditor, markClean = true) => {
    setTemplateForm(nextEditor.form);
    setTemplateBlocks(nextEditor.blocks);
    setParamRows(nextEditor.params);
    if (markClean) {
      setBaselineSignature(buildEditorSignature(nextEditor.form, nextEditor.blocks, nextEditor.params));
    }
  };

  const confirmDiscardIfDirty = () => {
    if (!isDirty) return true;
    return window.confirm("Tienes cambios sin guardar. Si continuas, se descartaran. ¿Deseas seguir?");
  };

  const handleNewTemplate = () => {
    if (!confirmDiscardIfDirty()) return;
    const fresh = buildEditorStateFromTemplate(null);
    setIsCreatingNew(true);
    setSelectedTemplateId(null);
    applyEditorState(fresh, true);
    onStatus?.("Modo nueva plantilla");
  };

  const handleSelectTemplate = (templateId) => {
    const nextId = Number(templateId || 0);
    if (!nextId) return;
    if (!isCreatingNew && selectedTemplateId === nextId) return;
    if (!confirmDiscardIfDirty()) return;
    setIsCreatingNew(false);
    setSelectedTemplateId(nextId);
  };

  useEffect(() => {
    if (isCreatingNew) return;
    const rows = templates || [];
    if (!rows.length) {
      if (!selectedTemplateId) {
        const fresh = buildEditorStateFromTemplate(null);
        applyEditorState(fresh, true);
      }
      return;
    }

    const exists = rows.some((x) => x.id === selectedTemplateId);
    if (!selectedTemplateId || !exists) {
      setSelectedTemplateId(rows[0].id);
    }
  }, [templates, selectedTemplateId, isCreatingNew]);

  useEffect(() => {
    if (isCreatingNew) return;
    if (!selectedTemplateId) return;
    const t = (templates || []).find((x) => x.id === selectedTemplateId);
    if (!t) return;
    applyEditorState(buildEditorStateFromTemplate(t), true);
  }, [selectedTemplateId, templates, isCreatingNew]);

  const saveTemplate = async () => {
    try {
      if (!payload.name) throw new Error("Nombre de plantilla requerido");

      const isUpdate = !isCreatingNew && !!selectedTemplateId;
      const url = isUpdate
        ? `${API}/api/templates/${encodeURIComponent(selectedTemplateId)}`
        : `${API}/api/templates`;
      const method = isUpdate ? "PATCH" : "POST";

      const r = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo guardar plantilla");

      const tpl = d?.template || null;
      if (tpl?.id) {
        setIsCreatingNew(false);
        setSelectedTemplateId(tpl.id);
        applyEditorState(buildEditorStateFromTemplate(tpl), true);
      } else {
        setBaselineSignature(buildEditorSignature(templateForm, templateBlocks, paramRows));
      }

      await onTemplatesReload?.();
      onStatus?.(isUpdate ? "Plantilla actualizada" : "Plantilla creada");
    } catch (e) {
      onError?.(String(e.message || e));
    }
  };

  const revertTemplate = () => {
    if (isCreatingNew || !selectedTemplateId) {
      const fresh = buildEditorStateFromTemplate(null);
      applyEditorState(fresh, true);
      onStatus?.("Formulario limpio");
      return;
    }
    const t = (templates || []).find((x) => x.id === selectedTemplateId);
    if (!t) return;
    applyEditorState(buildEditorStateFromTemplate(t), true);
    onStatus?.("Cambios revertidos");
  };

  const deleteTemplate = async () => {
    if (!selectedTemplateId || isCreatingNew) return;
    const label = selectedTemplate?.name || `#${selectedTemplateId}`;
    const ok = window.confirm(`Se eliminara la plantilla "${label}". Esta accion no se puede deshacer.\n\n¿Continuar?`);
    if (!ok) return;
    try {
      const r = await fetch(`${API}/api/templates/${encodeURIComponent(selectedTemplateId)}`, {
        method: "DELETE",
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo eliminar plantilla");
      setSelectedTemplateId(null);
      setIsCreatingNew(false);
      await onTemplatesReload?.();
      onStatus?.(`Plantilla eliminada: ${label}`);
    } catch (e) {
      onError?.(String(e.message || e));
    }
  };

  const addParamRow = () => setParamRows((prev) => [...prev, { key: "", example: "" }]);
  const updateParamRow = (idx, patch) => setParamRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  const removeParamRow = (idx) => setParamRows((prev) => prev.filter((_, i) => i !== idx));

  const addBlock = (kind = "text") => setTemplateBlocks((prev) => [...prev, emptyBlock(kind)]);
  const updateBlock = (idx, patch) => setTemplateBlocks((prev) => prev.map((b, i) => (i === idx ? { ...b, ...patch } : b)));
  const removeBlock = (idx) => setTemplateBlocks((prev) => prev.filter((_, i) => i !== idx));

  const reorderBlocks = (fromIdx, toIdx) => {
    const from = Number(fromIdx);
    const to = Number(toIdx);
    if (!Number.isInteger(from) || !Number.isInteger(to) || from === to) return;
    setTemplateBlocks((prev) => {
      if (from < 0 || to < 0 || from >= prev.length || to >= prev.length) return prev;
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  };

  const handleDragStartBlock = (idx) => {
    setDraggingBlockIndex(idx);
    setDragOverBlockIndex(idx);
  };

  const handleDragOverBlock = (idx, e) => {
    e.preventDefault();
    if (draggingBlockIndex === null) return;
    if (idx !== dragOverBlockIndex) setDragOverBlockIndex(idx);
  };

  const handleDropBlock = (idx, e) => {
    e.preventDefault();
    if (draggingBlockIndex === null) return;
    reorderBlocks(draggingBlockIndex, idx);
    setDraggingBlockIndex(null);
    setDragOverBlockIndex(null);
  };

  const handleDragEndBlock = () => {
    setDraggingBlockIndex(null);
    setDragOverBlockIndex(null);
  };

  const insertParamInBlock = (idx, field) => {
    const block = templateBlocks[idx] || {};
    const key = String(block.insert_key || "").trim();
    if (!key) return;
    if (field !== "caption" && field !== "text") return;
    const token = `{{${key}}}`;
    if (field === "caption") {
      updateBlock(idx, { caption: `${String(block.caption || "")} ${token}`.trim() });
      return;
    }
    updateBlock(idx, { text: `${String(block.text || "")} ${token}`.trim() });
  };

  const appendEmojiToBlockField = (idx, field, emoji) => {
    const block = templateBlocks[idx] || {};
    const current = String(block?.[field] || "");
    updateBlock(idx, { [field]: `${current}${emoji}` });
  };

  const uploadTemplateMedia = async (idx, file, kind) => {
    if (!file) return;
    const mediaKind = String(kind || "image").toLowerCase();
    if (!["image", "video", "audio"].includes(mediaKind)) return;
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("kind", mediaKind);

      const r = await fetch(`${API}/api/media/upload`, { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || `No se pudo subir ${mediaKind}`);

      const mediaId = String(d?.media_id || "").trim();
      const proxyUrl = mediaId ? `${API}/api/media/proxy/${encodeURIComponent(mediaId)}` : "";

      if (mediaKind === "image") {
        updateBlock(idx, { media_id: mediaId, image_url: proxyUrl });
      } else if (mediaKind === "video") {
        updateBlock(idx, { media_id: mediaId, video_url: proxyUrl });
      } else {
        updateBlock(idx, { media_id: mediaId, audio_url: proxyUrl });
      }
      onStatus?.(`${mediaKind[0].toUpperCase()}${mediaKind.slice(1)} cargado al template`);
    } catch (e) {
      onError?.(String(e.message || e));
    }
  };

  const startAudioRecording = async (idx) => {
    try {
      if (typeof window === "undefined" || typeof window.MediaRecorder === "undefined") {
        throw new Error("Tu navegador no soporta grabacion de audio");
      }
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("No se pudo acceder al microfono");
      }

      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
      if (recordingStreamRef.current) {
        recordingStreamRef.current.getTracks().forEach((t) => t.stop());
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferredMimeTypes = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/ogg",
      ];
      const selectedMime = preferredMimeTypes.find((m) => {
        try {
          return window.MediaRecorder.isTypeSupported(m);
        } catch (_) {
          return false;
        }
      });

      const recorder = selectedMime ? new window.MediaRecorder(stream, { mimeType: selectedMime }) : new window.MediaRecorder(stream);
      recordingChunksRef.current = [];
      recordingStreamRef.current = stream;
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) {
          recordingChunksRef.current.push(ev.data);
        }
      };

      recorder.onstop = async () => {
        setRecordingBlockIndex(null);
        const mimeType = recorder.mimeType || selectedMime || "audio/webm";
        const blob = new Blob(recordingChunksRef.current, { type: mimeType });
        recordingChunksRef.current = [];
        if (recordingStreamRef.current) {
          recordingStreamRef.current.getTracks().forEach((t) => t.stop());
          recordingStreamRef.current = null;
        }
        mediaRecorderRef.current = null;

        if (!blob.size) {
          onError?.("No se capturo audio");
          return;
        }

        const ext = mimeType.includes("ogg") ? "ogg" : "webm";
        const file = new File([blob], `audio-${Date.now()}.${ext}`, { type: mimeType });
        await uploadTemplateMedia(idx, file, "audio");
      };

      recorder.start();
      setRecordingBlockIndex(idx);
      onStatus?.("Grabando audio...");
    } catch (e) {
      setRecordingBlockIndex(null);
      onError?.(String(e.message || e));
    }
  };

  const stopAudioRecording = () => {
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
        setRecordingBlockIndex(null);
        onStatus?.("Procesando audio...");
      }
    } catch (e) {
      onError?.(String(e.message || e));
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "420px 1fr", gap: 12, alignItems: "start" }}>
      <div style={{ ...box, display: "grid", gap: 10, maxHeight: 740, overflow: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>Plantillas</h3>
          <button style={{ ...smallBtn, borderColor: "#2ecc71" }} onClick={handleNewTemplate}>+ Nueva</button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 140px", gap: 8 }}>
          <input
            style={input}
            placeholder="Buscar..."
            value={templateSearch}
            onChange={(e) => setTemplateSearch(e.target.value)}
          />
          <select style={input} value={templateStatusFilter} onChange={(e) => setTemplateStatusFilter(e.target.value)}>
            <option value="all">Todos</option>
            {TEMPLATE_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div style={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 90px 170px", gap: 8, padding: "8px 10px", fontSize: 12, opacity: 0.8, borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
            <div>Nombre</div>
            <div>Mensajes</div>
            <div>Creado</div>
          </div>

          <div style={{ maxHeight: 590, overflow: "auto", display: "grid" }}>
            {filteredTemplates.map((t) => {
              const count = normalizeTemplateBlocks(t.blocks_json, t.body || "").length;
              const selected = !isCreatingNew && selectedTemplateId === t.id;
              return (
                <button
                  type="button"
                  key={t.id}
                  onClick={() => handleSelectTemplate(t.id)}
                  style={{
                    textAlign: "left",
                    border: "none",
                    borderBottom: "1px solid rgba(255,255,255,0.08)",
                    background: selected ? "rgba(255,255,255,0.12)" : "transparent",
                    color: "inherit",
                    padding: "10px",
                    cursor: "pointer",
                    display: "grid",
                    gridTemplateColumns: "1fr 90px 170px",
                    gap: 8,
                    alignItems: "center",
                  }}
                  title={`Estado: ${statusLabel(t.status)}${t.category ? ` | Categoria: ${t.category}` : ""}`}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{t.name || "(sin nombre)"}</div>
                    <div style={{ fontSize: 11, opacity: 0.7 }}>{statusLabel(t.status)}</div>
                  </div>
                  <div>{count}</div>
                  <div style={{ fontSize: 12, opacity: 0.85 }}>{fmtDate(t.created_at)}</div>
                </button>
              );
            })}
            {!filteredTemplates.length ? (
              <div style={{ padding: 14, fontSize: 13, opacity: 0.7 }}>No hay plantillas para ese filtro.</div>
            ) : null}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(520px, 1fr) minmax(320px, 0.9fr)", gap: 12, alignItems: "start" }}>
        <div style={{ ...box, display: "grid", gap: 12, maxHeight: 740, overflow: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
            <div>
              <h3 style={{ margin: 0 }}>{isCreatingNew ? "Nueva plantilla" : (selectedTemplate?.name || "Plantilla")}</h3>
              <div style={{ fontSize: 12, opacity: 0.75 }}>
                {isCreatingNew ? "Modo creacion" : `ID #${selectedTemplate?.id || "-"} | ${statusLabel(templateForm.status)}`}
              </div>
            </div>
            <div style={{ fontSize: 12, color: isDirty ? "#f6c15b" : "#9be15d" }}>
              {isDirty ? "Cambios sin guardar" : "Guardado"}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Nombre</div>
              <input style={input} value={templateForm.name} onChange={(e) => setTemplateForm((p) => ({ ...p, name: e.target.value }))} />
            </label>
            <label>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Categoria</div>
              <input style={input} value={templateForm.category} onChange={(e) => setTemplateForm((p) => ({ ...p, category: e.target.value }))} />
            </label>
            <label>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Estado</div>
              <select style={input} value={templateForm.status} onChange={(e) => setTemplateForm((p) => ({ ...p, status: e.target.value }))}>
                {TEMPLATE_STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
            <label>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Vista</div>
              <select style={input} value={templateForm.render_mode} onChange={(e) => setTemplateForm((p) => ({ ...p, render_mode: e.target.value }))}>
                {TEMPLATE_RENDER_MODE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <h4 style={{ margin: 0 }}>Parametros (opcional)</h4>
              <button style={smallBtn} onClick={addParamRow}>+ Parametro</button>
            </div>
            <div style={{ display: "grid", gap: 6 }}>
              {paramRows.map((row, idx) => (
                <div key={`pr-${idx}`} style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 6 }}>
                  <select style={input} value={row.key} onChange={(e) => updateParamRow(idx, { key: e.target.value })}>
                    <option value="">Parametro...</option>
                    {(paramsCatalog || []).map((p) => (
                      <option key={p.key} value={p.key}>{p.label} ({p.key})</option>
                    ))}
                  </select>
                  <input style={input} value={row.example} onChange={(e) => updateParamRow(idx, { example: e.target.value })} placeholder="Ejemplo" />
                  <button style={smallBtn} onClick={() => removeParamRow(idx)}>x</button>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <h4 style={{ margin: 0 }}>Mensajes de la secuencia</h4>
              <div style={{ display: "flex", gap: 6 }}>
                <button style={smallBtn} onClick={() => addBlock("text")}>+ Texto</button>
                <button style={smallBtn} onClick={() => addBlock("image")}>+ Imagen</button>
                <button style={smallBtn} onClick={() => addBlock("video")}>+ Video</button>
                <button style={smallBtn} onClick={() => addBlock("audio")}>+ Audio</button>
              </div>
            </div>

            <div style={{ display: "grid", gap: 8 }}>
              {templateBlocks.map((b, idx) => {
                const kind = String(b.kind || "text").toLowerCase();
                const insertField = kind === "image" || kind === "video" ? "caption" : kind === "text" ? "text" : "";
                return (
                  <div
                    key={`blk-${idx}`}
                    onDragOver={(e) => handleDragOverBlock(idx, e)}
                    onDrop={(e) => handleDropBlock(idx, e)}
                    style={{
                      border: dragOverBlockIndex === idx ? "1px solid rgba(46,204,113,0.95)" : "1px solid rgba(255,255,255,0.14)",
                      borderRadius: 10,
                      padding: 10,
                    }}
                  >
                    <div style={{ display: "grid", gridTemplateColumns: "auto 130px 1fr auto", gap: 6, marginBottom: 8 }}>
                      <button
                        style={{ ...smallBtn, cursor: "grab", whiteSpace: "nowrap" }}
                        title="Arrastrar para reordenar"
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.effectAllowed = "move";
                          e.dataTransfer.setData("text/plain", String(idx));
                          handleDragStartBlock(idx);
                        }}
                        onDragEnd={handleDragEndBlock}
                      >
                        Arrastrar
                      </button>
                      <select
                        style={input}
                        value={kind}
                        onChange={(e) => {
                          const nextKind = e.target.value;
                          if (nextKind === "image") {
                            updateBlock(idx, {
                              kind: "image",
                              text: undefined,
                              caption: b.caption || b.text || "",
                              media_id: b.media_id || "",
                              image_url: b.image_url || "",
                              video_url: undefined,
                              audio_url: undefined,
                            });
                          } else if (nextKind === "video") {
                            updateBlock(idx, {
                              kind: "video",
                              text: undefined,
                              caption: b.caption || b.text || "",
                              media_id: b.media_id || "",
                              image_url: undefined,
                              video_url: b.video_url || "",
                              audio_url: undefined,
                            });
                          } else if (nextKind === "audio") {
                            updateBlock(idx, {
                              kind: "audio",
                              text: undefined,
                              caption: undefined,
                              media_id: b.media_id || "",
                              image_url: undefined,
                              video_url: undefined,
                              audio_url: b.audio_url || "",
                            });
                          } else {
                            updateBlock(idx, {
                              kind: "text",
                              text: b.text || b.caption || "",
                              caption: undefined,
                              media_id: undefined,
                              image_url: undefined,
                              video_url: undefined,
                              audio_url: undefined,
                            });
                          }
                        }}
                      >
                        <option value="text">Texto</option>
                        <option value="image">Imagen</option>
                        <option value="video">Video</option>
                        <option value="audio">Audio</option>
                      </select>

                      <input style={input} type="number" value={Number(b.delay_ms || 0)} onChange={(e) => updateBlock(idx, { delay_ms: e.target.value })} placeholder="Espera (ms)" />
                      <button style={smallBtn} onClick={() => removeBlock(idx)}>Eliminar</button>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 6, marginBottom: 6 }}>
                      <select style={input} value={b.insert_key || ""} onChange={(e) => updateBlock(idx, { insert_key: e.target.value })}>
                        <option value="">Insertar parametro...</option>
                        {(paramsCatalog || []).map((p) => (
                          <option key={p.key} value={p.key}>{p.label} ({p.key})</option>
                        ))}
                      </select>
                      <button style={smallBtn} disabled={!insertField} onClick={() => insertParamInBlock(idx, insertField)}>Insertar</button>
                    </div>

                    {kind === "image" ? (
                      <div style={{ display: "grid", gap: 6 }}>
                        <input style={input} value={b.media_id || ""} onChange={(e) => updateBlock(idx, { media_id: e.target.value })} placeholder="media_id de WhatsApp" />
                        <input style={input} value={b.image_url || ""} onChange={(e) => updateBlock(idx, { image_url: e.target.value })} placeholder="URL de vista previa (opcional)" />
                        <div style={{ display: "flex", justifyContent: "flex-end" }}>
                          <EmojiPickerButton onSelect={(emoji) => appendEmojiToBlockField(idx, "caption", emoji)} title="Agregar emoji al caption" />
                        </div>
                        <textarea style={{ ...input, minHeight: 70 }} value={b.caption || ""} onChange={(e) => updateBlock(idx, { caption: e.target.value })} placeholder="Texto de la imagen" />
                        <label style={{ ...smallBtn, display: "inline-flex", alignItems: "center", width: "fit-content" }}>
                          Subir imagen
                          <input type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => uploadTemplateMedia(idx, e.target.files?.[0], "image")} />
                        </label>
                      </div>
                    ) : kind === "video" ? (
                      <div style={{ display: "grid", gap: 6 }}>
                        <input style={input} value={b.media_id || ""} onChange={(e) => updateBlock(idx, { media_id: e.target.value })} placeholder="media_id de WhatsApp" />
                        <input style={input} value={b.video_url || ""} onChange={(e) => updateBlock(idx, { video_url: e.target.value })} placeholder="URL de vista previa (opcional)" />
                        <div style={{ display: "flex", justifyContent: "flex-end" }}>
                          <EmojiPickerButton onSelect={(emoji) => appendEmojiToBlockField(idx, "caption", emoji)} title="Agregar emoji al caption" />
                        </div>
                        <textarea style={{ ...input, minHeight: 70 }} value={b.caption || ""} onChange={(e) => updateBlock(idx, { caption: e.target.value })} placeholder="Texto del video" />
                        <label style={{ ...smallBtn, display: "inline-flex", alignItems: "center", width: "fit-content" }}>
                          Subir video
                          <input type="file" accept="video/*" style={{ display: "none" }} onChange={(e) => uploadTemplateMedia(idx, e.target.files?.[0], "video")} />
                        </label>
                      </div>
                    ) : kind === "audio" ? (
                      <div style={{ display: "grid", gap: 6 }}>
                        <input style={input} value={b.media_id || ""} onChange={(e) => updateBlock(idx, { media_id: e.target.value })} placeholder="media_id de WhatsApp" />
                        <input style={input} value={b.audio_url || ""} onChange={(e) => updateBlock(idx, { audio_url: e.target.value })} placeholder="URL de vista previa (opcional)" />
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          <label style={{ ...smallBtn, display: "inline-flex", alignItems: "center", width: "fit-content" }}>
                            Subir audio
                            <input type="file" accept="audio/*" style={{ display: "none" }} onChange={(e) => uploadTemplateMedia(idx, e.target.files?.[0], "audio")} />
                          </label>
                          {recordingBlockIndex === idx ? (
                            <button style={{ ...smallBtn, borderColor: "#ff7675" }} onClick={stopAudioRecording}>
                              Detener grabacion
                            </button>
                          ) : (
                            <button style={smallBtn} onClick={() => startAudioRecording(idx)}>
                              Grabar microfono
                            </button>
                          )}
                        </div>
                        {(b.audio_url || b.media_id) ? (
                          <audio controls src={b.audio_url || `${API}/api/media/proxy/${encodeURIComponent(b.media_id)}`} />
                        ) : null}
                      </div>
                    ) : (
                      <div style={{ display: "grid", gap: 6 }}>
                        <div style={{ display: "flex", justifyContent: "flex-end" }}>
                          <EmojiPickerButton onSelect={(emoji) => appendEmojiToBlockField(idx, "text", emoji)} title="Agregar emoji al texto" />
                        </div>
                        <textarea style={{ ...input, minHeight: 85 }} value={b.text || ""} onChange={(e) => updateBlock(idx, { text: e.target.value })} placeholder="Texto del mensaje" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button style={{ ...smallBtn, borderColor: "#2ecc71" }} onClick={saveTemplate}>Guardar</button>
            <button style={smallBtn} onClick={revertTemplate}>Revertir</button>
            <button style={dangerBtn} onClick={deleteTemplate} disabled={isCreatingNew || !selectedTemplateId}>Eliminar plantilla</button>
          </div>
        </div>

        <div style={{ ...box, minHeight: 740, maxHeight: 740, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <h3 style={{ margin: 0 }}>Mensajes</h3>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
              <input type="checkbox" checked={showChatPreview} onChange={(e) => setShowChatPreview(e.target.checked)} />
              Vista chat
            </label>
          </div>

          <div
            style={{
              flex: 1,
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.12)",
              padding: 10,
              overflow: "auto",
              background: "rgba(0,0,0,0.18)",
              display: "grid",
              gap: 8,
            }}
          >
            {previewBlocks.map((m, idx) => (
              <div
                key={`pv-${idx}`}
                onDragOver={(e) => handleDragOverBlock(idx, e)}
                onDrop={(e) => handleDropBlock(idx, e)}
                style={{
                  border: dragOverBlockIndex === idx ? "1px dashed rgba(46,204,113,0.95)" : "1px dashed transparent",
                  borderRadius: 10,
                  padding: 4,
                }}
              >
                <div style={{ display: "flex", justifyContent: showChatPreview ? "flex-end" : "flex-start", marginBottom: 4 }}>
                  <button
                    style={{ ...smallBtn, padding: "4px 8px", fontSize: 12, cursor: "grab" }}
                    title="Arrastrar para reordenar"
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.effectAllowed = "move";
                      e.dataTransfer.setData("text/plain", String(idx));
                      handleDragStartBlock(idx);
                    }}
                    onDragEnd={handleDragEndBlock}
                  >
                    Arrastrar
                  </button>
                </div>
                <div
                  style={{
                    maxWidth: "88%",
                    marginLeft: showChatPreview ? "auto" : 0,
                    background: showChatPreview ? "rgba(8,122,111,0.85)" : "rgba(255,255,255,0.06)",
                    color: "#fff",
                    padding: "8px 10px",
                    borderRadius: 10,
                    fontSize: 14,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {m.kind === "image" ? (
                    <>
                      {(m.image_url || m.media_id) ? (
                        <div style={{ marginBottom: m.caption ? 8 : 0 }}>
                          <img
                            src={m.image_url || `${API}/api/media/proxy/${encodeURIComponent(m.media_id)}`}
                            alt="preview"
                            style={{ maxWidth: 260, borderRadius: 8, display: "block" }}
                          />
                        </div>
                      ) : null}
                      {m.caption || "[imagen]"}
                    </>
                  ) : m.kind === "video" ? (
                    <>
                      {(m.video_url || m.media_id) ? (
                        <div style={{ marginBottom: m.caption ? 8 : 0 }}>
                          <video
                            src={m.video_url || `${API}/api/media/proxy/${encodeURIComponent(m.media_id)}`}
                            controls
                            style={{ maxWidth: 260, borderRadius: 8, display: "block" }}
                          />
                        </div>
                      ) : null}
                      {m.caption || "[video]"}
                    </>
                  ) : m.kind === "audio" ? (
                    <>
                      {(m.audio_url || m.media_id) ? (
                        <audio controls src={m.audio_url || `${API}/api/media/proxy/${encodeURIComponent(m.media_id)}`} />
                      ) : null}
                      {!m.audio_url && !m.media_id ? "[audio]" : ""}
                    </>
                  ) : (
                    m.text || "[texto vacio]"
                  )}
                </div>
                <div style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>
                  delay: {Number(m.delay_ms || 0)} ms
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
