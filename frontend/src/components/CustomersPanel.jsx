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

  const selected = useMemo(
    () => customers.find((c) => c.phone === selectedPhone) || null,
    [customers, selectedPhone]
  );

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
    const t = setTimeout(() => {
      loadCustomers();
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  useEffect(() => {
    if (selectedPhone) {
      loadCustomerDetail(selectedPhone);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPhone]);

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

