import React, { useEffect, useMemo, useState } from "react";

const panelStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  background: "rgba(255,255,255,0.02)",
};

const inputStyle = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "transparent",
  color: "inherit",
};

const editableFields = [
  "first_name",
  "last_name",
  "city",
  "customer_type",
  "interests",
  "tags",
  "notes",
  "payment_status",
  "payment_reference",
];

function fullName(c) {
  const n = `${c?.first_name || ""} ${c?.last_name || ""}`.trim();
  return n || c?.phone || "";
}

function stageFromEnrollment(enrollment) {
  if (!enrollment) return "";
  const st = String(enrollment.state || "").toLowerCase();
  if (st === "hold") return "hold";
  if (st === "completed") return "done";
  if (st === "exited") return "clear";
  const step = Number(enrollment.current_step_order || 0);
  if (Number.isFinite(step) && step > 0) return `s${step}`;
  return "";
}

function defaultStageName(stepOrder) {
  const n = Number(stepOrder || 0);
  if (n === 1) return "Primer contacto";
  if (n === 2) return "Seguimiento intensivo";
  if (n === 3) return "Cierre fuerte";
  return `Etapa ${n || 1}`;
}

export default function CustomersPanel({ apiBase }) {
  const API = (apiBase || "").replace(/\/$/, "");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [q, setQ] = useState("");
  const [customers, setCustomers] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState("");
  const [form, setForm] = useState({});
  const [rmkCatalog, setRmkCatalog] = useState([]);
  const [rmkEnrollments, setRmkEnrollments] = useState([]);
  const [rmkFlowId, setRmkFlowId] = useState("");
  const [rmkStage, setRmkStage] = useState("");
  const [rmkSaving, setRmkSaving] = useState(false);
  const [rmkSendNow, setRmkSendNow] = useState(true);

  const selected = useMemo(
    () => customers.find((c) => c.phone === selectedPhone) || null,
    [customers, selectedPhone]
  );

  const selectedRmkFlow = useMemo(
    () => (rmkCatalog || []).find((f) => String(f.id) === String(rmkFlowId)) || null,
    [rmkCatalog, rmkFlowId]
  );

  const selectedEnrollment = useMemo(
    () => (rmkEnrollments || []).find((e) => String(e.flow_id) === String(rmkFlowId)) || null,
    [rmkEnrollments, rmkFlowId]
  );

  const stageOptions = useMemo(() => {
    const steps = Array.isArray(selectedRmkFlow?.steps) ? selectedRmkFlow.steps : [];
    const byOrder = [...steps].sort((a, b) => Number(a.step_order || 0) - Number(b.step_order || 0));
    const opts = byOrder.map((s) => ({
      value: `s${Number(s.step_order || 1)}`,
      label: `${String(s.stage_name || "").trim() || defaultStageName(s.step_order)}${s.template_name ? ` - ${s.template_name}` : ""}`,
    }));
    opts.push({ value: "hold", label: "Pausar (hold)" });
    opts.push({ value: "done", label: "Finalizar (done)" });
    opts.push({ value: "clear", label: "Quitar del flow" });
    return opts;
  }, [selectedRmkFlow]);

  const loadCustomers = async () => {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/api/customers?search=${encodeURIComponent(q)}&page_size=50`);
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudieron cargar clientes");
      const rows = Array.isArray(data?.customers) ? data.customers : [];
      setCustomers(rows);
      if (!selectedPhone && rows.length) {
        setSelectedPhone(rows[0].phone);
      } else if (selectedPhone && !rows.some((x) => x.phone === selectedPhone)) {
        setSelectedPhone(rows[0]?.phone || "");
      }
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  };

  const loadCustomerDetail = async (phone) => {
    if (!phone) return;
    try {
      const r = await fetch(`${API}/api/customers/${encodeURIComponent(phone)}`);
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudo cargar detalle");
      const c = data?.customer || {};
      const next = {};
      editableFields.forEach((k) => {
        next[k] = c?.[k] || "";
      });
      setForm(next);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const loadRemarketingCatalog = async () => {
    try {
      const r = await fetch(`${API}/api/remarketing/stages/catalog`);
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo cargar catalogo de remarketing");
      const flows = Array.isArray(d?.flows) ? d.flows : [];
      setRmkCatalog(flows);
      if (!rmkFlowId && flows[0]?.id) {
        setRmkFlowId(String(flows[0].id));
      }
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const loadRemarketingForPhone = async (phone) => {
    if (!phone) {
      setRmkEnrollments([]);
      return;
    }
    try {
      const r = await fetch(`${API}/api/remarketing/contacts/${encodeURIComponent(phone)}`);
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo cargar estado de remarketing");
      const enrollments = Array.isArray(d?.enrollments) ? d.enrollments : [];
      setRmkEnrollments(enrollments);

      const currentFlow = enrollments[0]?.flow_id ? String(enrollments[0].flow_id) : "";
      if (currentFlow) {
        setRmkFlowId(currentFlow);
      } else if (!rmkFlowId && rmkCatalog[0]?.id) {
        setRmkFlowId(String(rmkCatalog[0].id));
      }
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const applyRemarketingStage = async () => {
    if (!selectedPhone || !rmkFlowId || !rmkStage) return;
    setRmkSaving(true);
    setError("");
    setStatus("");
    try {
      const r = await fetch(`${API}/api/remarketing/stage/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: selectedPhone,
          flow_id: Number(rmkFlowId),
          stage: rmkStage,
          send_now: !!rmkSendNow,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo asignar etapa");
      setStatus("Etapa de remarketing actualizada");
      await Promise.all([
        loadRemarketingForPhone(selectedPhone),
        loadCustomerDetail(selectedPhone),
        loadCustomers(),
      ]);
      setTimeout(() => setStatus(""), 2600);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setRmkSaving(false);
    }
  };

  const saveCustomer = async () => {
    if (!selectedPhone) return;
    setSaving(true);
    setStatus("");
    setError("");
    try {
      const payload = {};
      editableFields.forEach((k) => {
        payload[k] = form?.[k] || "";
      });

      const r = await fetch(`${API}/api/customers/${encodeURIComponent(selectedPhone)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "No se pudo guardar");
      setStatus("Cliente guardado");
      await loadCustomers();
      await loadCustomerDetail(selectedPhone);
      setTimeout(() => setStatus(""), 2400);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    loadCustomers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadRemarketingCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      loadCustomers();
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  useEffect(() => {
    if (selectedPhone) {
      loadCustomerDetail(selectedPhone);
      loadRemarketingForPhone(selectedPhone);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPhone]);

  useEffect(() => {
    if (selectedEnrollment) {
      const suggested = stageFromEnrollment(selectedEnrollment);
      if (suggested) {
        setRmkStage(suggested);
        return;
      }
    }
    const firstStep = selectedRmkFlow?.steps?.[0]?.step_order;
    if (firstStep) {
      setRmkStage(`s${Number(firstStep)}`);
    }
  }, [selectedEnrollment, selectedRmkFlow]);

  return (
    <div className="placeholder-view" style={{ alignItems: "stretch" }}>
      <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: 12, minHeight: 520 }}>
        <div style={{ ...panelStyle, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ padding: 12, borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
            <h2 style={{ margin: "0 0 8px" }}>Clientes</h2>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar por nombre, teléfono o texto..."
              style={inputStyle}
            />
          </div>

          <div style={{ overflow: "auto", padding: 8, display: "grid", gap: 6 }}>
            {loading && customers.length === 0 ? <div style={{ opacity: 0.75, padding: 8 }}>Cargando...</div> : null}
            {!loading && customers.length === 0 ? <div style={{ opacity: 0.75, padding: 8 }}>Sin resultados</div> : null}

            {customers.map((c) => (
              <button
                key={c.phone}
                onClick={() => setSelectedPhone(c.phone)}
                style={{
                  textAlign: "left",
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 10,
                  padding: 10,
                  background: selectedPhone === c.phone ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.03)",
                  color: "inherit",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontWeight: 600 }}>{fullName(c)}</div>
                <div style={{ fontSize: 12, opacity: 0.75 }}>{c.phone}</div>
                <div style={{ fontSize: 11, marginTop: 4, opacity: 0.8 }}>
                  Intento: {c.intent_current || "-"} | Pago: {c.payment_status || "-"}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div style={{ ...panelStyle, padding: 14, overflow: "auto" }}>
          {!selectedPhone ? (
            <div style={{ opacity: 0.75 }}>Selecciona un cliente.</div>
          ) : (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 12 }}>
                <div>
                  <h3 style={{ margin: 0 }}>{fullName(selected)}</h3>
                  <div style={{ fontSize: 12, opacity: 0.75 }}>{selectedPhone}</div>
                </div>
                <button onClick={saveCustomer} disabled={saving} style={{ padding: "8px 14px", borderRadius: 10, cursor: "pointer" }}>
                  {saving ? "Guardando..." : "Guardar"}
                </button>
              </div>

              {error ? <div style={{ color: "#ff7b7b", marginBottom: 8 }}>{error}</div> : null}
              {status ? <div style={{ color: "#9be15d", marginBottom: 8 }}>{status}</div> : null}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Nombre</div>
                  <input style={inputStyle} value={form.first_name || ""} onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))} />
                </label>

                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Apellido</div>
                  <input style={inputStyle} value={form.last_name || ""} onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))} />
                </label>

                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Ciudad</div>
                  <input style={inputStyle} value={form.city || ""} onChange={(e) => setForm((p) => ({ ...p, city: e.target.value }))} />
                </label>

                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Tipo cliente</div>
                  <input style={inputStyle} value={form.customer_type || ""} onChange={(e) => setForm((p) => ({ ...p, customer_type: e.target.value }))} />
                </label>

                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Estado pago</div>
                  <input style={inputStyle} value={form.payment_status || ""} onChange={(e) => setForm((p) => ({ ...p, payment_status: e.target.value }))} />
                </label>

                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Referencia pago</div>
                  <input style={inputStyle} value={form.payment_reference || ""} onChange={(e) => setForm((p) => ({ ...p, payment_reference: e.target.value }))} />
                </label>
              </div>

              <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Intereses</div>
                  <input style={inputStyle} value={form.interests || ""} onChange={(e) => setForm((p) => ({ ...p, interests: e.target.value }))} />
                </label>

                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Tags (coma separadas)</div>
                  <input style={inputStyle} value={form.tags || ""} onChange={(e) => setForm((p) => ({ ...p, tags: e.target.value }))} />
                </label>

                <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10 }}>
                  <div style={{ fontWeight: 600, marginBottom: 8 }}>Remarketing por etapas</div>
                  {rmkCatalog.length === 0 ? (
                    <div style={{ fontSize: 12, opacity: 0.8 }}>No hay flows activos para asignar.</div>
                  ) : (
                    <>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 8 }}>
                        <select style={inputStyle} value={rmkFlowId} onChange={(e) => setRmkFlowId(e.target.value)}>
                          <option value="">Flow</option>
                          {rmkCatalog.map((f) => (
                            <option key={f.id} value={String(f.id)}>
                              {f.name}
                            </option>
                          ))}
                        </select>
                        <select style={inputStyle} value={rmkStage} onChange={(e) => setRmkStage(e.target.value)}>
                          <option value="">Etapa</option>
                          {stageOptions.map((s) => (
                            <option key={s.value} value={s.value}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                        <button
                          style={{ padding: "8px 12px", borderRadius: 8, cursor: "pointer" }}
                          onClick={applyRemarketingStage}
                          disabled={!rmkFlowId || !rmkStage || rmkSaving}
                        >
                          {rmkSaving ? "Aplicando..." : "Aplicar"}
                        </button>
                      </div>
                      <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 12, marginTop: 8 }}>
                        <input type="checkbox" checked={!!rmkSendNow} onChange={(e) => setRmkSendNow(e.target.checked)} />
                        Enviar al instante al mover a etapa activa
                      </label>
                      <div style={{ fontSize: 12, opacity: 0.8, marginTop: 8 }}>
                        Actual: {selectedEnrollment ? `${selectedEnrollment.flow_name || "Flow"} - ${selectedEnrollment.state} - ${selectedEnrollment.current_stage_name || defaultStageName(selectedEnrollment.current_step_order)} (paso ${selectedEnrollment.current_step_order || "-"})` : "Sin enrollment"}
                        {String(selectedEnrollment?.state || "").toLowerCase() === "hold" && selectedEnrollment?.meta_json?.hold_reason
                          ? ` | motivo hold: ${selectedEnrollment.meta_json.hold_reason}`
                          : ""}
                      </div>
                    </>
                  )}
                </div>

                <label>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>Notas</div>
                  <textarea
                    style={{ ...inputStyle, minHeight: 140, resize: "vertical" }}
                    value={form.notes || ""}
                    onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
                  />
                </label>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

