import React, { useEffect, useMemo, useState } from "react";

const panel = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 14,
  background: "rgba(255,255,255,0.02)",
  padding: 12,
};

const input = {
  width: "100%",
  padding: "9px 10px",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "transparent",
  color: "inherit",
};

const btn = {
  padding: "8px 12px",
  borderRadius: 9,
  border: "1px solid rgba(255,255,255,0.16)",
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
};

const dangerBtn = {
  ...btn,
  border: "1px solid rgba(255,120,120,0.55)",
  color: "#ffb7b7",
};

const ICON_OPTIONS = ["🏷️", "⭐", "🛒", "💰", "📞", "📌", "🔥", "✅", "⏳", "💬", "🎁", "📦"];

function emptyForm() {
  return {
    id: null,
    name: "",
    label_key: "",
    color: "#64748b",
    icon: "🏷️",
    description: "",
    is_active: true,
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

export default function LabelsPanel({ apiBase }) {
  const API = (apiBase || "").replace(/\/$/, "");

  const [labels, setLabels] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);

  const filtered = useMemo(() => {
    const q = String(search || "").trim().toLowerCase();
    if (!q) return labels;
    return (labels || []).filter((l) => {
      const hay = `${l.name || ""} ${l.label_key || ""} ${l.description || ""}`.toLowerCase();
      return hay.includes(q);
    });
  }, [labels, search]);

  const loadLabels = async () => {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/api/labels?active=all&limit=1000`);
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudieron cargar etiquetas");
      setLabels(Array.isArray(d?.labels) ? d.labels : []);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLabels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openNew = () => {
    setForm(emptyForm());
    setShowModal(true);
  };

  const openEdit = (label) => {
    setForm({
      id: label.id,
      name: label.name || "",
      label_key: label.label_key || "",
      color: label.color || "#64748b",
      icon: label.icon || "🏷️",
      description: label.description || "",
      is_active: !!label.is_active,
    });
    setShowModal(true);
  };

  const saveLabel = async () => {
    setSaving(true);
    setError("");
    setStatus("");
    try {
      const payload = {
        name: String(form.name || "").trim(),
        label_key: String(form.label_key || "").trim(),
        color: String(form.color || "").trim(),
        icon: String(form.icon || "").trim() || "🏷️",
        description: String(form.description || "").trim(),
        is_active: !!form.is_active,
      };
      if (!payload.name) throw new Error("Nombre requerido");

      const isUpdate = !!form.id;
      const url = isUpdate ? `${API}/api/labels/${encodeURIComponent(form.id)}` : `${API}/api/labels`;
      const method = isUpdate ? "PATCH" : "POST";

      const r = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo guardar etiqueta");

      setShowModal(false);
      setStatus(isUpdate ? "Etiqueta actualizada" : "Etiqueta creada");
      await loadLabels();
      setTimeout(() => setStatus(""), 2200);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSaving(false);
    }
  };

  const removeLabel = async (label) => {
    const cleanup = window.confirm(
      `Vas a eliminar "${label.name}".\n\nAceptar: tambien limpiar esta etiqueta de todos los clientes.\nCancelar: eliminar solo del catalogo.`
    );
    const second = window.confirm(
      cleanup
        ? `Confirma eliminar "${label.name}" y limpiar etiquetas de clientes.`
        : `Confirma eliminar "${label.name}" del catalogo (sin limpiar clientes).`
    );
    if (!second) return;
    setError("");
    try {
      const r = await fetch(
        `${API}/api/labels/${encodeURIComponent(label.id)}?cleanup_tags=${cleanup ? "true" : "false"}`,
        { method: "DELETE" }
      );
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo eliminar etiqueta");
      setStatus(
        cleanup
          ? `Etiqueta eliminada y limpiada en ${d?.conversations_cleaned || 0} clientes`
          : "Etiqueta eliminada"
      );
      await loadLabels();
      setTimeout(() => setStatus(""), 2400);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  return (
    <div className="placeholder-view" style={{ alignItems: "stretch", padding: 12 }}>
      <div style={{ ...panel, width: "100%", minHeight: 620, display: "grid", gap: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <h2 style={{ margin: 0 }}>Etiquetas</h2>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={btn} onClick={loadLabels}>Recargar</button>
            <button style={{ ...btn, borderColor: "rgba(46,204,113,0.4)" }} onClick={openNew}>Nueva etiqueta</button>
          </div>
        </div>

        <div style={{ ...panel, padding: 10, display: "flex", gap: 8, alignItems: "center" }}>
          <input
            style={input}
            placeholder="Buscar por nombre, key o descripcion..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <span style={{ fontSize: 12, opacity: 0.8, minWidth: 90, textAlign: "right" }}>{filtered.length} etiquetas</span>
        </div>

        {error ? <div style={{ color: "#ff8080" }}>{error}</div> : null}
        {status ? <div style={{ color: "#9be15d" }}>{status}</div> : null}

        <div style={{ ...panel, padding: 0, overflow: "hidden", minHeight: 430 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "46px 1.2fr 0.7fr 0.6fr 0.6fr 1fr 180px",
              gap: 8,
              padding: "10px 12px",
              fontSize: 12,
              fontWeight: 700,
              borderBottom: "1px solid rgba(255,255,255,0.12)",
              opacity: 0.85,
            }}
          >
            <div>Icono</div>
            <div>Nombre</div>
            <div>Key</div>
            <div>Color</div>
            <div>Uso</div>
            <div>Descripcion</div>
            <div>Acciones</div>
          </div>

          <div style={{ maxHeight: 460, overflow: "auto" }}>
            {loading ? <div style={{ padding: 12, opacity: 0.8 }}>Cargando...</div> : null}
            {!loading && filtered.length === 0 ? <div style={{ padding: 12, opacity: 0.8 }}>No hay etiquetas.</div> : null}
            {filtered.map((label) => (
              <div
                key={label.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "46px 1.2fr 0.7fr 0.6fr 0.6fr 1fr 180px",
                  gap: 8,
                  alignItems: "center",
                  padding: "10px 12px",
                  borderBottom: "1px solid rgba(255,255,255,0.07)",
                  background: label.is_active ? "transparent" : "rgba(255,255,255,0.03)",
                }}
              >
                <div style={{ fontSize: 18 }}>{label.icon || "🏷️"}</div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {label.name || "-"}
                  </div>
                  <div style={{ fontSize: 11, opacity: 0.65 }}>
                    {label.is_active ? "Activa" : "Inactiva"} • {fmtDate(label.updated_at)}
                  </div>
                </div>
                <div style={{ fontSize: 12, opacity: 0.9 }}>{label.label_key || "-"}</div>
                <div>
                  <span
                    style={{
                      display: "inline-block",
                      width: 24,
                      height: 24,
                      borderRadius: 6,
                      border: "1px solid rgba(255,255,255,0.25)",
                      background: label.color || "#64748b",
                    }}
                    title={label.color || "#64748b"}
                  />
                </div>
                <div>{Number(label.usage_count || 0)}</div>
                <div style={{ fontSize: 12, opacity: 0.82, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {label.description || "-"}
                </div>
                <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                  <button style={btn} onClick={() => openEdit(label)}>Editar</button>
                  <button style={dangerBtn} onClick={() => removeLabel(label)}>Borrar</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showModal ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.55)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16,
            zIndex: 1200,
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{
              width: "min(680px, 100%)",
              borderRadius: 14,
              border: "1px solid rgba(255,255,255,0.18)",
              background: "#0b1217",
              overflow: "hidden",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ padding: "12px 14px", borderBottom: "1px solid rgba(255,255,255,0.12)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0 }}>{form.id ? "Editar etiqueta" : "Nueva etiqueta"}</h3>
              <button style={btn} onClick={() => setShowModal(false)}>X</button>
            </div>
            <div style={{ padding: 14, display: "grid", gap: 10 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: 10 }}>
                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Nombre</div>
                  <input style={input} value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} />
                </label>
                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Key interna (opcional)</div>
                  <input style={input} value={form.label_key} onChange={(e) => setForm((p) => ({ ...p, label_key: e.target.value }))} placeholder="ej: pago_pendiente" />
                </label>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 10 }}>
                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Color</div>
                  <input style={{ ...input, padding: 0, height: 40 }} type="color" value={form.color} onChange={(e) => setForm((p) => ({ ...p, color: e.target.value }))} />
                </label>
                <div>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Icono</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {ICON_OPTIONS.map((icon) => (
                      <button
                        key={icon}
                        type="button"
                        style={{
                          ...btn,
                          width: 36,
                          height: 36,
                          padding: 0,
                          borderColor: form.icon === icon ? "rgba(46,204,113,0.7)" : btn.border,
                          background: form.icon === icon ? "rgba(46,204,113,0.12)" : "transparent",
                        }}
                        onClick={() => setForm((p) => ({ ...p, icon }))}
                      >
                        {icon}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <label>
                <div style={{ fontSize: 12, marginBottom: 4 }}>Descripcion</div>
                <textarea
                  style={{ ...input, minHeight: 80, resize: "vertical" }}
                  value={form.description}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                />
              </label>

              <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" checked={!!form.is_active} onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))} />
                Etiqueta activa
              </label>

              <div style={{ ...panel, display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "6px 10px",
                    borderRadius: 999,
                    background: `${form.color}22`,
                    border: `1px solid ${form.color}`,
                    color: "#fff",
                  }}
                >
                  <span>{form.icon || "🏷️"}</span>
                  <span>{form.name || "Preview etiqueta"}</span>
                </span>
              </div>
            </div>
            <div style={{ padding: "12px 14px", borderTop: "1px solid rgba(255,255,255,0.12)", display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button style={btn} onClick={() => setShowModal(false)}>Cancelar</button>
              <button style={{ ...btn, borderColor: "rgba(46,204,113,0.7)" }} onClick={saveLabel} disabled={saving}>
                {saving ? "Guardando..." : "Guardar"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

