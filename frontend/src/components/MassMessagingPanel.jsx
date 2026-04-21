import React, { useEffect, useMemo, useRef, useState } from "react";
import useViewport from "../hooks/useViewport";

const shell = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  display: "flex",
  flexDirection: "column",
  gap: 12,
  padding: 12,
  overflow: "auto",
};

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

const menuCard = {
  border: "1px solid rgba(148,163,184,0.35)",
  borderRadius: 12,
  background: "#0f172a",
  boxShadow: "0 20px 40px rgba(2,6,23,0.45)",
  padding: 10,
};

const MODULES = [
  { id: "ai_agent", title: "AI Agent", description: "Skeleton: reglas IA para outbound y copys automaticos." },
  { id: "broadcast_campaign", title: "Broadcast Campaign", description: "Skeleton: campanas de envio masivo." },
  { id: "chat_widget", title: "Chat Widget", description: "Skeleton: widget embebido para captura y conversion." },
  { id: "sequence", title: "Secuencia", description: "Skeleton: secuencias de seguimiento por pasos y tiempos." },
  { id: "input_flow", title: "Input Flow", description: "Skeleton: formularios/flows para calificar leads." },
  { id: "whatsapp_flows", title: "WhatsApp Flows", description: "Skeleton: flows interactivos de WhatsApp." },
  { id: "message_template", title: "Message Template", description: "Activo: plantillas oficiales para broadcast." },
  { id: "wc_shopify_automation", title: "WC/Shopify Automation", description: "Skeleton: automatizaciones ecommerce." },
  { id: "outbound_webhook", title: "Out-bound Webhook", description: "Skeleton: webhooks de salida." },
  { id: "action_buttons", title: "Action Buttons", description: "Skeleton: botones CTA de conversion." },
  { id: "configuration", title: "Configuracion", description: "Skeleton: ajustes globales de mensajeria masiva." },
];

const LOCALE_OPTIONS = [
  { value: "es", label: "Spanish" },
  { value: "en_US", label: "English (US)" },
  { value: "pt_BR", label: "Portuguese (BR)" },
];

const CATEGORY_OPTIONS = [
  { value: "UTILITY", label: "Utility" },
  { value: "MARKETING", label: "Marketing" },
  { value: "AUTHENTICATION", label: "Auth/OTP" },
];

const HEADER_OPTIONS = [
  { value: "", label: "No Header" },
  { value: "TEXT", label: "Text" },
  { value: "IMAGE", label: "Image" },
  { value: "VIDEO", label: "Video" },
  { value: "DOCUMENT", label: "Document" },
];

const BUTTON_PRESET_OPTIONS = [
  { id: "quick_reply", label: "Quick reply buttons", hint: "hasta 3 botones" },
  { id: "visit_website", label: "Visit website", hint: "maximo 2 botones URL" },
  { id: "call_phone", label: "Call phone number", hint: "maximo 1 boton telefono" },
  { id: "copy_offer_code", label: "Copy offer code", hint: "maximo 1 boton" },
];

const COUNTRY_OPTIONS = [
  { value: "+57", label: "Colombia (+57)" },
  { value: "+52", label: "Mexico (+52)" },
  { value: "+1", label: "USA (+1)" },
  { value: "+34", label: "Espana (+34)" },
];

const TOKEN_EXAMPLES = {
  customer_name: "Juan",
  customer_first_name: "Juan",
  customer_last_name: "Perez",
  customer_phone: "+573001112233",
  customer_email: "juan@email.com",
  customer_city: "Bogota",
  customer_state: "Cundinamarca",
  customer_country: "CO",
  origin: "Instagram Ads",
  purchase_date: "2026-04-20",
  date: "2026-04-20",
  business_name: "Verane Perfumeria",
  business_phone: "+57 323 7028445",
  business_email: "ventas@verane.com",
  assistant_name: "Laura",
  assistant_phone: "+57 300 0000000",
  campaign_name: "Promo mayo",
  objective: "Ventas",
};

function emptyButton(mode = "quick_reply") {
  if (mode === "visit_website") return { mode, type: "URL", text: "Visit website", url_type: "STATIC", url: "" };
  if (mode === "call_phone") return { mode, type: "PHONE_NUMBER", text: "Call Phone Number", country_code: "+57", phone_number: "" };
  if (mode === "copy_offer_code") return { mode, type: "QUICK_REPLY", text: "Copy Offer Code", offer_code: "" };
  return { mode: "quick_reply", type: "QUICK_REPLY", subtype: "CUSTOM", text: "Quick Reply" };
}

function emptyForm() {
  return {
    name: "",
    language: "es",
    category: "UTILITY",
    header_type: "",
    header_text: "",
    header_media_handle: "",
    body_text: "",
    footer_text: "",
    buttons: [],
    allow_category_change: true,
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

function renderWithTokens(text, examples) {
  return String(text || "").replace(/\{\{\s*([a-zA-Z0-9_-]+)\s*\}\}/g, (_, key) => {
    const token = String(key || "").trim();
    if (!token) return "";
    return String(examples?.[token] || `{{${token}}}`);
  });
}

function getButtonMode(btn) {
  const mode = String(btn?.mode || "").trim();
  if (mode) return mode;
  const type = String(btn?.type || "").trim().toUpperCase();
  if (type === "URL") return "visit_website";
  if (type === "PHONE_NUMBER") return "call_phone";
  return "quick_reply";
}

function statusColor(status) {
  const token = String(status || "").trim().toLowerCase();
  if (token === "approved") return "#9df0bf";
  if (token === "rejected") return "#ffb7b7";
  if (token === "paused") return "#ffd27f";
  return "#cbd5e1";
}

function categoryColor(category) {
  const token = String(category || "").trim().toUpperCase();
  if (token === "MARKETING") return "#7dd3fc";
  if (token === "UTILITY") return "#bbf7d0";
  if (token === "AUTHENTICATION") return "#fecaca";
  return "#cbd5e1";
}

export default function MassMessagingPanel({ apiBase }) {
  const API = (apiBase || "").replace(/\/$/, "");
  const { isMobile, isTablet } = useViewport();
  const bodyRef = useRef(null);

  const [activeModule, setActiveModule] = useState("message_template");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [creatingTemplate, setCreatingTemplate] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [paramsCatalog, setParamsCatalog] = useState([]);
  const [showCustomMenu, setShowCustomMenu] = useState(false);
  const [showVarsMenu, setShowVarsMenu] = useState(false);
  const [showAddButtonMenu, setShowAddButtonMenu] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const gridCols = isMobile ? "1fr" : isTablet ? "repeat(2, minmax(0, 1fr))" : "repeat(3, minmax(0, 1fr))";
  const editorCols = isMobile ? "1fr" : "minmax(540px, 1fr) minmax(360px, 430px)";

  const activeModuleMeta = useMemo(() => {
    return MODULES.find((m) => m.id === activeModule) || MODULES[0];
  }, [activeModule]);

  const customFields = useMemo(() => {
    const rows = Array.isArray(paramsCatalog) ? paramsCatalog : [];
    return rows.filter((p) => String(p?.group || "").trim().toLowerCase() === "custom_field");
  }, [paramsCatalog]);

  const systemVars = useMemo(() => {
    const rows = Array.isArray(paramsCatalog) ? paramsCatalog : [];
    return rows.filter((p) => String(p?.group || "").trim().toLowerCase() === "system_variable");
  }, [paramsCatalog]);

  const bodyChars = String(form.body_text || "").length;
  const headerType = String(form.header_type || "").trim().toUpperCase();
  const menuOpen = showCustomMenu || showVarsMenu || showAddButtonMenu;

  const indexedButtons = useMemo(() => {
    return (Array.isArray(form.buttons) ? form.buttons : []).map((btn, idx) => ({ ...btn, _idx: idx, _mode: getButtonMode(btn) }));
  }, [form.buttons]);
  const quickReplyRows = useMemo(() => {
    return indexedButtons.filter((btn) => btn._mode === "quick_reply");
  }, [indexedButtons]);
  const ctaRows = useMemo(() => {
    return indexedButtons.filter((btn) => ["visit_website", "call_phone", "copy_offer_code"].includes(btn._mode));
  }, [indexedButtons]);

  const previewBody = useMemo(() => {
    return renderWithTokens(form.body_text || "", TOKEN_EXAMPLES);
  }, [form.body_text]);

  const previewFooter = useMemo(() => {
    return renderWithTokens(form.footer_text || "", TOKEN_EXAMPLES);
  }, [form.footer_text]);

  const loadCatalog = async () => {
    try {
      const r = await fetch(`${API}/api/templates/params/catalog`);
      const d = await r.json();
      if (!r.ok) throw new Error(asErrorMessage(d));
      const rows = Array.isArray(d?.params) ? d.params : [];
      setParamsCatalog(rows);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const loadTemplates = async (fromSync = false) => {
    setError("");
    setStatus("");
    setLoadingTemplates(true);
    try {
      const url = fromSync
        ? `${API}/api/broadcast/meta/templates/sync?limit=300`
        : `${API}/api/broadcast/meta/templates?limit=300`;
      const method = fromSync ? "POST" : "GET";
      const r = await fetch(url, { method });
      const d = await r.json();
      if (!r.ok) throw new Error(asErrorMessage(d));
      const rows = Array.isArray(d?.templates) ? d.templates : [];
      setTemplates(rows);
      setStatus(fromSync ? "Plantillas sincronizadas con Meta." : "Plantillas cargadas.");
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoadingTemplates(false);
    }
  };

  useEffect(() => {
    loadTemplates(false);
    loadCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const closeMenus = () => {
    setShowCustomMenu(false);
    setShowVarsMenu(false);
    setShowAddButtonMenu(false);
  };

  const insertTokenInBody = (key) => {
    const token = `{{${String(key || "").trim()}}}`;
    const ta = bodyRef.current;
    closeMenus();
    if (!ta) {
      setForm((prev) => ({ ...prev, body_text: `${String(prev.body_text || "")}${token}` }));
      return;
    }
    const start = ta.selectionStart || 0;
    const end = ta.selectionEnd || 0;
    const current = String(form.body_text || "");
    const next = `${current.slice(0, start)}${token}${current.slice(end)}`;
    setForm((prev) => ({ ...prev, body_text: next }));
    setTimeout(() => {
      const pos = start + token.length;
      ta.focus();
      ta.setSelectionRange(pos, pos);
    }, 0);
  };

  const updateButton = (idx, patch) => {
    setForm((prev) => ({
      ...prev,
      buttons: (Array.isArray(prev.buttons) ? prev.buttons : []).map((b, i) =>
        i === idx ? { ...b, ...patch } : b
      ),
    }));
  };

  const removeButton = (idx) => {
    setForm((prev) => ({
      ...prev,
      buttons: (Array.isArray(prev.buttons) ? prev.buttons : []).filter((_, i) => i !== idx),
    }));
  };

  const setButtonMode = (idx, nextMode) => {
    const rows = Array.isArray(form.buttons) ? form.buttons : [];
    const others = rows.filter((_, i) => i !== idx);
    const countUrl = others.filter((b) => getButtonMode(b) === "visit_website").length;
    const countPhone = others.filter((b) => getButtonMode(b) === "call_phone").length;
    const countCopy = others.filter((b) => getButtonMode(b) === "copy_offer_code").length;

    if (nextMode === "visit_website" && countUrl >= 2) {
      setError("Maximo 2 botones de tipo Visit website.");
      return;
    }
    if (nextMode === "call_phone" && countPhone >= 1) {
      setError("Maximo 1 boton de tipo Call phone number.");
      return;
    }
    if (nextMode === "copy_offer_code" && countCopy >= 1) {
      setError("Maximo 1 boton de tipo Copy offer code.");
      return;
    }

    setError("");
    const fresh = emptyButton(nextMode);
    setForm((prev) => ({
      ...prev,
      buttons: (Array.isArray(prev.buttons) ? prev.buttons : []).map((b, i) => {
        if (i !== idx) return b;
        return {
          ...fresh,
          text: String(b?.text || "").trim() || fresh.text,
          url: String(b?.url || "").trim() || fresh.url || "",
          url_type: String(b?.url_type || "").trim() || fresh.url_type || "STATIC",
          phone_number: String(b?.phone_number || "").trim() || fresh.phone_number || "",
          country_code: String(b?.country_code || "").trim() || fresh.country_code || "+57",
          offer_code: String(b?.offer_code || "").trim() || fresh.offer_code || "",
        };
      }),
    }));
  };

  const addButtonByPreset = (presetId) => {
    const current = Array.isArray(form.buttons) ? form.buttons : [];
    if (current.length >= 3) {
      setError("Meta permite maximo 3 botones por plantilla.");
      return;
    }

    const countUrl = current.filter((b) => getButtonMode(b) === "visit_website").length;
    const countPhone = current.filter((b) => getButtonMode(b) === "call_phone").length;
    const countCopy = current.filter((b) => getButtonMode(b) === "copy_offer_code").length;

    if (presetId === "visit_website" && countUrl >= 2) {
      setError("Maximo 2 botones de tipo Visit website.");
      return;
    }
    if (presetId === "call_phone" && countPhone >= 1) {
      setError("Maximo 1 boton de tipo Call phone number.");
      return;
    }
    if (presetId === "copy_offer_code" && countCopy >= 1) {
      setError("Maximo 1 boton de tipo Copy offer code.");
      return;
    }

    setError("");
    const next = emptyButton(presetId);
    setForm((prev) => ({ ...prev, buttons: [...(prev.buttons || []), next] }));
    closeMenus();
  };

  const runAiRewrite = () => {
    const body = String(form.body_text || "");
    if (!body.trim()) {
      setError("No hay texto para reescribir.");
      return;
    }
    const normalized = body
      .replace(/\s+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .replace(/[ \t]{2,}/g, " ")
      .trim();
    setForm((prev) => ({ ...prev, body_text: normalized }));
    setError("");
    setStatus("Texto optimizado (modo local).");
  };

  const createMetaTemplate = async () => {
    const name = String(form.name || "").trim();
    const bodyText = String(form.body_text || "").trim();
    if (!name) {
      setError("Debes escribir el nombre interno de la plantilla.");
      return;
    }
    if (!bodyText) {
      setError("Debes escribir el cuerpo principal (BODY).");
      return;
    }
    if (bodyText.length > 1024) {
      setError("El body supera 1024 caracteres.");
      return;
    }
    if (headerType === "TEXT" && !String(form.header_text || "").trim()) {
      setError("El header de tipo TEXT requiere contenido.");
      return;
    }
    if (["IMAGE", "VIDEO", "DOCUMENT"].includes(headerType) && !String(form.header_media_handle || "").trim()) {
      setError("Para header multimedia debes indicar header media handle.");
      return;
    }
    for (const b of Array.isArray(form.buttons) ? form.buttons : []) {
      const mode = getButtonMode(b);
      if (mode === "visit_website" && !String(b.url || "").trim()) {
        setError("Cada boton Visit website requiere URL.");
        return;
      }
      if (mode === "call_phone" && !String(b.phone_number || "").trim()) {
        setError("Cada boton Call phone number requiere numero.");
        return;
      }
    }

    setError("");
    setStatus("");
    setCreatingTemplate(true);
    try {
      const payload = {
        name,
        language: String(form.language || "es").trim().toLowerCase() || "es",
        category: String(form.category || "UTILITY").trim().toUpperCase() || "UTILITY",
        body_text: bodyText,
        header_type: headerType,
        header_text: String(form.header_text || "").trim(),
        header_media_handle: String(form.header_media_handle || "").trim(),
        footer_text: String(form.footer_text || "").trim(),
        allow_category_change: !!form.allow_category_change,
        buttons: (Array.isArray(form.buttons) ? form.buttons : [])
          .map((b) => {
            const mode = getButtonMode(b);
            const text = String(b.text || "").trim();
            if (mode === "visit_website") {
              return {
                type: "URL",
                text: text || "Visit website",
                url: String(b.url || "").trim(),
                phone_number: "",
              };
            }
            if (mode === "call_phone") {
              const cc = String(b.country_code || "").trim();
              const num = String(b.phone_number || "").trim();
              const full = num.startsWith("+") ? num : `${cc}${num}`.replace(/\s+/g, "");
              return {
                type: "PHONE_NUMBER",
                text: text || "Call phone number",
                url: "",
                phone_number: full,
              };
            }
            if (mode === "copy_offer_code") {
              const code = String(b.offer_code || "").trim();
              return {
                type: "QUICK_REPLY",
                text: text || (code ? `Copiar ${code}` : "Copy offer code"),
                url: "",
                phone_number: "",
              };
            }
            return {
              type: "QUICK_REPLY",
              text: text || "Quick reply",
              url: "",
              phone_number: "",
            };
          })
          .filter((b) => !!String(b.text || "").trim()),
      };

      const r = await fetch(`${API}/api/broadcast/meta/templates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(asErrorMessage(d));

      setStatus(`Plantilla creada en Meta: ${d?.template?.name || name}`);
      setForm((prev) => ({ ...emptyForm(), language: prev.language || "es" }));
      await loadTemplates(true);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setCreatingTemplate(false);
    }
  };

  return (
    <div className="custom-scrollbar" style={shell}>
      <div style={card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
          <div>
            <h2 style={{ margin: 0 }}>Mensajeria masiva</h2>
            <p style={{ margin: "6px 0 0", fontSize: 12, opacity: 0.82 }}>
              Modulo separado de Campanas CRM para mensajes iniciados por negocio (broadcast).
            </p>
          </div>
          <div style={{ fontSize: 12, opacity: 0.78 }}>
            Constructor estilo WhatsApp Template Manager.
          </div>
        </div>
      </div>

      <div style={{ ...card, display: "grid", gridTemplateColumns: gridCols, gap: 10 }}>
        {MODULES.map((mod, idx) => {
          const isActive = activeModule === mod.id;
          const isLive = mod.id === "message_template";
          return (
            <button
              key={mod.id}
              type="button"
              onClick={() => setActiveModule(mod.id)}
              style={{
                textAlign: "left",
                borderRadius: 10,
                border: isActive ? "1px solid rgba(46, 204, 113, 0.55)" : "1px solid rgba(255,255,255,0.14)",
                background: isActive ? "rgba(46, 204, 113, 0.12)" : "rgba(255,255,255,0.02)",
                color: "inherit",
                padding: 10,
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", marginBottom: 6 }}>
                <strong style={{ fontSize: 14 }}>{mod.title}</strong>
                <span
                  style={{
                    borderRadius: 999,
                    padding: "2px 8px",
                    fontSize: 10,
                    border: isLive ? "1px solid rgba(125,211,252,0.45)" : "1px solid rgba(255,255,255,0.18)",
                    color: isLive ? "#7dd3fc" : "#cbd5e1",
                  }}
                >
                  {isLive ? "LIVE" : `SK-${idx + 1}`}
                </span>
              </div>
              <div style={{ fontSize: 12, opacity: 0.78 }}>{mod.description}</div>
            </button>
          );
        })}
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

      {activeModule === "message_template" && menuOpen ? (
        <div
          onClick={closeMenus}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 25,
            background: "rgba(2, 6, 23, 0.42)",
            backdropFilter: "blur(2px)",
          }}
        />
      ) : null}

      {activeModule !== "message_template" ? (
        <div style={card}>
          <h3 style={{ marginTop: 0 }}>{activeModuleMeta.title}</h3>
          <p style={{ margin: "8px 0", fontSize: 13, opacity: 0.82 }}>
            Esta seccion queda en skeleton por ahora. La activamos en la siguiente fase.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: editorCols, gap: 12, alignItems: "start" }}>
          <div style={{ ...card, display: "grid", gap: 10, position: "relative", zIndex: menuOpen ? 40 : "auto" }}>
            <h3 style={{ margin: 0 }}>Message Template</h3>

            <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 8 }}>
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Template name *</div>
                <input
                  style={input}
                  placeholder="system_order_success_notification_new"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                />
              </label>
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Locale *</div>
                <select
                  style={input}
                  value={form.language}
                  onChange={(e) => setForm((prev) => ({ ...prev, language: e.target.value }))}
                >
                  {LOCALE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </label>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 8 }}>
              <div>
                <div style={{ fontSize: 12, marginBottom: 6 }}>Template category *</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {CATEGORY_OPTIONS.map((opt) => {
                    const active = form.category === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setForm((prev) => ({ ...prev, category: opt.value }))}
                        style={{
                          ...smallBtn,
                          background: active ? "rgba(99,102,241,0.3)" : "transparent",
                          borderColor: active ? "rgba(129,140,248,0.65)" : smallBtn.border,
                        }}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Header type *</div>
                <select
                  style={input}
                  value={form.header_type}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      header_type: e.target.value,
                      header_text: e.target.value === "TEXT" ? prev.header_text : "",
                    }))
                  }
                >
                  {HEADER_OPTIONS.map((opt) => (
                    <option key={opt.value || "none"} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {headerType === "TEXT" ? (
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Header text</div>
                <input
                  style={input}
                  placeholder="Titulo del mensaje"
                  value={form.header_text}
                  onChange={(e) => setForm((prev) => ({ ...prev, header_text: e.target.value }))}
                />
              </label>
            ) : null}

            {["IMAGE", "VIDEO", "DOCUMENT"].includes(headerType) ? (
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Header media handle *</div>
                <input
                  style={input}
                  placeholder="Header handle de Meta (archivo subido previamente)"
                  value={form.header_media_handle}
                  onChange={(e) => setForm((prev) => ({ ...prev, header_media_handle: e.target.value }))}
                />
              </label>
            ) : null}

            <div style={{ position: "relative" }}>
              <div style={{ fontSize: 12, marginBottom: 6 }}>Message body (1024)*</div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 6 }}>
                <button type="button" style={smallBtn} onClick={() => { setShowCustomMenu((v) => !v); setShowVarsMenu(false); }}>
                  Custom Fields
                </button>
                <button type="button" style={smallBtn} onClick={() => { setShowVarsMenu((v) => !v); setShowCustomMenu(false); }}>
                  Variables
                </button>
                <button type="button" style={smallBtn} onClick={() => insertTokenInBody("customer_name")}>
                  Name
                </button>
                <button type="button" style={smallBtn} onClick={runAiRewrite}>
                  AI Re-write
                </button>
              </div>

              {showCustomMenu ? (
                <div style={{ position: "absolute", zIndex: 55, top: 58, left: 0, width: isMobile ? "min(320px, calc(100vw - 56px))" : 300, maxHeight: 280, overflowY: "auto", ...menuCard }}>
                  {(customFields || []).map((p) => (
                    <button
                      key={`cf-${p.key}`}
                      type="button"
                      onClick={() => insertTokenInBody(p.key)}
                      style={{ ...smallBtn, width: "100%", textAlign: "left", marginBottom: 6 }}
                    >
                      {p.label || p.key}
                    </button>
                  ))}
                </div>
              ) : null}

              {showVarsMenu ? (
                <div style={{ position: "absolute", zIndex: 55, top: 58, left: isMobile ? 0 : 120, width: isMobile ? "min(340px, calc(100vw - 56px))" : 340, maxHeight: 280, overflowY: "auto", ...menuCard }}>
                  {(systemVars || []).map((p) => (
                    <button
                      key={`sv-${p.key}`}
                      type="button"
                      onClick={() => insertTokenInBody(p.key)}
                      style={{ ...smallBtn, width: "100%", textAlign: "left", marginBottom: 6 }}
                    >
                      {p.key}
                    </button>
                  ))}
                </div>
              ) : null}

              <textarea
                ref={bodyRef}
                className="custom-scrollbar"
                style={{ ...input, minHeight: 150, resize: "vertical" }}
                placeholder="Hello, {{customer_name}}, ..."
                maxLength={1024}
                value={form.body_text}
                onChange={(e) => setForm((prev) => ({ ...prev, body_text: e.target.value }))}
              />
              <div style={{ textAlign: "right", fontSize: 11, opacity: 0.7, marginTop: 4 }}>
                Characters: {bodyChars} / 1024
              </div>
            </div>

            <label>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Footer text</div>
              <input
                style={input}
                placeholder="Atentamente, Equipo Verane"
                value={form.footer_text}
                onChange={(e) => setForm((prev) => ({ ...prev, footer_text: e.target.value }))}
              />
            </label>

            <div style={{ position: "relative" }}>
              <button
                type="button"
                style={smallBtn}
                onClick={() => {
                  setShowAddButtonMenu((v) => !v);
                  setShowCustomMenu(false);
                  setShowVarsMenu(false);
                }}
              >
                + Add button
              </button>
              {showAddButtonMenu ? (
                <div style={{ position: "absolute", zIndex: 55, bottom: 44, left: 0, width: isMobile ? "min(340px, calc(100vw - 56px))" : 360, ...menuCard }}>
                  {BUTTON_PRESET_OPTIONS.map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      style={{ ...smallBtn, width: "100%", textAlign: "left", marginBottom: 6 }}
                      onClick={() => addButtonByPreset(opt.id)}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                        <span>{opt.label}</span>
                        <span style={{ opacity: 0.7, fontSize: 11 }}>{opt.hint}</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : null}
            </div>

            <div style={{ ...card, background: "rgba(255,255,255,0.03)" }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Quick Reply - Optional</div>
              {quickReplyRows.length === 0 ? (
                <div style={{ fontSize: 12, opacity: 0.72 }}>No hay botones quick reply configurados.</div>
              ) : null}
              <div style={{ display: "grid", gap: 8 }}>
                {quickReplyRows.map((btn) => (
                  <div key={`qr-${btn._idx}`} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: 8 }}>
                    <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "160px 1fr auto", gap: 8 }}>
                      <div>
                        <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Type</div>
                        <select
                          style={input}
                          value={btn.subtype || "CUSTOM"}
                          onChange={(e) => updateButton(btn._idx, { subtype: e.target.value })}
                        >
                          <option value="CUSTOM">Custom</option>
                        </select>
                      </div>
                      <div>
                        <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Button Text</div>
                        <input
                          style={input}
                          placeholder="Quick Reply"
                          value={btn.text || ""}
                          onChange={(e) => updateButton(btn._idx, { text: e.target.value })}
                        />
                      </div>
                      <button type="button" style={dangerBtn} onClick={() => removeButton(btn._idx)}>X</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ ...card, background: "rgba(255,255,255,0.03)" }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Call to Action - Optional</div>
              {ctaRows.length === 0 ? (
                <div style={{ fontSize: 12, opacity: 0.72 }}>No hay botones call to action configurados.</div>
              ) : null}
              <div style={{ display: "grid", gap: 8 }}>
                {ctaRows.map((btn) => {
                  const mode = btn._mode;
                  return (
                    <div key={`cta-${btn._idx}`} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: 8 }}>
                      {mode === "visit_website" ? (
                        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "180px 1fr 140px 1fr auto", gap: 8 }}>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Type of Action</div>
                            <select style={input} value={mode} onChange={(e) => setButtonMode(btn._idx, e.target.value)}>
                              <option value="visit_website">Visit website</option>
                              <option value="call_phone">Call phone number</option>
                              <option value="copy_offer_code">Copy offer code</option>
                            </select>
                          </div>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Button Text</div>
                            <input style={input} placeholder="Visit website" value={btn.text || ""} onChange={(e) => updateButton(btn._idx, { text: e.target.value })} />
                          </div>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>URL Type</div>
                            <select style={input} value={btn.url_type || "STATIC"} onChange={(e) => updateButton(btn._idx, { url_type: e.target.value })}>
                              <option value="STATIC">Static</option>
                            </select>
                          </div>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Website URL</div>
                            <input style={input} placeholder="https://..." value={btn.url || ""} onChange={(e) => updateButton(btn._idx, { url: e.target.value })} />
                          </div>
                          <button type="button" style={dangerBtn} onClick={() => removeButton(btn._idx)}>X</button>
                        </div>
                      ) : null}

                      {mode === "call_phone" ? (
                        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "180px 1fr 1fr 1fr auto", gap: 8 }}>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Type of Action</div>
                            <select style={input} value={mode} onChange={(e) => setButtonMode(btn._idx, e.target.value)}>
                              <option value="call_phone">Call phone number</option>
                              <option value="visit_website">Visit website</option>
                              <option value="copy_offer_code">Copy offer code</option>
                            </select>
                          </div>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Button Text</div>
                            <input style={input} placeholder="Call Phone Number" value={btn.text || ""} onChange={(e) => updateButton(btn._idx, { text: e.target.value })} />
                          </div>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Country</div>
                            <select style={input} value={btn.country_code || "+57"} onChange={(e) => updateButton(btn._idx, { country_code: e.target.value })}>
                              {COUNTRY_OPTIONS.map((opt) => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Phone Number</div>
                            <input style={input} placeholder="3237028445" value={btn.phone_number || ""} onChange={(e) => updateButton(btn._idx, { phone_number: e.target.value })} />
                          </div>
                          <button type="button" style={dangerBtn} onClick={() => removeButton(btn._idx)}>X</button>
                        </div>
                      ) : null}

                      {mode === "copy_offer_code" ? (
                        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "180px 1fr 1fr auto", gap: 8 }}>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Type of Action</div>
                            <select style={input} value={mode} onChange={(e) => setButtonMode(btn._idx, e.target.value)}>
                              <option value="copy_offer_code">Copy offer code</option>
                              <option value="visit_website">Visit website</option>
                              <option value="call_phone">Call phone number</option>
                            </select>
                          </div>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Button Text</div>
                            <input style={input} placeholder="Copy Offer Code" value={btn.text || ""} onChange={(e) => updateButton(btn._idx, { text: e.target.value })} />
                          </div>
                          <div>
                            <div style={{ fontSize: 12, marginBottom: 4, opacity: 0.8 }}>Offer Code</div>
                            <input style={input} placeholder="Enter sample" value={btn.offer_code || ""} onChange={(e) => updateButton(btn._idx, { offer_code: e.target.value })} />
                          </div>
                          <button type="button" style={dangerBtn} onClick={() => removeButton(btn._idx)}>X</button>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
              <input
                type="checkbox"
                checked={!!form.allow_category_change}
                onChange={(e) => setForm((prev) => ({ ...prev, allow_category_change: e.target.checked }))}
              />
              Permitir ajuste de categoria por Meta
            </label>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                style={primaryBtn}
                onClick={createMetaTemplate}
                disabled={creatingTemplate}
              >
                {creatingTemplate ? "Creando..." : "Crear plantilla en Meta"}
              </button>
              <button type="button" style={smallBtn} onClick={() => setForm(emptyForm())}>
                Limpiar
              </button>
            </div>
          </div>

          <div style={{ display: "grid", gap: 12 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Vista previa</h3>
              <div
                style={{
                  margin: "0 auto",
                  width: "100%",
                  maxWidth: 300,
                  borderRadius: 28,
                  border: "3px solid #1f2937",
                  background: "#0b1217",
                  padding: 10,
                  boxShadow: "0 14px 30px rgba(0,0,0,0.35)",
                }}
              >
                <div style={{ borderRadius: 20, background: "linear-gradient(180deg, #0f766e, #0b5f56)", padding: "8px 10px", fontSize: 12 }}>
                  <strong>Business</strong>
                </div>
                <div style={{ padding: 10, minHeight: 260, background: "rgba(255,255,255,0.06)", borderBottomLeftRadius: 18, borderBottomRightRadius: 18 }}>
                  <div style={{ background: "#d9fdd3", color: "#122013", borderRadius: 10, padding: 10, whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.35 }}>
                    {headerType === "TEXT" && String(form.header_text || "").trim() ? (
                      <div style={{ fontWeight: 700, marginBottom: 6 }}>{renderWithTokens(form.header_text, TOKEN_EXAMPLES)}</div>
                    ) : null}
                    {["IMAGE", "VIDEO", "DOCUMENT"].includes(headerType) ? (
                      <div style={{ marginBottom: 6, fontWeight: 700 }}>
                        [{headerType}] {form.header_media_handle ? "header handle configurado" : "header handle pendiente"}
                      </div>
                    ) : null}
                    {previewBody || "[Escribe el body de la plantilla]"}
                    {previewFooter ? (
                      <div style={{ marginTop: 10, opacity: 0.78, borderTop: "1px solid rgba(0,0,0,0.12)", paddingTop: 6 }}>
                        {previewFooter}
                      </div>
                    ) : null}
                    {(form.buttons || []).length ? (
                      <div style={{ marginTop: 10, display: "grid", gap: 5 }}>
                        {(form.buttons || []).map((b, idx) => (
                          <div key={`pv-btn-${idx}`} style={{ border: "1px solid rgba(0,0,0,0.18)", borderRadius: 8, padding: "5px 8px", fontSize: 12 }}>
                            {b.text || `Boton ${idx + 1}`}
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ ...card, minHeight: 320, display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <h3 style={{ margin: 0 }}>Plantillas de Meta</h3>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button type="button" style={smallBtn} onClick={() => loadTemplates(false)} disabled={loadingTemplates}>
                    Recargar
                  </button>
                  <button type="button" style={primaryBtn} onClick={() => loadTemplates(true)} disabled={loadingTemplates}>
                    {loadingTemplates ? "Sincronizando..." : "Sincronizar"}
                  </button>
                </div>
              </div>
              <div style={{ fontSize: 12, opacity: 0.76 }}>Total: {templates.length} plantilla(s).</div>

              <div className="custom-scrollbar" style={{ flex: 1, minHeight: 0, overflowY: "auto", display: "grid", gap: 8, paddingRight: 2 }}>
                {templates.length === 0 ? (
                  <div style={{ ...card, opacity: 0.72 }}>No hay plantillas cargadas aun.</div>
                ) : (
                  templates.map((tpl, idx) => (
                    <div key={`${tpl.id || tpl.name || "tpl"}-${idx}`} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
                        <strong style={{ fontSize: 14 }}>{tpl.name || "(sin nombre)"}</strong>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          <span style={{ border: "1px solid rgba(255,255,255,0.16)", borderRadius: 999, padding: "2px 8px", fontSize: 10, color: statusColor(tpl.status) }}>
                            {String(tpl.status || "pending").toUpperCase()}
                          </span>
                          <span style={{ border: "1px solid rgba(255,255,255,0.16)", borderRadius: 999, padding: "2px 8px", fontSize: 10, color: categoryColor(tpl.category) }}>
                            {String(tpl.category || "-").toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 4 }}>
                        ID: {tpl.id || "-"} | idioma: {tpl.language || "-"} | calidad: {tpl.quality_score || "-"}
                      </div>
                      <div style={{ fontSize: 12, opacity: 0.88, whiteSpace: "pre-wrap" }}>
                        {String(tpl.body_text || "").trim() || "[Sin body detectado]"}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
