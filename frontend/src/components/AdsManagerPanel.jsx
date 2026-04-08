import React, { useMemo, useState } from "react";
import useViewport from "../hooks/useViewport";

const CHANNELS = [
  { id: "facebook", label: "Facebook" },
  { id: "instagram", label: "Instagram" },
  { id: "tiktok", label: "TikTok" },
];

const ADS_MODULES = [
  { id: "campaigns", label: "Campanas" },
  { id: "adsets", label: "Conjuntos" },
  { id: "ads", label: "Anuncios" },
  { id: "automation", label: "Automatizacion IA" },
  { id: "reports", label: "Reportes" },
];

const cardBase = {
  border: "1px solid rgba(255,255,255,0.14)",
  borderRadius: 12,
  background: "rgba(255,255,255,0.02)",
  padding: 12,
};

const chipBase = {
  border: "1px solid rgba(255,255,255,0.18)",
  background: "transparent",
  color: "inherit",
  borderRadius: 999,
  padding: "8px 12px",
  fontSize: 12,
  fontWeight: 700,
  cursor: "pointer",
};

function ModuleBody({ moduleId, channelLabel }) {
  if (moduleId === "campaigns") {
    return (
      <>
        <h3 style={{ marginTop: 0, marginBottom: 8 }}>Gestor de Campanas - {channelLabel}</h3>
        <p style={{ marginTop: 0, opacity: 0.82, fontSize: 13 }}>
          Este modulo queda dedicado solo a anuncios: objetivos, presupuesto, segmentacion, calendario y estado de publicacion.
        </p>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, opacity: 0.9 }}>
          <li>Crear y pausar campanas.</li>
          <li>Definir objetivos por conversion, trafico o mensajes.</li>
          <li>Controlar limites de gasto diario y total.</li>
        </ul>
      </>
    );
  }

  if (moduleId === "adsets") {
    return (
      <>
        <h3 style={{ marginTop: 0, marginBottom: 8 }}>Conjuntos de Anuncios - {channelLabel}</h3>
        <p style={{ marginTop: 0, opacity: 0.82, fontSize: 13 }}>
          Administracion de audiencias, ubicaciones, pujas y pruebas A/B a nivel conjunto.
        </p>
      </>
    );
  }

  if (moduleId === "ads") {
    return (
      <>
        <h3 style={{ marginTop: 0, marginBottom: 8 }}>Anuncios - {channelLabel}</h3>
        <p style={{ marginTop: 0, opacity: 0.82, fontSize: 13 }}>
          Creativos, copys, llamados a la accion y controles de publicacion por pieza publicitaria.
        </p>
      </>
    );
  }

  if (moduleId === "automation") {
    return (
      <>
        <h3 style={{ marginTop: 0, marginBottom: 8 }}>Automatizacion IA Trafficker</h3>
        <p style={{ marginTop: 0, opacity: 0.82, fontSize: 13 }}>
          Reglas de ajuste automatico para presupuesto, pause/scale y alertas bajo aprobacion humana.
        </p>
      </>
    );
  }

  return (
    <>
      <h3 style={{ marginTop: 0, marginBottom: 8 }}>Reportes de Ads</h3>
      <p style={{ marginTop: 0, opacity: 0.82, fontSize: 13 }}>
        Visualizacion de CPM, CTR, CPC, CPA, ROAS y comparativos por canal, campaña y anuncio.
      </p>
    </>
  );
}

export default function AdsManagerPanel() {
  const { isMobile } = useViewport();
  const [channel, setChannel] = useState("facebook");
  const [moduleId, setModuleId] = useState("campaigns");

  const channelLabel = useMemo(
    () => CHANNELS.find((c) => c.id === channel)?.label || "Facebook",
    [channel]
  );

  return (
    <div
      className="placeholder-view custom-scrollbar"
      style={{
        alignItems: "stretch",
        justifyContent: "flex-start",
        flexDirection: "column",
        width: "100%",
        minHeight: 0,
        overflowY: "auto",
        padding: 12,
        gap: 12,
      }}
    >
      <div style={cardBase}>
        <h2 style={{ margin: 0, marginBottom: 8 }}>Ads Manager</h2>
        <div style={{ fontSize: 12, opacity: 0.82 }}>
          Modulo exclusivo para anuncios. La mensajeria y comentarios ahora viven en Inbox.
        </div>
      </div>

      <div style={{ ...cardBase, display: "grid", gap: 10 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {CHANNELS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setChannel(item.id)}
              style={{
                ...chipBase,
                background: channel === item.id ? "rgba(52, 152, 219, 0.18)" : "transparent",
                borderColor: channel === item.id ? "rgba(52, 152, 219, 0.42)" : "rgba(255,255,255,0.18)",
              }}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {ADS_MODULES.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setModuleId(item.id)}
              style={{
                ...chipBase,
                background: moduleId === item.id ? "rgba(46, 204, 113, 0.18)" : "transparent",
                borderColor: moduleId === item.id ? "rgba(46, 204, 113, 0.42)" : "rgba(255,255,255,0.18)",
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
          gap: 12,
        }}
      >
        <div style={cardBase}>
          <ModuleBody moduleId={moduleId} channelLabel={channelLabel} />
        </div>

        <div style={cardBase}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Checklist Operativo</h3>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, opacity: 0.9 }}>
            <li>OAuth y permisos por red social.</li>
            <li>Sincronizacion de cuentas publicitarias.</li>
            <li>Acciones sensibles con aprobacion humana.</li>
            <li>Auditoria completa de cambios en campanas.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

