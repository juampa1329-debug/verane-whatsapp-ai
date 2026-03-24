import React, { useState } from "react";
import AIPanel from "./AIPanel";
import SecurityPanel from "./SecurityPanel";
import useViewport from "../hooks/useViewport";

const tabs = [
  { id: "ia", label: "IA" },
  { id: "security", label: "Seguridad" },
];

export default function SettingsPanel({ apiBase }) {
  const { isMobile } = useViewport();
  const [activeTab, setActiveTab] = useState("ia");

  return (
    <div className="settings-shell">
      <div className="settings-topbar">
        <div>
          <h2 className="settings-title">Ajustes</h2>
          <p className="settings-subtitle">
            Configura IA, seguridad y políticas de operación.
          </p>
        </div>

        <div
          className={`settings-tabs ${isMobile ? "is-mobile" : ""}`}
          role="tablist"
          aria-label="Pestañas de ajustes"
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`settings-tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="settings-tab-panel custom-scrollbar">
        {activeTab === "ia" ? (
          <AIPanel apiBase={apiBase} />
        ) : (
          <SecurityPanel apiBase={apiBase} />
        )}
      </div>
    </div>
  );
}
