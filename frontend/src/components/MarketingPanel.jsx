import React, { useEffect, useMemo, useState } from "react";
import TemplateBuilderPanel from "./TemplateBuilderPanel";
import TriggerBuilderPanel from "./TriggerBuilderPanel";

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

function fmtDt(v) {
  if (!v) return "-";
  try {
    return new Date(v).toLocaleString();
  } catch {
    return String(v);
  }
}

function defaultStageName(stepOrder) {
  const n = Number(stepOrder || 0);
  if (n === 1) return "Primer contacto";
  if (n === 2) return "Seguimiento intensivo";
  if (n === 3) return "Cierre fuerte";
  return `Etapa ${n || 1}`;
}

function takeoverTokenToBool(token) {
  const v = String(token || "all").toLowerCase();
  if (v === "on") return true;
  if (v === "off") return false;
  return null;
}

export default function MarketingPanel({ apiBase }) {
  const API = (apiBase || "").replace(/\/$/, "");

  const [tab, setTab] = useState("templates");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const [templates, setTemplates] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [triggers, setTriggers] = useState([]);
  const [flows, setFlows] = useState([]);
  const [segments, setSegments] = useState([]);
  const [steps, setSteps] = useState([]);
  const [engineInfo, setEngineInfo] = useState(null);

  const [selectedFlowId, setSelectedFlowId] = useState(null);

  const [templateForm, setTemplateForm] = useState({
    name: "",
    category: "general",
    body: "",
    variables: "nombre,producto",
    status: "draft",
  });

  const [campaignForm, setCampaignForm] = useState({
    name: "",
    objective: "",
    segment_id: "",
    template_id: "",
    scheduled_at: "",
  });

  const [flowForm, setFlowForm] = useState({
    name: "",
    is_active: false,
    entry_intent: "BUY_FLOW",
    entry_tag: "",
    entry_payment_status: "",
    entry_city: "",
    entry_customer_type: "",
    entry_takeover: "all",
    resume_after_minutes: 120,
    retry_minutes: 30,
    exit_intent: "",
    exit_tag: "",
    exit_payment_status: "paid",
    exit_city: "",
    exit_customer_type: "",
    exit_takeover: "all",
  });

  const [stepForm, setStepForm] = useState({
    step_order: 1,
    stage_name: "Primer contacto",
    wait_minutes: 60,
    template_id: "",
  });

  const selectedFlow = useMemo(
    () => flows.find((f) => f.id === selectedFlowId) || null,
    [flows, selectedFlowId]
  );

  const flowWaitTotalMinutes = useMemo(() => {
    return (steps || []).reduce((acc, s) => acc + Math.max(0, Number(s.wait_minutes || 0)), 0);
  }, [steps]);

  const setTempStatus = (txt) => {
    setStatus(txt);
    setTimeout(() => setStatus(""), 2200);
  };

  const loadTemplates = async () => {
    const r = await fetch(`${API}/api/templates`);
    const d = await r.json();
    if (!r.ok) throw new Error(d?.detail || "Error templates");
    setTemplates(Array.isArray(d?.templates) ? d.templates : []);
  };

  const loadCampaigns = async () => {
    const r = await fetch(`${API}/api/campaigns`);
    const d = await r.json();
    if (!r.ok) throw new Error(d?.detail || "Error campaigns");
    setCampaigns(Array.isArray(d?.campaigns) ? d.campaigns : []);
  };

  const loadTriggers = async () => {
    const r = await fetch(`${API}/api/triggers`);
    const d = await r.json();
    if (!r.ok) throw new Error(d?.detail || "Error triggers");
    setTriggers(Array.isArray(d?.triggers) ? d.triggers : []);
  };

  const loadFlows = async () => {
    const r = await fetch(`${API}/api/remarketing/flows`);
    const d = await r.json();
    if (!r.ok) throw new Error(d?.detail || "Error flows");
    const rows = Array.isArray(d?.flows) ? d.flows : [];
    setFlows(rows);
    if (!selectedFlowId && rows[0]?.id) {
      setSelectedFlowId(rows[0].id);
    } else if (selectedFlowId && !rows.some((x) => x.id === selectedFlowId)) {
      setSelectedFlowId(rows[0]?.id || null);
    }
  };

  const loadSegments = async () => {
    const r = await fetch(`${API}/api/customers/segments?active=all`);
    const d = await r.json();
    if (!r.ok) throw new Error(d?.detail || "Error segments");
    setSegments(Array.isArray(d?.segments) ? d.segments : []);
  };

  const loadEngineStatus = async () => {
    const r = await fetch(`${API}/api/campaigns/engine/status`);
    const d = await r.json();
    if (!r.ok) throw new Error(d?.detail || "Error engine status");
    setEngineInfo(d || null);
  };

  const loadSteps = async (flowId) => {
    if (!flowId) {
      setSteps([]);
      return;
    }
    const r = await fetch(`${API}/api/remarketing/flows/${encodeURIComponent(flowId)}/steps`);
    const d = await r.json();
    if (!r.ok) throw new Error(d?.detail || "Error steps");
    setSteps(Array.isArray(d?.steps) ? d.steps : []);
  };

  const loadAll = async () => {
    setError("");
    try {
      await Promise.all([loadTemplates(), loadCampaigns(), loadTriggers(), loadFlows(), loadSegments(), loadEngineStatus()]);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadSteps(selectedFlowId).catch((e) => setError(String(e.message || e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFlowId]);

  const createTemplate = async () => {
    setError("");
    try {
      const payload = {
        name: templateForm.name.trim(),
        category: templateForm.category.trim() || "general",
        body: templateForm.body,
        variables_json: (templateForm.variables || "")
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),
        status: templateForm.status || "draft",
      };

      const r = await fetch(`${API}/api/templates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo crear plantilla");
      setTemplateForm((p) => ({ ...p, name: "", body: "" }));
      await loadTemplates();
      setTempStatus("Plantilla creada");
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const createCampaign = async () => {
    setError("");
    try {
      const payload = {
        name: campaignForm.name.trim(),
        objective: campaignForm.objective || "",
        segment_id: campaignForm.segment_id ? Number(campaignForm.segment_id) : null,
        template_id: campaignForm.template_id ? Number(campaignForm.template_id) : null,
        scheduled_at: campaignForm.scheduled_at ? new Date(campaignForm.scheduled_at).toISOString() : null,
        status: "draft",
      };

      const r = await fetch(`${API}/api/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo crear campaña");
      setCampaignForm({ name: "", objective: "", segment_id: "", template_id: "", scheduled_at: "" });
      await loadCampaigns();
      setTempStatus("Campaña creada");
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const launchCampaign = async (id) => {
    setError("");
    try {
      const r = await fetch(`${API}/api/campaigns/${encodeURIComponent(id)}/launch?max_recipients=300`, { method: "POST" });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo lanzar campaña");
      await loadCampaigns();
      setTempStatus(`Campaña ${id} lanzada`);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const tickEngineNow = async () => {
    setError("");
    try {
      const r = await fetch(`${API}/api/campaigns/engine/tick?batch_size=20&send_delay_ms=0`, { method: "POST" });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo ejecutar motor");
      await Promise.all([loadCampaigns(), loadEngineStatus()]);
      setTempStatus(`Motor ejecutado: sent=${d?.sent ?? 0} failed=${d?.failed ?? 0}`);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const createFlow = async () => {
    setError("");
    try {
      const entryRules = {};
      if (String(flowForm.entry_intent || "").trim()) entryRules.intent = String(flowForm.entry_intent).trim();
      if (String(flowForm.entry_tag || "").trim()) entryRules.tag = String(flowForm.entry_tag).trim();
      if (String(flowForm.entry_payment_status || "").trim()) entryRules.payment_status = String(flowForm.entry_payment_status).trim();
      if (String(flowForm.entry_city || "").trim()) entryRules.city = String(flowForm.entry_city).trim();
      if (String(flowForm.entry_customer_type || "").trim()) entryRules.customer_type = String(flowForm.entry_customer_type).trim();
      const entryTakeover = takeoverTokenToBool(flowForm.entry_takeover);
      if (entryTakeover !== null) entryRules.takeover = entryTakeover;
      if (Number(flowForm.resume_after_minutes) > 0) entryRules.resume_after_minutes = Number(flowForm.resume_after_minutes);
      if (Number(flowForm.retry_minutes) > 0) entryRules.retry_minutes = Number(flowForm.retry_minutes);

      const exitRules = {};
      if (String(flowForm.exit_intent || "").trim()) exitRules.intent = String(flowForm.exit_intent).trim();
      if (String(flowForm.exit_tag || "").trim()) exitRules.tag = String(flowForm.exit_tag).trim();
      if (String(flowForm.exit_payment_status || "").trim()) exitRules.payment_status = String(flowForm.exit_payment_status).trim();
      if (String(flowForm.exit_city || "").trim()) exitRules.city = String(flowForm.exit_city).trim();
      if (String(flowForm.exit_customer_type || "").trim()) exitRules.customer_type = String(flowForm.exit_customer_type).trim();
      const exitTakeover = takeoverTokenToBool(flowForm.exit_takeover);
      if (exitTakeover !== null) exitRules.takeover = exitTakeover;

      const payload = {
        name: flowForm.name.trim(),
        is_active: !!flowForm.is_active,
        entry_rules_json: entryRules,
        exit_rules_json: exitRules,
      };

      const r = await fetch(`${API}/api/remarketing/flows`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo crear flow");
      setFlowForm((p) => ({ ...p, name: "" }));
      await loadFlows();
      setTempStatus("Flow creado");
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const addStep = async () => {
    if (!selectedFlowId) return;
    setError("");
    try {
      const payload = {
        step_order: Number(stepForm.step_order || 1),
        stage_name: String(stepForm.stage_name || "").trim(),
        wait_minutes: Number(stepForm.wait_minutes || 0),
        template_id: stepForm.template_id ? Number(stepForm.template_id) : null,
      };
      const r = await fetch(`${API}/api/remarketing/flows/${encodeURIComponent(selectedFlowId)}/steps`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo crear paso");
      await loadSteps(selectedFlowId);
      const nextOrder = Number(stepForm.step_order || 1) + 1;
      setStepForm((p) => ({ ...p, step_order: nextOrder, stage_name: defaultStageName(nextOrder) }));
      setTempStatus("Paso agregado");
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  return (
    <div className="placeholder-view" style={{ alignItems: "stretch", flexDirection: "column", justifyContent: "flex-start" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Marketing</h2>
        <button onClick={loadAll} style={smallBtn}>Recargar</button>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {["templates", "campaigns", "triggers", "remarketing"].map((k) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            style={{
              ...smallBtn,
              background: tab === k ? "rgba(255,255,255,0.16)" : "transparent",
            }}
          >
            {k === "templates" ? "Plantillas" : k === "campaigns" ? "Campañas" : k === "triggers" ? "Triggers" : "Remarketing"}
          </button>
        ))}
      </div>

      {error ? <div style={{ color: "#ff7b7b", marginBottom: 8 }}>Error: {error}</div> : null}
      {status ? <div style={{ color: "#9be15d", marginBottom: 8 }}>{status}</div> : null}

      {tab === "templates" ? (
        <TemplateBuilderPanel
          apiBase={API}
          templates={templates}
          onTemplatesReload={loadTemplates}
          onError={(msg) => setError(String(msg || ""))}
          onStatus={setTempStatus}
        />
      ) : null}

      {tab === "campaigns" ? (
        <div style={{ display: "grid", gridTemplateColumns: "420px 1fr", gap: 12 }}>
          <div style={box}>
            <h3 style={{ marginTop: 0 }}>Nueva campaña</h3>
            <div style={{ display: "grid", gap: 8 }}>
              <input style={input} placeholder="Nombre" value={campaignForm.name} onChange={(e) => setCampaignForm((p) => ({ ...p, name: e.target.value }))} />
              <input style={input} placeholder="Objetivo" value={campaignForm.objective} onChange={(e) => setCampaignForm((p) => ({ ...p, objective: e.target.value }))} />
              <select style={input} value={campaignForm.segment_id} onChange={(e) => setCampaignForm((p) => ({ ...p, segment_id: e.target.value }))}>
                <option value="">Segmento (todos)</option>
                {segments.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <select style={input} value={campaignForm.template_id} onChange={(e) => setCampaignForm((p) => ({ ...p, template_id: e.target.value }))}>
                <option value="">Plantilla</option>
                {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
              <input style={input} type="datetime-local" value={campaignForm.scheduled_at} onChange={(e) => setCampaignForm((p) => ({ ...p, scheduled_at: e.target.value }))} />
              <button onClick={createCampaign} style={smallBtn}>Crear campaña</button>
            </div>

            <div style={{ marginTop: 12, borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: 10 }}>
              <h4 style={{ margin: "0 0 8px" }}>Motor de campañas</h4>
              <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 8 }}>
                Estado: {engineInfo?.running ? "running" : "stopped"} | Enabled: {String(engineInfo?.enabled ?? false)}
              </div>
              <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 8 }}>
                Intervalo: {engineInfo?.interval_sec ?? "-"}s | Batch: {engineInfo?.batch_size ?? "-"} | Delay: {engineInfo?.send_delay_ms ?? "-"}ms
              </div>
              <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 8 }}>
                Remarketing: enabled={String(engineInfo?.remarketing_enabled ?? false)} | batch={engineInfo?.remarketing_batch_size ?? "-"} | resume={engineInfo?.remarketing_resume_after_minutes ?? "-"} min | ventana={engineInfo?.remarketing_service_window_hours ?? 24}h
              </div>
              <button onClick={tickEngineNow} style={smallBtn}>Procesar lote ahora</button>
            </div>
          </div>

          <div style={box}>
            <h3 style={{ marginTop: 0 }}>Campañas</h3>
            <div style={{ display: "grid", gap: 8 }}>
              {campaigns.map((c) => (
                <div key={c.id} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{c.name}</div>
                      <div style={{ fontSize: 12, opacity: 0.75 }}>
                        {c.objective || "-"} | {c.status} | template: {c.template_name || "-"}
                      </div>
                      <div style={{ fontSize: 11, opacity: 0.65 }}>Programada: {fmtDt(c.scheduled_at)}</div>
                    </div>
                    <button style={smallBtn} onClick={() => launchCampaign(c.id)}>Lanzar</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {tab === "triggers" ? (
        <TriggerBuilderPanel
          apiBase={API}
          templates={templates}
          triggers={triggers}
          onTriggersReload={loadTriggers}
          onError={(msg) => setError(String(msg || ""))}
          onStatus={setTempStatus}
        />
      ) : null}

      {tab === "remarketing" ? (
        <div style={{ display: "grid", gridTemplateColumns: "420px 1fr", gap: 12 }}>
          <div style={{ display: "grid", gap: 12 }}>
            <div style={box}>
              <h3 style={{ marginTop: 0 }}>Nuevo flow</h3>
              <div style={{ display: "grid", gap: 8 }}>
                <input style={input} placeholder="Nombre" value={flowForm.name} onChange={(e) => setFlowForm((p) => ({ ...p, name: e.target.value }))} />
                <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10, display: "grid", gap: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, opacity: 0.85 }}>Reglas de entrada al remarketing</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    <input style={input} placeholder="Intent (ej: BUY_FLOW)" value={flowForm.entry_intent} onChange={(e) => setFlowForm((p) => ({ ...p, entry_intent: e.target.value }))} />
                    <input style={input} placeholder="Tag contiene" value={flowForm.entry_tag} onChange={(e) => setFlowForm((p) => ({ ...p, entry_tag: e.target.value }))} />
                    <input style={input} placeholder="Payment status" value={flowForm.entry_payment_status} onChange={(e) => setFlowForm((p) => ({ ...p, entry_payment_status: e.target.value }))} />
                    <input style={input} placeholder="Ciudad contiene" value={flowForm.entry_city} onChange={(e) => setFlowForm((p) => ({ ...p, entry_city: e.target.value }))} />
                    <input style={input} placeholder="Tipo cliente" value={flowForm.entry_customer_type} onChange={(e) => setFlowForm((p) => ({ ...p, entry_customer_type: e.target.value }))} />
                    <select style={input} value={flowForm.entry_takeover} onChange={(e) => setFlowForm((p) => ({ ...p, entry_takeover: e.target.value }))}>
                      <option value="all">Takeover: cualquiera</option>
                      <option value="on">Takeover ON</option>
                      <option value="off">Takeover OFF</option>
                    </select>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    <input style={input} type="number" min={1} placeholder="Reanudar hold después de (min)" value={flowForm.resume_after_minutes} onChange={(e) => setFlowForm((p) => ({ ...p, resume_after_minutes: e.target.value }))} />
                    <input style={input} type="number" min={1} placeholder="Retry error envío (min)" value={flowForm.retry_minutes} onChange={(e) => setFlowForm((p) => ({ ...p, retry_minutes: e.target.value }))} />
                  </div>
                </div>
                <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10, display: "grid", gap: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, opacity: 0.85 }}>Reglas de salida del flow</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    <input style={input} placeholder="Intent" value={flowForm.exit_intent} onChange={(e) => setFlowForm((p) => ({ ...p, exit_intent: e.target.value }))} />
                    <input style={input} placeholder="Tag contiene" value={flowForm.exit_tag} onChange={(e) => setFlowForm((p) => ({ ...p, exit_tag: e.target.value }))} />
                    <input style={input} placeholder="Payment status (ej: paid)" value={flowForm.exit_payment_status} onChange={(e) => setFlowForm((p) => ({ ...p, exit_payment_status: e.target.value }))} />
                    <input style={input} placeholder="Ciudad contiene" value={flowForm.exit_city} onChange={(e) => setFlowForm((p) => ({ ...p, exit_city: e.target.value }))} />
                    <input style={input} placeholder="Tipo cliente" value={flowForm.exit_customer_type} onChange={(e) => setFlowForm((p) => ({ ...p, exit_customer_type: e.target.value }))} />
                    <select style={input} value={flowForm.exit_takeover} onChange={(e) => setFlowForm((p) => ({ ...p, exit_takeover: e.target.value }))}>
                      <option value="all">Takeover: cualquiera</option>
                      <option value="on">Takeover ON</option>
                      <option value="off">Takeover OFF</option>
                    </select>
                  </div>
                </div>
                <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input type="checkbox" checked={!!flowForm.is_active} onChange={(e) => setFlowForm((p) => ({ ...p, is_active: e.target.checked }))} />
                  Activo
                </label>
                <button onClick={createFlow} style={smallBtn}>Crear flow</button>
              </div>
            </div>

            <div style={box}>
              <h3 style={{ marginTop: 0 }}>Flows</h3>
              <div style={{ display: "grid", gap: 6 }}>
                {flows.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setSelectedFlowId(f.id)}
                    style={{
                      ...smallBtn,
                      textAlign: "left",
                      background: selectedFlowId === f.id ? "rgba(255,255,255,0.16)" : "transparent",
                    }}
                  >
                    {f.name} ({f.steps_count || 0} pasos) {f.is_active ? "[activo]" : ""}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div style={box}>
            <h3 style={{ marginTop: 0 }}>Pasos del flow {selectedFlow ? `: ${selectedFlow.name}` : ""}</h3>

            <div style={{ display: "grid", gridTemplateColumns: "100px 170px 120px 1fr auto", gap: 8, marginBottom: 12 }}>
              <input style={input} type="number" value={stepForm.step_order} onChange={(e) => setStepForm((p) => ({ ...p, step_order: e.target.value }))} placeholder="Orden" />
              <input style={input} value={stepForm.stage_name} onChange={(e) => setStepForm((p) => ({ ...p, stage_name: e.target.value }))} placeholder="Nombre etapa" />
              <input style={input} type="number" value={stepForm.wait_minutes} onChange={(e) => setStepForm((p) => ({ ...p, wait_minutes: e.target.value }))} placeholder="Wait min" />
              <select style={input} value={stepForm.template_id} onChange={(e) => setStepForm((p) => ({ ...p, template_id: e.target.value }))}>
                <option value="">Plantilla</option>
                {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
              <button style={smallBtn} onClick={addStep} disabled={!selectedFlowId}>Agregar</button>
            </div>

            <div style={{ fontSize: 12, marginBottom: 8, color: flowWaitTotalMinutes > 1380 ? "#ff9f6e" : "rgba(255,255,255,0.75)" }}>
              Tiempo total configurado del flow: {flowWaitTotalMinutes} min ({Math.round((flowWaitTotalMinutes / 60) * 10) / 10}h)
              {flowWaitTotalMinutes > 1380 ? " | Recomendado: <= 1380 min para respetar ventana de 24h." : ""}
            </div>

            <div style={{ display: "grid", gap: 8 }}>
              {steps.map((s) => (
                <div key={s.id} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10 }}>
                  Paso {s.step_order} ({s.stage_name || defaultStageName(s.step_order)}) | Espera {s.wait_minutes} min | Plantilla: {s.template_name || s.template_id || "-"}
                </div>
              ))}
              {selectedFlowId && steps.length === 0 ? <div style={{ opacity: 0.75 }}>Sin pasos todavía.</div> : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

