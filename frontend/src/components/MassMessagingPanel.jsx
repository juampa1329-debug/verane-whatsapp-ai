import React, { useEffect, useMemo, useState } from "react";
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

const MODULES = [
  {
    id: "ai_agent",
    title: "AI Agent",
    description: "Skeleton: reglas IA para outbound y copys automaticos.",
  },
  {
    id: "broadcast_campaign",
    title: "Broadcast Campaign",
    description: "Skeleton: campanas de envio masivo (inicio por negocio).",
  },
  {
    id: "chat_widget",
    title: "Chat Widget",
    description: "Skeleton: widget embebido para captura y conversion.",
  },
  {
    id: "sequence",
    title: "Secuencia",
    description: "Skeleton: secuencias de seguimiento por pasos y tiempos.",
  },
  {
    id: "input_flow",
    title: "Input Flow",
    description: "Skeleton: formularios/flows para calificar leads.",
  },
  {
    id: "whatsapp_flows",
    title: "WhatsApp Flows",
    description: "Skeleton: integracion con flows interactivos de WhatsApp.",
  },
  {
    id: "message_template",
    title: "Message Template",
    description: "Activo: plantillas oficiales de Meta para mensajes marketing.",
  },
  {
    id: "wc_shopify_automation",
    title: "WC/Shopify Automation",
    description: "Skeleton: automatizaciones ecommerce (carrito, recompra, etc.).",
  },
  {
    id: "outbound_webhook",
    title: "Out-bound Webhook",
    description: "Skeleton: webhooks de salida para integraciones externas.",
  },
  {
    id: "action_buttons",
    title: "Action Buttons",
    description: "Skeleton: botones CTA de conversion y respuesta rapida.",
  },
  {
    id: "configuration",
    title: "Configuracion",
    description: "Skeleton: ajustes globales de mensajeria masiva.",
  },
];

function emptyButton() {
  return { type: "QUICK_REPLY", text: "", url: "", phone_number: "" };
}

function emptyForm() {
  return {
    name: "",
    language: "es",
    category: "MARKETING",
    body_text: "",
    header_type: "",
    header_text: "",
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
  const [activeModule, setActiveModule] = useState("message_template");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [creatingTemplate, setCreatingTemplate] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState(emptyForm);

  const gridCols = isMobile ? "1fr" : isTablet ? "repeat(2, minmax(0, 1fr))" : "repeat(3, minmax(0, 1fr))";
  const editorCols = isMobile ? "1fr" : "minmax(360px, 420px) 1fr";

  const activeModuleMeta = useMemo(() => {
    return MODULES.find((m) => m.id === activeModule) || MODULES[0];
  }, [activeModule]);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addButton = () => {
    setForm((prev) => {
      const nextButtons = Array.isArray(prev.buttons) ? [...prev.buttons] : [];
      if (nextButtons.length >= 3) return prev;
      nextButtons.push(emptyButton());
      return { ...prev, buttons: nextButtons };
    });
  };

  const removeButton = (idx) => {
    setForm((prev) => ({
      ...prev,
      buttons: (Array.isArray(prev.buttons) ? prev.buttons : []).filter((_, i) => i !== idx),
    }));
  };

  const updateButton = (idx, patch) => {
    setForm((prev) => ({
      ...prev,
      buttons: (Array.isArray(prev.buttons) ? prev.buttons : []).map((b, i) =>
        i === idx ? { ...b, ...patch } : b
      ),
    }));
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

    setError("");
    setStatus("");
    setCreatingTemplate(true);
    try {
      const payload = {
        name,
        language: String(form.language || "es").trim().toLowerCase() || "es",
        category: String(form.category || "MARKETING").trim().toUpperCase() || "MARKETING",
        body_text: bodyText,
        header_type: String(form.header_type || "").trim().toUpperCase(),
        header_text: String(form.header_text || "").trim(),
        footer_text: String(form.footer_text || "").trim(),
        allow_category_change: !!form.allow_category_change,
        buttons: (Array.isArray(form.buttons) ? form.buttons : [])
          .map((b) => ({
            type: String(b.type || "QUICK_REPLY").trim().toUpperCase(),
            text: String(b.text || "").trim(),
            url: String(b.url || "").trim(),
            phone_number: String(b.phone_number || "").trim(),
          }))
          .filter((b) => !!b.text),
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
              Modulo separado de Campanas CRM. Aqui se gestionan mensajes iniciados por negocio (broadcast).
            </p>
            <p style={{ margin: "4px 0 0", fontSize: 12, opacity: 0.7 }}>
              Nota: las plantillas CRM existentes siguen siendo para respuestas rapidas de IA en inbox.
            </p>
          </div>
          <div style={{ fontSize: 12, opacity: 0.78 }}>
            Punto 11: skeleton aprobado (excepto Message Template activo).
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
                    border: isLive
                      ? "1px solid rgba(125,211,252,0.45)"
                      : "1px solid rgba(255,255,255,0.18)",
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

      {activeModule !== "message_template" ? (
        <div style={card}>
          <h3 style={{ marginTop: 0 }}>{activeModuleMeta.title}</h3>
          <p style={{ margin: "8px 0", fontSize: 13, opacity: 0.82 }}>
            Esta seccion queda en skeleton por ahora, tal como aprobaste. En la siguiente fase la activamos modulo por modulo.
          </p>
          <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 12, opacity: 0.74, lineHeight: 1.5 }}>
            <li>Estructura UI creada para pruebas de flujo.</li>
            <li>Sin logica de ejecucion ni endpoints acoplados aun.</li>
            <li>Lista para implementar reglas, jobs y auditoria.</li>
          </ul>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: editorCols, gap: 12, alignItems: "start" }}>
          <div style={{ ...card, display: "grid", gap: 10 }}>
            <h3 style={{ margin: 0 }}>Message Template (Meta WhatsApp Manager)</h3>
            <p style={{ margin: "0 0 4px", fontSize: 12, opacity: 0.78 }}>
              Estas plantillas son las oficiales que Meta revisa para mensajes iniciados por negocio.
            </p>

            <label>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Nombre interno</div>
              <input
                style={input}
                placeholder="ej: pago_pendiente_recordatorio_1"
                value={form.name}
                onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              />
            </label>

            <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 8 }}>
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Idioma</div>
                <input
                  style={input}
                  placeholder="es"
                  value={form.language}
                  onChange={(e) => setForm((prev) => ({ ...prev, language: e.target.value }))}
                />
              </label>
              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Categoria</div>
                <select
                  style={input}
                  value={form.category}
                  onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}
                >
                  <option value="MARKETING">MARKETING</option>
                  <option value="UTILITY">UTILITY</option>
                  <option value="AUTHENTICATION">AUTHENTICATION</option>
                </select>
              </label>
            </div>

            <label>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Header</div>
              <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "140px 1fr", gap: 8 }}>
                <select
                  style={input}
                  value={form.header_type}
                  onChange={(e) => setForm((prev) => ({ ...prev, header_type: e.target.value }))}
                >
                  <option value="">Sin header</option>
                  <option value="TEXT">TEXT</option>
                </select>
                <input
                  style={input}
                  placeholder="Texto del header"
                  value={form.header_text}
                  onChange={(e) => setForm((prev) => ({ ...prev, header_text: e.target.value }))}
                  disabled={String(form.header_type || "").toUpperCase() !== "TEXT"}
                />
              </div>
            </label>

            <label>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Body</div>
              <textarea
                style={{ ...input, minHeight: 110, resize: "vertical" }}
                placeholder="Hola {{1}}, recuerda tu pago pendiente..."
                value={form.body_text}
                onChange={(e) => setForm((prev) => ({ ...prev, body_text: e.target.value }))}
              />
            </label>

            <label>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Footer (opcional)</div>
              <input
                style={input}
                placeholder="Ejemplo: Verane Perfumeria"
                value={form.footer_text}
                onChange={(e) => setForm((prev) => ({ ...prev, footer_text: e.target.value }))}
              />
            </label>

            <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                <strong style={{ fontSize: 13 }}>Botones (max 3)</strong>
                <button type="button" style={smallBtn} onClick={addButton} disabled={(form.buttons || []).length >= 3}>
                  + Boton
                </button>
              </div>
              <div style={{ marginTop: 8, display: "grid", gap: 8 }}>
                {(form.buttons || []).map((btn, idx) => {
                  const btnType = String(btn.type || "QUICK_REPLY").toUpperCase();
                  return (
                    <div key={`btn-${idx}`} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: 8 }}>
                      <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 8, marginBottom: 8 }}>
                        <select
                          style={input}
                          value={btnType}
                          onChange={(e) => updateButton(idx, { type: e.target.value })}
                        >
                          <option value="QUICK_REPLY">QUICK_REPLY</option>
                          <option value="URL">URL</option>
                          <option value="PHONE_NUMBER">PHONE_NUMBER</option>
                        </select>
                        <input
                          style={input}
                          placeholder="Texto del boton"
                          value={btn.text || ""}
                          onChange={(e) => updateButton(idx, { text: e.target.value })}
                        />
                      </div>

                      {btnType === "URL" ? (
                        <input
                          style={input}
                          placeholder="https://..."
                          value={btn.url || ""}
                          onChange={(e) => updateButton(idx, { url: e.target.value })}
                        />
                      ) : null}
                      {btnType === "PHONE_NUMBER" ? (
                        <input
                          style={input}
                          placeholder="+573001112233"
                          value={btn.phone_number || ""}
                          onChange={(e) => updateButton(idx, { phone_number: e.target.value })}
                        />
                      ) : null}

                      <div style={{ marginTop: 8 }}>
                        <button type="button" style={dangerBtn} onClick={() => removeButton(idx)}>
                          Quitar boton
                        </button>
                      </div>
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
              <button
                type="button"
                style={smallBtn}
                onClick={() => setForm(emptyForm())}
                disabled={creatingTemplate}
              >
                Limpiar
              </button>
            </div>
          </div>

          <div style={{ ...card, minHeight: 360, display: "flex", flexDirection: "column", gap: 10 }}>
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
            <div style={{ fontSize: 12, opacity: 0.76 }}>
              Total: {templates.length} plantilla(s).
            </div>

            <div className="custom-scrollbar" style={{ flex: 1, minHeight: 0, overflowY: "auto", display: "grid", gap: 8, paddingRight: 2 }}>
              {templates.length === 0 ? (
                <div style={{ ...card, opacity: 0.72 }}>
                  No hay plantillas cargadas aun.
                </div>
              ) : (
                templates.map((tpl, idx) => (
                  <div key={`${tpl.id || tpl.name || "tpl"}-${idx}`} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
                      <strong style={{ fontSize: 14 }}>{tpl.name || "(sin nombre)"}</strong>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <span
                          style={{
                            border: "1px solid rgba(255,255,255,0.16)",
                            borderRadius: 999,
                            padding: "2px 8px",
                            fontSize: 10,
                            color: statusColor(tpl.status),
                          }}
                        >
                          {String(tpl.status || "pending").toUpperCase()}
                        </span>
                        <span
                          style={{
                            border: "1px solid rgba(255,255,255,0.16)",
                            borderRadius: 999,
                            padding: "2px 8px",
                            fontSize: 10,
                            color: categoryColor(tpl.category),
                          }}
                        >
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
      )}
    </div>
  );
}
