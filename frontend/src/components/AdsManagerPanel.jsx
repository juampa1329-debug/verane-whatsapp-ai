import React, { useMemo, useState } from "react";
import useViewport from "../hooks/useViewport";

const box = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  background: "rgba(255,255,255,0.02)",
  padding: 12,
};

const chip = {
  padding: "8px 12px",
  borderRadius: 999,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 700,
};

const CHANNELS = [
  { id: "facebook", label: "Facebook" },
  { id: "instagram", label: "Instagram" },
  { id: "tiktok", label: "TikTok" },
];

const MODULES = [
  { id: "ads", label: "Campanas Ads" },
  { id: "comments", label: "Comentarios" },
  { id: "dm", label: "Mensajeria Directa" },
  { id: "automation", label: "IA Trafficker" },
  { id: "audit", label: "Auditoria" },
];

function ModuleIntro({ channel, moduleId }) {
  const text = useMemo(() => {
    if (moduleId === "ads") {
      return "Control de campanas publicitarias con aprobacion humana, presupuesto, objetivo, audiencias y reglas de seguridad.";
    }
    if (moduleId === "comments") {
      return "Bandeja para responder comentarios organicos y de anuncios con IA, sugerencias y aprobacion opcional.";
    }
    if (moduleId === "dm") {
      return "Bandeja de mensajes directos por red social con soporte de adjuntos, historial y handoff humano.";
    }
    if (moduleId === "automation") {
      return "Panel de instrucciones para IA trafficker: metas, limites de CPA/CPL, tests A/B y ventanas horarias.";
    }
    return "Trazabilidad de acciones IA y usuario: cambios de presupuesto, publicaciones, respuestas y alertas.";
  }, [moduleId]);

  return (
    <div style={box}>
      <h3 style={{ marginTop: 0, marginBottom: 8 }}>
        Esqueleto UI - {channel} - {MODULES.find((m) => m.id === moduleId)?.label}
      </h3>
      <p style={{ marginTop: 0, opacity: 0.86, fontSize: 13 }}>{text}</p>
      <div style={{ display: "grid", gap: 8 }}>
        <div style={{ fontSize: 12, opacity: 0.78 }}>Estado: UI creada, conexion API pendiente.</div>
        <div style={{ fontSize: 12, opacity: 0.78 }}>Permisos: lectura y escritura por token por canal.</div>
        <div style={{ fontSize: 12, opacity: 0.78 }}>Seguridad: acciones criticas con aprobacion y auditoria obligatoria.</div>
      </div>
    </div>
  );
}

export default function AdsManagerPanel() {
  const { isMobile } = useViewport();
  const [channel, setChannel] = useState("facebook");
  const [moduleId, setModuleId] = useState("ads");

  const cols = isMobile ? "1fr" : "1fr 1fr";

  return (
    <div
      className="placeholder-view custom-scrollbar"
      style={{ alignItems: "stretch", flexDirection: "column", justifyContent: "flex-start", width: "100%", minHeight: 0, overflowY: "auto", padding: 12 }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, gap: 8, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0 }}>Ads Manager</h2>
        <span style={{ fontSize: 12, opacity: 0.8 }}>Fase actual: Esqueleto UI</span>
      </div>

      <div style={{ ...box, marginBottom: 12 }}>
        <div style={{ fontSize: 12, opacity: 0.82, marginBottom: 10 }}>
          Modulo separado del CRM de WhatsApp: aqui solo control de Ads y atencion social en Facebook, Instagram y TikTok.
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
          {CHANNELS.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setChannel(c.id)}
              style={{
                ...chip,
                background: channel === c.id ? "rgba(52, 152, 219, 0.18)" : "transparent",
                borderColor: channel === c.id ? "rgba(52, 152, 219, 0.45)" : "rgba(255,255,255,0.18)",
              }}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {MODULES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setModuleId(m.id)}
              style={{
                ...chip,
                background: moduleId === m.id ? "rgba(46, 204, 113, 0.18)" : "transparent",
                borderColor: moduleId === m.id ? "rgba(46, 204, 113, 0.42)" : "rgba(255,255,255,0.18)",
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: cols, gap: 12 }}>
        <ModuleIntro channel={CHANNELS.find((c) => c.id === channel)?.label || channel} moduleId={moduleId} />
        <div style={box}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Checklist para siguiente sprint</h3>
          <div style={{ display: "grid", gap: 8, fontSize: 13 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" disabled />
              Conexion OAuth por red social
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" disabled />
              Webhooks de mensajes, comentarios y eventos ads
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" disabled />
              Politicas de aprobacion para acciones de IA
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" disabled />
              Trazabilidad en modulo de auditoria
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
