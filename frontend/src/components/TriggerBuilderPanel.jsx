import React, { useEffect, useMemo, useState } from "react";

const panel = {
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
  border: "1px solid rgba(255,120,120,0.5)",
  color: "#ffb0b0",
};

function blankTrigger() {
  return {
    id: null,
    name: "",
    event_type: "message_in",
    trigger_type: "message_flow",
    flow_event: "received",
    cooldown_minutes: 60,
    is_active: true,
    assistant_enabled: false,
    assistant_message_type: "auto",
    priority: 100,
    block_ai: true,
    stop_on_match: true,
    only_when_no_takeover: true,
  };
}

function blankCondition(type = "check_words") {
  if (type === "template_sent_status") return { type, state: "not_sent", template_id: "" };
  if (type === "current_tag") return { type, state: "has", tag: "" };
  if (type === "last_message_sent") return { type, op: "gte", minutes: 10 };
  if (type === "sent_count") return { type, op: "gte", value: 1, window_hours: 24 };
  if (type === "schedule") {
    return { type, timezone: "America/Bogota", start_time: "08:00", end_time: "20:00", days: ["mon", "tue", "wed", "thu", "fri", "sat"] };
  }
  return { type: "check_words", mode: "any", words: [] };
}

function blankAction(type = "send_template") {
  if (type === "change_tag") return { type, mode: "add", tag: "" };
  if (type === "configure_conversation") return { type, takeover: "keep", ai_state: "" };
  if (type === "change_contact_status") return { type, field: "customer_type", status: "" };
  if (type === "notify_admins") return { type, phones: "", message: "" };
  if (type === "extract_conversation_info") return { type, last_messages: 10 };
  if (type === "schedule_message") return { type, template_id: "", delay_minutes: 30 };
  return { type: "send_template", template_id: "" };
}

function normalizeConditions(raw) {
  const root = raw && typeof raw === "object" ? raw : {};
  let rows = Array.isArray(root.conditions) ? root.conditions : [];
  if (!rows.length && Array.isArray(root.all)) rows = root.all;
  if (!rows.length && root.contains) rows = [{ type: "check_words", words: [String(root.contains)] }];
  return rows.filter((x) => x && typeof x === "object");
}

function normalizeActions(raw) {
  const root = raw && typeof raw === "object" ? raw : {};
  let rows = Array.isArray(root.actions) ? root.actions : [];
  if (!rows.length && Array.isArray(root.list)) rows = root.list;
  if (!rows.length && root.type) rows = [root];
  return rows.filter((x) => x && typeof x === "object");
}

function cleanConditions(conditions) {
  return (conditions || [])
    .map((c) => {
      const type = String(c?.type || "").trim().toLowerCase();
      if (!type) return null;

      if (type === "check_words") {
        const words = Array.isArray(c.words)
          ? c.words.map((w) => String(w || "").trim()).filter(Boolean)
          : [];
        return { type, mode: c.mode === "all" ? "all" : "any", words };
      }
      if (type === "template_sent_status") {
        return { type, state: c.state === "sent" ? "sent" : "not_sent", template_id: c.template_id ? Number(c.template_id) : null };
      }
      if (type === "current_tag") {
        return { type, state: c.state === "not_has" ? "not_has" : "has", tag: String(c.tag || "").trim() };
      }
      if (type === "last_message_sent") {
        return { type, op: c.op || "gte", minutes: Number(c.minutes || 0) };
      }
      if (type === "sent_count") {
        return { type, op: c.op || "gte", value: Number(c.value || 0), window_hours: Number(c.window_hours || 24) };
      }
      if (type === "schedule") {
        const days = Array.isArray(c.days) ? c.days.map((d) => String(d || "").slice(0, 3).toLowerCase()) : [];
        return {
          type,
          timezone: String(c.timezone || "America/Bogota").trim(),
          start_time: String(c.start_time || "08:00"),
          end_time: String(c.end_time || "20:00"),
          days,
        };
      }
      return c;
    })
    .filter(Boolean);
}

function cleanActions(actions) {
  return (actions || [])
    .map((a) => {
      const type = String(a?.type || "").trim().toLowerCase();
      if (!type) return null;

      if (type === "send_template") {
        return { type, template_id: a.template_id ? Number(a.template_id) : null };
      }
      if (type === "change_tag") {
        return { type, mode: a.mode || "add", tag: String(a.tag || "").trim() };
      }
      if (type === "configure_conversation") {
        return {
          type,
          takeover: String(a.takeover || "keep"),
          ai_state: String(a.ai_state || "").trim(),
          clear_ai_state: !!a.clear_ai_state,
        };
      }
      if (type === "change_contact_status") {
        return { type, field: a.field || "customer_type", status: String(a.status || "").trim() };
      }
      if (type === "notify_admins") {
        return { type, phones: String(a.phones || "").trim(), message: String(a.message || "").trim() };
      }
      if (type === "extract_conversation_info") {
        return { type, last_messages: Number(a.last_messages || 10) };
      }
      if (type === "schedule_message") {
        return { type, template_id: a.template_id ? Number(a.template_id) : null, delay_minutes: Number(a.delay_minutes || 0) };
      }
      return a;
    })
    .filter(Boolean);
}

const weekDays = [
  { key: "mon", label: "Lun" },
  { key: "tue", label: "Mar" },
  { key: "wed", label: "Mie" },
  { key: "thu", label: "Jue" },
  { key: "fri", label: "Vie" },
  { key: "sat", label: "Sab" },
  { key: "sun", label: "Dom" },
];

export default function TriggerBuilderPanel({
  apiBase,
  templates,
  triggers,
  onTriggersReload,
  onError,
  onStatus,
}) {
  const API = (apiBase || "").replace(/\/$/, "");
  const [catalog, setCatalog] = useState(null);
  const [selectedTriggerId, setSelectedTriggerId] = useState(null);
  const [form, setForm] = useState(blankTrigger());
  const [conditionMode, setConditionMode] = useState("all");
  const [conditions, setConditions] = useState([]);
  const [actions, setActions] = useState([]);
  const [conditionDraft, setConditionDraft] = useState("check_words");
  const [actionDraft, setActionDraft] = useState("send_template");
  const [tab, setTab] = useState("conditions");
  const [wordDraft, setWordDraft] = useState({});

  useEffect(() => {
    const run = async () => {
      try {
        const r = await fetch(`${API}/api/triggers/catalog`);
        const d = await r.json();
        if (!r.ok) throw new Error(d?.detail || "No se pudo cargar catalogo de triggers");
        setCatalog(d || null);
      } catch (e) {
        onError?.(String(e.message || e));
      }
    };
    run();
  }, [API, onError]);

  useEffect(() => {
    if (!selectedTriggerId && triggers?.[0]?.id) setSelectedTriggerId(triggers[0].id);
  }, [triggers, selectedTriggerId]);

  useEffect(() => {
    if (!selectedTriggerId) {
      setForm(blankTrigger());
      setConditionMode("all");
      setConditions([]);
      setActions([]);
      return;
    }
    const t = (triggers || []).find((x) => x.id === selectedTriggerId);
    if (!t) return;

    const condRoot = t.conditions_json && typeof t.conditions_json === "object" ? t.conditions_json : {};
    setForm({
      id: t.id,
      name: t.name || "",
      event_type: t.event_type || "message_in",
      trigger_type: t.trigger_type || "message_flow",
      flow_event: t.flow_event || "received",
      cooldown_minutes: Number(t.cooldown_minutes || 0),
      is_active: !!t.is_active,
      assistant_enabled: !!t.assistant_enabled,
      assistant_message_type: t.assistant_message_type || "auto",
      priority: Number(t.priority || 100),
      block_ai: !!t.block_ai,
      stop_on_match: !!t.stop_on_match,
      only_when_no_takeover: !!t.only_when_no_takeover,
    });
    setConditionMode(condRoot.match === "any" ? "any" : "all");
    setConditions(normalizeConditions(t.conditions_json));
    setActions(normalizeActions(t.action_json));
  }, [selectedTriggerId, triggers]);

  const triggerTypes = useMemo(() => Array.isArray(catalog?.trigger_types) ? catalog.trigger_types : [], [catalog]);
  const flowEvents = useMemo(() => Array.isArray(catalog?.flow_events) ? catalog.flow_events : [], [catalog]);
  const conditionTypes = useMemo(() => Array.isArray(catalog?.condition_types) ? catalog.condition_types : [], [catalog]);
  const actionTypes = useMemo(() => Array.isArray(catalog?.action_types) ? catalog.action_types : [], [catalog]);
  const assistantTypes = useMemo(() => Array.isArray(catalog?.assistant_message_types) ? catalog.assistant_message_types : [], [catalog]);

  const updateCondition = (idx, patch) => {
    setConditions((prev) => prev.map((c, i) => (i === idx ? { ...c, ...patch } : c)));
  };

  const updateAction = (idx, patch) => {
    setActions((prev) => prev.map((a, i) => (i === idx ? { ...a, ...patch } : a)));
  };

  const moveItem = (type, idx, dir) => {
    const fn = type === "condition" ? setConditions : setActions;
    fn((prev) => {
      const next = [...prev];
      const to = idx + dir;
      if (to < 0 || to >= next.length) return prev;
      const tmp = next[idx];
      next[idx] = next[to];
      next[to] = tmp;
      return next;
    });
  };

  const saveTrigger = async () => {
    try {
      const payload = {
        name: String(form.name || "").trim(),
        event_type: "message_in",
        trigger_type: form.trigger_type || "message_flow",
        flow_event: form.flow_event || "received",
        cooldown_minutes: Number(form.cooldown_minutes || 0),
        is_active: !!form.is_active,
        assistant_enabled: !!form.assistant_enabled,
        assistant_message_type: form.assistant_message_type || "auto",
        priority: Number(form.priority || 100),
        block_ai: !!form.block_ai,
        stop_on_match: !!form.stop_on_match,
        only_when_no_takeover: !!form.only_when_no_takeover,
        conditions_json: { match: conditionMode, conditions: cleanConditions(conditions) },
        action_json: { actions: cleanActions(actions) },
      };

      if (!payload.name) throw new Error("Nombre del trigger requerido");

      const isUpdate = !!form.id;
      const url = isUpdate ? `${API}/api/triggers/${encodeURIComponent(form.id)}` : `${API}/api/triggers`;
      const method = isUpdate ? "PATCH" : "POST";

      const r = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo guardar trigger");

      await onTriggersReload?.();
      const id = d?.trigger?.id || form.id || null;
      if (id) setSelectedTriggerId(id);
      onStatus?.(isUpdate ? "Trigger actualizado" : "Trigger creado");
    } catch (e) {
      onError?.(String(e.message || e));
    }
  };

  const toggleActive = async (trigger) => {
    try {
      const r = await fetch(`${API}/api/triggers/${encodeURIComponent(trigger.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !trigger.is_active }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo actualizar trigger");
      await onTriggersReload?.();
    } catch (e) {
      onError?.(String(e.message || e));
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "420px 1fr", gap: 12 }}>
      <div style={{ display: "grid", gap: 12 }}>
        <div style={panel}>
          <div style={{ fontSize: 28, color: "#00d9ff", fontWeight: 700, marginBottom: 8 }}>Disparador</div>
          <div style={{ display: "grid", gap: 8 }}>
            <input style={input} placeholder="Nombre" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} />
            <select style={input} value={form.trigger_type} onChange={(e) => setForm((p) => ({ ...p, trigger_type: e.target.value }))}>
              {triggerTypes.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
            </select>
            {form.trigger_type === "message_flow" ? (
              <select style={input} value={form.flow_event} onChange={(e) => setForm((p) => ({ ...p, flow_event: e.target.value }))}>
                {flowEvents.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
              </select>
            ) : null}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <input
                style={input}
                type="number"
                min="0"
                placeholder="Cooldown (min)"
                value={form.cooldown_minutes}
                onChange={(e) => setForm((p) => ({ ...p, cooldown_minutes: e.target.value }))}
              />
              <input
                style={input}
                type="number"
                min="1"
                placeholder="Prioridad"
                value={form.priority}
                onChange={(e) => setForm((p) => ({ ...p, priority: e.target.value }))}
              />
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={!!form.assistant_enabled} onChange={(e) => setForm((p) => ({ ...p, assistant_enabled: e.target.checked }))} />
              Enviar mensajes generado por el asistente
            </label>
            <select style={input} value={form.assistant_message_type} onChange={(e) => setForm((p) => ({ ...p, assistant_message_type: e.target.value }))}>
              {assistantTypes.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
            </select>

            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={!!form.block_ai} onChange={(e) => setForm((p) => ({ ...p, block_ai: e.target.checked }))} />
              Bloquear IA cuando matchee trigger
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={!!form.stop_on_match} onChange={(e) => setForm((p) => ({ ...p, stop_on_match: e.target.checked }))} />
              Detener al primer match
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={!!form.only_when_no_takeover} onChange={(e) => setForm((p) => ({ ...p, only_when_no_takeover: e.target.checked }))} />
              Solo si takeover desactivado
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={!!form.is_active} onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))} />
              Activo
            </label>
            <button style={smallBtn} onClick={saveTrigger}>Guardar</button>
          </div>
        </div>

        <div style={panel}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <strong>Triggers</strong>
            <button style={smallBtn} onClick={() => setSelectedTriggerId(null)}>Nuevo</button>
          </div>
          <div style={{ display: "grid", gap: 8, maxHeight: 320, overflowY: "auto" }}>
            {(triggers || []).map((t) => (
              <div
                key={t.id}
                style={{
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 10,
                  padding: 8,
                  background: selectedTriggerId === t.id ? "rgba(255,255,255,0.08)" : "transparent",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <button style={{ ...smallBtn, flex: 1, textAlign: "left" }} onClick={() => setSelectedTriggerId(t.id)}>
                    <div style={{ fontWeight: 600 }}>{t.name}</div>
                    <div style={{ fontSize: 12, opacity: 0.75 }}>{t.trigger_type} | {t.flow_event} | p{t.priority}</div>
                  </button>
                  <button style={t.is_active ? dangerBtn : smallBtn} onClick={() => toggleActive(t)}>{t.is_active ? "OFF" : "ON"}</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={panel}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
          <button style={{ ...smallBtn, background: tab === "conditions" ? "rgba(255,255,255,0.16)" : "transparent" }} onClick={() => setTab("conditions")}>Condiciones</button>
          <button style={{ ...smallBtn, background: tab === "actions" ? "rgba(80,255,130,0.18)" : "transparent" }} onClick={() => setTab("actions")}>Acciones</button>
        </div>

        {tab === "conditions" ? (
          <div style={{ display: "grid", gap: 10 }}>
            <div style={{ display: "grid", gridTemplateColumns: "150px 1fr auto", gap: 8 }}>
              <select style={input} value={conditionMode} onChange={(e) => setConditionMode(e.target.value)}>
                <option value="all">Cumplir todas</option>
                <option value="any">Cumplir alguna</option>
              </select>
              <select style={input} value={conditionDraft} onChange={(e) => setConditionDraft(e.target.value)}>
                {conditionTypes.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
              </select>
              <button style={smallBtn} onClick={() => setConditions((p) => [...p, blankCondition(conditionDraft)])}>Agregar</button>
            </div>

            {conditions.map((c, idx) => (
              <div key={`${idx}-${c.type}`} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10, display: "grid", gap: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{idx + 1}. {c.type}</strong>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button style={smallBtn} onClick={() => moveItem("condition", idx, -1)}>↑</button>
                    <button style={smallBtn} onClick={() => moveItem("condition", idx, 1)}>↓</button>
                    <button style={dangerBtn} onClick={() => setConditions((p) => p.filter((_, i) => i !== idx))}>Eliminar</button>
                  </div>
                </div>

                {c.type === "check_words" ? (
                  <div style={{ display: "grid", gap: 8 }}>
                    <select style={input} value={c.mode || "any"} onChange={(e) => updateCondition(idx, { mode: e.target.value })}>
                      <option value="any">Cualquiera</option>
                      <option value="all">Todas</option>
                    </select>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8 }}>
                      <input style={input} placeholder="Escribir palabra..." value={wordDraft[idx] || ""} onChange={(e) => setWordDraft((p) => ({ ...p, [idx]: e.target.value }))} />
                      <button
                        style={smallBtn}
                        onClick={() => {
                          const val = String(wordDraft[idx] || "").trim();
                          if (!val) return;
                          const words = Array.isArray(c.words) ? c.words : [];
                          if (!words.includes(val)) updateCondition(idx, { words: [...words, val] });
                          setWordDraft((p) => ({ ...p, [idx]: "" }));
                        }}
                      >
                        +
                      </button>
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {(Array.isArray(c.words) ? c.words : []).map((w, wi) => (
                        <button key={`${wi}-${w}`} style={smallBtn} onClick={() => updateCondition(idx, { words: c.words.filter((_, i) => i !== wi) })}>{w} x</button>
                      ))}
                    </div>
                  </div>
                ) : null}

                {c.type === "template_sent_status" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: 8 }}>
                    <select style={input} value={c.state || "not_sent"} onChange={(e) => updateCondition(idx, { state: e.target.value })}>
                      <option value="not_sent">No enviado</option>
                      <option value="sent">Enviado</option>
                    </select>
                    <select style={input} value={c.template_id || ""} onChange={(e) => updateCondition(idx, { template_id: e.target.value })}>
                      <option value="">Plantilla</option>
                      {(templates || []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                  </div>
                ) : null}

                {c.type === "current_tag" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: 8 }}>
                    <select style={input} value={c.state || "has"} onChange={(e) => updateCondition(idx, { state: e.target.value })}>
                      <option value="has">Tiene etiqueta</option>
                      <option value="not_has">No tiene etiqueta</option>
                    </select>
                    <input style={input} placeholder="Etiqueta" value={c.tag || ""} onChange={(e) => updateCondition(idx, { tag: e.target.value })} />
                  </div>
                ) : null}

                {c.type === "last_message_sent" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: 8 }}>
                    <select style={input} value={c.op || "gte"} onChange={(e) => updateCondition(idx, { op: e.target.value })}>
                      <option value="gte">&gt;=</option>
                      <option value="lte">&lt;=</option>
                      <option value="gt">&gt;</option>
                      <option value="lt">&lt;</option>
                      <option value="eq">=</option>
                    </select>
                    <input style={input} type="number" value={c.minutes || 0} onChange={(e) => updateCondition(idx, { minutes: e.target.value })} placeholder="Minutos" />
                  </div>
                ) : null}

                {c.type === "sent_count" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "130px 1fr 1fr", gap: 8 }}>
                    <select style={input} value={c.op || "gte"} onChange={(e) => updateCondition(idx, { op: e.target.value })}>
                      <option value="gte">&gt;=</option>
                      <option value="lte">&lt;=</option>
                      <option value="gt">&gt;</option>
                      <option value="lt">&lt;</option>
                      <option value="eq">=</option>
                    </select>
                    <input style={input} type="number" value={c.value || 0} onChange={(e) => updateCondition(idx, { value: e.target.value })} placeholder="Cantidad" />
                    <input style={input} type="number" value={c.window_hours || 24} onChange={(e) => updateCondition(idx, { window_hours: e.target.value })} placeholder="Ventana horas" />
                  </div>
                ) : null}

                {c.type === "schedule" ? (
                  <div style={{ display: "grid", gap: 8 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 120px 120px", gap: 8 }}>
                      <input style={input} value={c.timezone || "America/Bogota"} onChange={(e) => updateCondition(idx, { timezone: e.target.value })} placeholder="Timezone" />
                      <input style={input} value={c.start_time || "08:00"} onChange={(e) => updateCondition(idx, { start_time: e.target.value })} placeholder="Inicio HH:MM" />
                      <input style={input} value={c.end_time || "20:00"} onChange={(e) => updateCondition(idx, { end_time: e.target.value })} placeholder="Fin HH:MM" />
                    </div>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {weekDays.map((d) => {
                        const has = Array.isArray(c.days) ? c.days.includes(d.key) : false;
                        return (
                          <button
                            key={d.key}
                            style={{ ...smallBtn, background: has ? "rgba(120,255,120,0.2)" : "transparent" }}
                            onClick={() => {
                              const days = Array.isArray(c.days) ? c.days : [];
                              if (has) updateCondition(idx, { days: days.filter((x) => x !== d.key) });
                              else updateCondition(idx, { days: [...days, d.key] });
                            }}
                          >
                            {d.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}

        {tab === "actions" ? (
          <div style={{ display: "grid", gap: 10 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8 }}>
              <select style={input} value={actionDraft} onChange={(e) => setActionDraft(e.target.value)}>
                {actionTypes.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
              </select>
              <button style={smallBtn} onClick={() => setActions((p) => [...p, blankAction(actionDraft)])}>Agregar</button>
            </div>

            {actions.map((a, idx) => (
              <div key={`${idx}-${a.type}`} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10, display: "grid", gap: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{idx + 1}. {a.type}</strong>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button style={smallBtn} onClick={() => moveItem("action", idx, -1)}>↑</button>
                    <button style={smallBtn} onClick={() => moveItem("action", idx, 1)}>↓</button>
                    <button style={dangerBtn} onClick={() => setActions((p) => p.filter((_, i) => i !== idx))}>Eliminar</button>
                  </div>
                </div>

                {a.type === "send_template" ? (
                  <select style={input} value={a.template_id || ""} onChange={(e) => updateAction(idx, { template_id: e.target.value })}>
                    <option value="">Plantilla</option>
                    {(templates || []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                ) : null}

                {a.type === "change_tag" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: 8 }}>
                    <select style={input} value={a.mode || "add"} onChange={(e) => updateAction(idx, { mode: e.target.value })}>
                      <option value="add">Agregar</option>
                      <option value="remove">Quitar</option>
                      <option value="set">Reemplazar</option>
                    </select>
                    <input style={input} placeholder="Etiqueta" value={a.tag || ""} onChange={(e) => updateAction(idx, { tag: e.target.value })} />
                  </div>
                ) : null}

                {a.type === "configure_conversation" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: 8 }}>
                    <select style={input} value={a.takeover || "keep"} onChange={(e) => updateAction(idx, { takeover: e.target.value })}>
                      <option value="keep">Takeover: sin cambio</option>
                      <option value="on">Takeover: ON</option>
                      <option value="off">Takeover: OFF</option>
                    </select>
                    <input style={input} placeholder="AI state (opcional)" value={a.ai_state || ""} onChange={(e) => updateAction(idx, { ai_state: e.target.value })} />
                  </div>
                ) : null}

                {a.type === "change_contact_status" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: 8 }}>
                    <select style={input} value={a.field || "customer_type"} onChange={(e) => updateAction(idx, { field: e.target.value })}>
                      <option value="customer_type">Estado contacto</option>
                      <option value="payment_status">Estado pago</option>
                    </select>
                    <input style={input} placeholder="Valor estado" value={a.status || ""} onChange={(e) => updateAction(idx, { status: e.target.value })} />
                  </div>
                ) : null}

                {a.type === "notify_admins" ? (
                  <div style={{ display: "grid", gap: 8 }}>
                    <input style={input} placeholder="Telefonos admin (coma)" value={a.phones || ""} onChange={(e) => updateAction(idx, { phones: e.target.value })} />
                    <textarea style={{ ...input, minHeight: 70 }} placeholder="Mensaje para admin" value={a.message || ""} onChange={(e) => updateAction(idx, { message: e.target.value })} />
                  </div>
                ) : null}

                {a.type === "extract_conversation_info" ? (
                  <input style={input} type="number" value={a.last_messages || 10} onChange={(e) => updateAction(idx, { last_messages: e.target.value })} />
                ) : null}

                {a.type === "schedule_message" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 180px", gap: 8 }}>
                    <select style={input} value={a.template_id || ""} onChange={(e) => updateAction(idx, { template_id: e.target.value })}>
                      <option value="">Plantilla</option>
                      {(templates || []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                    <input style={input} type="number" value={a.delay_minutes || 0} onChange={(e) => updateAction(idx, { delay_minutes: e.target.value })} placeholder="Delay minutos" />
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
