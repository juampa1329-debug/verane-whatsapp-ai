import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import SettingsPanel from "./components/SettingsPanel";
import DashboardPanel from "./components/DashboardPanel";
import CustomersPanel from "./components/CustomersPanel";
import MarketingPanel from "./components/MarketingPanel";
import MassMessagingPanel from "./components/MassMessagingPanel";
import AdsManagerPanel from "./components/AdsManagerPanel";
import LabelsPanel from "./components/LabelsPanel";
import EmojiPickerButton from "./components/EmojiPickerButton";
import InboxCommentsPanel from "./components/InboxCommentsPanel";
import useViewport from "./hooks/useViewport";


// --- CONFIGURACION ---
const API_BASE = import.meta.env.VITE_API_BASE || "https://backend.perfumesverane.com";

// --- ICONOS SVG (Nativos) ---
const IconMessage = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>;
const IconUsers = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>;
const IconZap = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>;
const IconSettings = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>;
const IconChart = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></svg>;
const IconMegaphone = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 11v2a2 2 0 0 0 2 2h2l3 6h2l-1.8-6.2L19 11V5l-8.8 3H5a2 2 0 0 0-2 2v1z" /><line x1="19" y1="5" x2="22" y2="4" /><line x1="19" y1="11" x2="22" y2="12" /></svg>;
const IconSearch = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>;
const IconSend = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>;
const IconBot = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="10" rx="2" /><circle cx="12" cy="5" r="2" /><path d="M12 7v4" /><line x1="8" y1="16" x2="8" y2="16" /><line x1="16" y1="16" x2="16" y2="16" /></svg>;
const IconUser = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>;
const IconImage = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>;
const IconTag = () => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" /><line x1="7" y1="7" x2="7.01" y2="7" /></svg>;
const IconTagNav = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" /><line x1="7" y1="7" x2="7.01" y2="7" /></svg>;
const IconBag = () => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><line x1="3" y1="6" x2="21" y2="6" /><path d="M16 10a4 4 0 0 1-8 0" /></svg>;
const IconPaperclip = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21.44 11.05l-8.49 8.49a5 5 0 0 1-7.07-7.07l8.49-8.49a3.5 3.5 0 0 1 4.95 4.95l-8.5 8.5a2 2 0 0 1-2.83-2.83l8.49-8.48" />
  </svg>
);
const IconMic = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 1 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);
const IconVideo = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="6" width="15" height="12" rx="2" />
    <path d="M17 10l5-3v10l-5-3z" />
  </svg>
);
const IconFile = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
  </svg>
);
const IconAudio = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M15.5 8.5a5 5 0 0 1 0 7" />
    <path d="M18.5 6a9 9 0 0 1 0 12" />
  </svg>
);
const IconAudioMessage = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 10v4" />
    <path d="M11 7v10" />
    <path d="M15 9v6" />
    <path d="M19 6v12" />
    <path d="M3 9v6" />
  </svg>
);

function fmtDateTime(s) {
  if (!s) return '';
  try { return new Date(s).toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' }); }
  catch { return s; }
}

function formatBytes(bytes) {
  const n = Number(bytes);
  if (!Number.isFinite(n) || n <= 0) return "";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  const out = i === 0 ? String(Math.round(v)) : v.toFixed(v >= 10 ? 0 : 1);
  return `${out} ${units[i]}`;
}

function formatDur(sec) {
  const n = Number(sec);
  if (!Number.isFinite(n) || n <= 0) return "";
  const m = Math.floor(n / 60);
  const s = n % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function waTicks(m) {
  if (!m || m.direction !== "out") return "";
  const st = (m.wa_status || "").toLowerCase();
  if (st === "failed") return "ERR";
  if (st === "read") return "READ";
  if (st === "delivered") return "DEL";
  if (st === "sent") return "SENT";
  return "SENT";
}

function waTickClass(m) {
  const st = (m.wa_status || "").toLowerCase();
  if (st === "read") return "wa-read";
  if (st === "delivered") return "wa-delivered";
  if (st === "failed") return "wa-failed";
  return "wa-sent";
}

function mediaProxyUrl(mediaId) {
  if (!mediaId) return "";
  return `${API_BASE}/api/media/proxy/${encodeURIComponent(mediaId)}`;
}

function normalizeWaveBars(raw, bars = 48) {
  const nBars = Math.max(8, Math.min(Number(bars) || 48, 96));
  const src = Array.isArray(raw) ? raw.filter((x) => Number.isFinite(Number(x))) : [];
  if (src.length === 0) return Array.from({ length: nBars }, () => 0.14);
  if (src.length === nBars) return src.map((v) => Math.max(0.06, Math.min(1, Number(v))));

  const out = [];
  for (let i = 0; i < nBars; i++) {
    const start = Math.floor((i * src.length) / nBars);
    const end = Math.max(start + 1, Math.floor(((i + 1) * src.length) / nBars));
    let maxVal = 0;
    for (let j = start; j < end; j++) {
      const v = Number(src[j] || 0);
      if (v > maxVal) maxVal = v;
    }
    out.push(Math.max(0.06, Math.min(1, maxVal)));
  }
  return out;
}

function defaultWaveBars(seed, bars = 48) {
  const text = String(seed || "wave");
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
  }
  const out = [];
  for (let i = 0; i < bars; i++) {
    h = (h * 1664525 + 1013904223) >>> 0;
    const base = ((h % 1000) / 1000) * 0.75 + 0.12;
    out.push(Math.max(0.08, Math.min(1, base)));
  }
  return out;
}

function waveformFromAudioBuffer(audioBuffer, bars = 42) {
  try {
    const ch = audioBuffer?.numberOfChannels ? audioBuffer.getChannelData(0) : null;
    if (!ch || !ch.length) return defaultWaveBars("audio", bars);
    const blockSize = Math.max(1, Math.floor(ch.length / bars));
    const peaks = [];
    for (let i = 0; i < bars; i++) {
      const start = i * blockSize;
      const end = Math.min(ch.length, start + blockSize);
      let peak = 0;
      for (let j = start; j < end; j++) {
        const amp = Math.abs(ch[j] || 0);
        if (amp > peak) peak = amp;
      }
      peaks.push(Math.max(0.06, Math.min(1, peak)));
    }
    return normalizeWaveBars(peaks, bars);
  } catch {
    return defaultWaveBars("audio", bars);
  }
}

// --- Inbox helpers (nombre CRM) ---
function displayName(c) {
  const fn = (c?.first_name || "").trim();
  const ln = (c?.last_name || "").trim();
  const full = `${fn} ${ln}`.trim();
  return full || (c?.phone || "");
}

function initialsFromConversation(c) {
  const name = displayName(c);
  if (!name) return "*";
  if (/^\d+$/.test(name)) return name.slice(-2);
  const parts = name.split(" ").filter(Boolean);
  const a = (parts[0] || "").slice(0, 1).toUpperCase();
  const b = (parts[1] || "").slice(0, 1).toUpperCase();
  return (a + b).trim() || "*";
}

// --- 1. Barra de Navegacion Lateral ---
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

function normalizeInboxChannel(raw, fallback = "all") {
  const token = String(raw || "").trim().toLowerCase();
  if (["all", "whatsapp", "facebook", "instagram", "tiktok"].includes(token)) return token;
  return fallback;
}

const inboxChannelMeta = {
  all: { label: "Todos", short: "ALL" },
  whatsapp: { label: "WhatsApp", short: "WA" },
  facebook: { label: "Facebook", short: "FB" },
  instagram: { label: "Instagram", short: "IG" },
  tiktok: { label: "TikTok", short: "TT" },
};

function getInboxChannelMeta(raw, fallback = "all") {
  const channel = normalizeInboxChannel(raw, fallback);
  return inboxChannelMeta[channel] || inboxChannelMeta.all;
}

const MainNav = ({ activeTab, onChangeTab, isMobile }) => {
  const navItems = [
    { id: 'dashboard', icon: IconChart, label: 'Dashboard' },
    { id: 'inbox', icon: IconMessage, label: 'Inbox' },
    { id: 'crm', icon: IconUsers, label: 'Clientes' },
    { id: 'labels', icon: IconTagNav, label: 'Etiquetas' },
    { id: 'marketing', icon: IconZap, label: 'Campanas CRM' },
    { id: 'mass_messaging', icon: IconMegaphone, label: 'Mensajeria masiva' },
    { id: 'ads_manager', icon: IconChart, label: 'Ads Manager' },
    { id: 'settings', icon: IconSettings, label: 'Ajustes' },
  ];

  return (
    <div className={`main-nav ${isMobile ? "is-mobile" : ""}`}>
      <div className="nav-logo">V.</div>
      <nav className="nav-items">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onChangeTab(item.id)}
            className={`nav-btn ${activeTab === item.id ? 'active' : ''}`}
          >
            <item.icon />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="nav-footer">
        <div className="avatar-placeholder">A</div>
      </div>
    </div>
  );
};

// --- 2. Lista de Conversaciones ---
const ChatList = ({
  conversations,
  selectedPhone,
  onSelect,
  channel,
  setChannel,
  q,
  setQ,
  filterTakeover,
  setFilterTakeover,
  filterUnread,
  setFilterUnread,
  filterTags,
  setFilterTags,
  onClearFilters,
  loadError,
}) => {
  const channelTabs = [
    { id: "all", label: "Todos" },
    { id: "whatsapp", label: "WhatsApp" },
    { id: "facebook", label: "Facebook" },
    { id: "instagram", label: "Instagram" },
    { id: "tiktok", label: "TikTok" },
  ];
  const activeChannelLabel = channelTabs.find((tab) => tab.id === normalizeInboxChannel(channel))?.label || "Todos";

  return (
    <div className="chat-list-panel">
      <div className="chat-list-header">
        <div className="header-row">
          <h2>Inbox</h2>
          <span className="badge">{activeChannelLabel}</span>
        </div>

        <div className="inbox-channel-tabs">
          {channelTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`inbox-channel-tab ${channel === tab.id ? "active" : ""}`}
              onClick={() => setChannel(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="search-box">
          <div className="search-icon"><IconSearch /></div>
          <input
            placeholder="Buscar (telefono o preview)..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>

        {loadError ? (
          <div className="inbox-load-error">
            {loadError}
          </div>
        ) : null}

        {/* Filtros */}
        <div className="filter-row" style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
          <select value={filterTakeover} onChange={(e) => setFilterTakeover(e.target.value)} style={{ padding: "8px 10px", borderRadius: 10 }}>
            <option value="all">Takeover: Todos</option>
            <option value="on">Takeover: ON</option>
            <option value="off">Takeover: OFF</option>
          </select>

          <select value={filterUnread} onChange={(e) => setFilterUnread(e.target.value)} style={{ padding: "8px 10px", borderRadius: 10 }}>
            <option value="all">Unread: Todos</option>
            <option value="yes">Unread: Si</option>
            <option value="no">Unread: No</option>
          </select>

          <input
            value={filterTags}
            onChange={(e) => setFilterTags(e.target.value)}
            placeholder="Tags (ej: vip,pago pendiente)"
            style={{ padding: "8px 10px", borderRadius: 10, flex: "1 1 220px" }}
          />

          <button
            onClick={onClearFilters}
            style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.15)", background: "transparent", cursor: "pointer" }}
            title="Limpiar filtros"
          >
            Limpiar
          </button>
        </div>
      </div>

      <div className="chat-list-items custom-scrollbar">
        {(conversations || []).map(c => {
          const unread = !!c.has_unread;
          const unreadCount = Number.isFinite(Number(c.unread_count)) ? Number(c.unread_count) : 0;
          const rowChannel = normalizeInboxChannel(c.last_channel, "whatsapp");
          const rowChannelMeta = getInboxChannelMeta(rowChannel, "whatsapp");
          const showChannelChip = normalizeInboxChannel(channel, "all") === "all";

          return (
            <button
              key={c.phone}
              onClick={() => onSelect(c.phone)}
              className={`chat-item ${selectedPhone === c.phone ? 'selected' : ''} ${unread ? 'unread' : ''}`}
            >
              <div className="chat-item-top">
                <div className="chat-title-wrap" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="chat-phone">{displayName(c)}</span>
                  {showChannelChip ? (
                    <span
                      className={`channel-chip channel-${rowChannel}`}
                      title={`Canal: ${rowChannelMeta.label}`}
                    >
                      {rowChannelMeta.short}
                    </span>
                  ) : null}

                  {unread && (
                    <>
                      <span className="unread-dot" title="Nuevo mensaje" />
                      {unreadCount > 0 && (
                        <span
                          title={`No leidos: ${unreadCount}`}
                          style={{
                            fontSize: 11,
                            padding: "2px 8px",
                            borderRadius: 999,
                            border: "1px solid rgba(255,255,255,0.15)",
                            opacity: 0.9,
                          }}
                        >
                          {unreadCount}
                        </span>
                      )}
                    </>
                  )}
                </div>
                <span className="chat-date">{fmtDateTime(c.updated_at).split(',')[0]}</span>
              </div>

              <div className="chat-tags">
                <span className={`pill ${c.takeover ? 'pill-human' : 'pill-bot'}`}>
                  {c.takeover ? 'Humano' : 'Bot'}
                </span>
              </div>

              <p className="chat-preview">
                {c.text || ""}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};

// --- 3. Panel de CRM (Datos del cliente) ---
const CustomerCardCRM = ({ phone, takeover, isMobile = false, onBack = null }) => {
  const [form, setForm] = useState({
    first_name: "", last_name: "", city: "", customer_type: "",
    interests: "", tags: "", notes: ""
  });
  const [memory, setMemory] = useState({
    memory_summary: "",
    intent_current: "",
    intent_stage: "",
    payment_status: "",
    payment_reference: "",
  });
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [rmkCatalog, setRmkCatalog] = useState([]);
  const [rmkEnrollments, setRmkEnrollments] = useState([]);
  const [rmkFlowId, setRmkFlowId] = useState("");
  const [rmkStage, setRmkStage] = useState("");
  const [rmkSaving, setRmkSaving] = useState(false);
  const [rmkStatus, setRmkStatus] = useState("");
  const [rmkSendNow, setRmkSendNow] = useState(true);
  const [labelCatalog, setLabelCatalog] = useState([]);

  const currentTagTokens = (form.tags || "")
    .split(",")
    .map((x) => String(x || "").trim().toLowerCase())
    .filter(Boolean);
  const currentTagSet = new Set(currentTagTokens);

  const selectedRmkFlow = (rmkCatalog || []).find((f) => String(f.id) === String(rmkFlowId)) || null;
  const selectedEnrollment = (rmkEnrollments || []).find((e) => String(e.flow_id) === String(rmkFlowId)) || null;

  const stageOptions = (() => {
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
  })();

  const loadRemarketingCatalog = async () => {
    try {
      const r = await fetch(`${API_BASE}/api/remarketing/stages/catalog`);
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo cargar catalogo de remarketing");
      const flows = Array.isArray(d?.flows) ? d.flows : [];
      setRmkCatalog(flows);
      return flows;
    } catch (e) {
      console.error(e);
      return [];
    }
  };

  const loadLabelCatalog = async () => {
    try {
      const r = await fetch(`${API_BASE}/api/labels?active=yes&limit=500`);
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo cargar etiquetas");
      setLabelCatalog(Array.isArray(d?.labels) ? d.labels : []);
    } catch (e) {
      console.error(e);
      setLabelCatalog([]);
    }
  };

  const loadRemarketingForPhone = async (targetPhone) => {
    if (!targetPhone) {
      setRmkEnrollments([]);
      return;
    }
    try {
      const r = await fetch(`${API_BASE}/api/remarketing/contacts/${encodeURIComponent(targetPhone)}`);
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo cargar estado de remarketing");
      setRmkEnrollments(Array.isArray(d?.enrollments) ? d.enrollments : []);
    } catch (e) {
      console.error(e);
    }
  };

  const load = async () => {
    if (!phone) return;
    try {
      const r = await fetch(`${API_BASE}/api/crm/${encodeURIComponent(phone)}`);
      const data = await r.json();
      setForm({
        first_name: data.first_name || "",
        last_name: data.last_name || "",
        city: data.city || "",
        customer_type: data.customer_type || "",
        interests: data.interests || "",
        tags: data.tags || "",
        notes: data.notes || "",
      });
      setMemory({
        memory_summary: data.memory_summary || "",
        intent_current: data.intent_current || "",
        intent_stage: data.intent_stage || "",
        payment_status: data.payment_status || "",
        payment_reference: data.payment_reference || "",
      });
      setDirty(false);
      setStatus("");
    } catch (e) { console.error(e); }
  };

  const applyRemarketingStage = async () => {
    if (!phone || !rmkFlowId || !rmkStage) return;
    setRmkSaving(true);
    setRmkStatus("");
    try {
      const r = await fetch(`${API_BASE}/api/remarketing/stage/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone,
          flow_id: Number(rmkFlowId),
          stage: rmkStage,
          send_now: !!rmkSendNow,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "No se pudo asignar etapa");
      setRmkStatus("Etapa actualizada");
      await Promise.all([load(), loadRemarketingForPhone(phone)]);
      setTimeout(() => setRmkStatus(""), 2500);
    } catch (e) {
      setRmkStatus(String(e.message || e));
    } finally {
      setRmkSaving(false);
    }
  };

  useEffect(() => {
    loadRemarketingCatalog();
    loadLabelCatalog();
  }, []);

  useEffect(() => {
    load();
    loadRemarketingForPhone(phone);
  }, [phone]);

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

  useEffect(() => {
    if (rmkFlowId) return;
    if (rmkEnrollments[0]?.flow_id) {
      setRmkFlowId(String(rmkEnrollments[0].flow_id));
      return;
    }
    if (rmkCatalog[0]?.id) {
      setRmkFlowId(String(rmkCatalog[0].id));
    }
  }, [rmkCatalog, rmkEnrollments, rmkFlowId]);

  const save = async () => {
    if (!phone) return;
    setSaving(true);
    setStatus("");
    try {
      const r = await fetch(`${API_BASE}/api/crm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, ...form }),
      });
      if (!r.ok) throw new Error("Error");
      setDirty(false);
      setStatus("Guardado OK");
    } catch {
      setStatus("Error al guardar");
    } finally {
      setSaving(false);
      setTimeout(() => setStatus(""), 2500);
    }
  };

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    setDirty(true);
  };

  const toggleLabelTag = (labelKey) => {
    const token = String(labelKey || "").trim().toLowerCase();
    if (!token) return;
    const next = [...currentTagTokens];
    const idx = next.findIndex((x) => x === token);
    if (idx >= 0) next.splice(idx, 1);
    else next.push(token);
    handleChange("tags", next.join(","));
  };

  if (!phone) return <div className="crm-panel empty" />;

  return (
    <div className={`crm-panel ${isMobile ? "crm-panel-mobile" : ""}`}>
      <div className="crm-header">
        <div className="crm-header-row">
          {isMobile && (
            <button type="button" className="mobile-nav-btn" onClick={onBack}>
              Volver
            </button>
          )}
          <h3><span className="icon-green"><IconUsers /></span> CRM - Cliente</h3>
        </div>
      </div>

      <div className="crm-content custom-scrollbar">
        <div className="crm-card-info">
          <div className="crm-row">
            <span className="crm-label">Telefono</span>
            <span className="crm-value mono">{phone}</span>
          </div>
          <div className="crm-row">
            <span className="crm-label">Modo</span>
            <span className={`pill ${takeover ? "pill-human" : "pill-bot"}`}>
              {takeover ? "Humano" : "Bot"}
            </span>
          </div>
        </div>

        {(memory.memory_summary || memory.intent_current || memory.payment_status) && (
          <>
            <div className="crm-card-info">
              <div className="crm-row">
                <span className="crm-label">Intento IA</span>
                <span className="crm-value mono">{memory.intent_current || "-"}</span>
              </div>
              <div className="crm-row">
                <span className="crm-label">Etapa</span>
                <span className="crm-value mono">{memory.intent_stage || "-"}</span>
              </div>
              <div className="crm-row">
                <span className="crm-label">Pago</span>
                <span className="crm-value mono">{memory.payment_status || memory.payment_reference || "-"}</span>
              </div>
            </div>

            <div className="form-group">
              <label>Resumen IA / Memoria</label>
              <textarea
                className="notes-area"
                value={memory.memory_summary}
                readOnly
                placeholder="La IA ira recapitulando aqui intencion, perfumes consultados, estado de pago y contexto del cliente."
              />
            </div>

            <div className="separator" />
          </>
        )}

        <div className="form-group-row">
          <div className="form-group">
            <label>Nombre</label>
            <input
              value={form.first_name}
              onChange={e => handleChange('first_name', e.target.value)}
              placeholder="Ej: Juan"
            />
          </div>
          <div className="form-group">
            <label>Apellido</label>
            <input
              value={form.last_name}
              onChange={e => handleChange('last_name', e.target.value)}
              placeholder="Ej: Perez"
            />
          </div>
        </div>

        <div className="form-group-row">
          <div className="form-group">
            <label>Ciudad</label>
            <input
              value={form.city}
              onChange={e => handleChange('city', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Tipo</label>
            <select
              value={form.customer_type}
              onChange={e => handleChange('customer_type', e.target.value)}
            >
              <option value="">Sin definir</option>
              <option value="minorista">Minorista</option>
              <option value="mayorista">Mayorista</option>
            </select>
          </div>
        </div>

        <div className="separator" />

        <div className="form-group">
          <label>Intereses</label>
          <input
            value={form.interests}
            onChange={e => handleChange('interests', e.target.value)}
            placeholder="dulces, frescos..."
          />
        </div>

        <div className="form-group">
          <label className="flex-label"><IconTag /> Etiquetas</label>
          <input
            value={form.tags}
            onChange={e => handleChange('tags', e.target.value)}
            placeholder="Separadas por comas..."
          />
          {labelCatalog.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
              {labelCatalog.map((label) => {
                const token = String(label.label_key || "").trim().toLowerCase();
                const active = currentTagSet.has(token);
                const color = String(label.color || "#64748b");
                return (
                  <button
                    type="button"
                    key={label.id}
                    onClick={() => toggleLabelTag(token)}
                    style={{
                      border: `1px solid ${active ? color : "rgba(255,255,255,0.16)"}`,
                      background: active ? `${color}33` : "transparent",
                      color: "#fff",
                      borderRadius: 999,
                      padding: "4px 9px",
                      fontSize: 11,
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 5,
                    }}
                    title={label.description || label.name || token}
                  >
                    <span>{label.icon || "tag"}</span>
                    <span>{label.name || token}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="crm-card-info" style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", marginBottom: 10 }}>
            Remarketing por etapas
          </div>
          {rmkCatalog.length === 0 ? (
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>No hay flows activos de remarketing.</div>
          ) : (
            <>
              <div className="form-group-row" style={{ marginBottom: 8 }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Flow</label>
                  <select value={rmkFlowId} onChange={e => setRmkFlowId(e.target.value)}>
                    <option value="">Selecciona flow</option>
                    {rmkCatalog.map((f) => (
                      <option key={f.id} value={String(f.id)}>
                        {f.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Etapa</label>
                  <select value={rmkStage} onChange={e => setRmkStage(e.target.value)}>
                    <option value="">Selecciona etapa</option>
                    {stageOptions.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button
                  type="button"
                  onClick={applyRemarketingStage}
                  disabled={!rmkFlowId || !rmkStage || rmkSaving}
                  style={{
                    border: "1px solid rgba(52, 152, 219, 0.35)",
                    background: "rgba(52, 152, 219, 0.18)",
                    color: "#7ec8ff",
                    borderRadius: 10,
                    padding: "8px 12px",
                    cursor: !rmkFlowId || !rmkStage || rmkSaving ? "not-allowed" : "pointer",
                    opacity: !rmkFlowId || !rmkStage || rmkSaving ? 0.6 : 1,
                    fontWeight: 700,
                  }}
                >
                  {rmkSaving ? "Aplicando..." : "Aplicar etapa"}
                </button>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  Actual: {selectedEnrollment ? `${selectedEnrollment.flow_name || "Flow"} - ${selectedEnrollment.state} - ${selectedEnrollment.current_stage_name || defaultStageName(selectedEnrollment.current_step_order)} (paso ${selectedEnrollment.current_step_order || "-"})` : "Sin enrollment"}
                  {String(selectedEnrollment?.state || "").toLowerCase() === "hold" && selectedEnrollment?.meta_json?.hold_reason
                    ? ` | motivo hold: ${selectedEnrollment.meta_json.hold_reason}`
                    : ""}
                </div>
              </div>
              <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
                <input type="checkbox" checked={!!rmkSendNow} onChange={e => setRmkSendNow(e.target.checked)} />
                Enviar al instante al mover a etapa activa
              </label>
              {rmkStatus && (
                <div className="status-msg" style={{ textAlign: "left", marginTop: 8 }}>
                  {rmkStatus}
                </div>
              )}
            </>
          )}
        </div>

        <div className="separator" />

        <div className="form-group">
          <label className="flex-label"><IconBag /> Notas Internas</label>
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 6 }}>
            <EmojiPickerButton
              onSelect={(emoji) => handleChange("notes", `${form.notes || ""}${emoji}`)}
              title="Agregar emoji a notas"
            />
          </div>
          <textarea
            className="notes-area"
            value={form.notes}
            onChange={e => handleChange('notes', e.target.value)}
            placeholder="Escribe notas aqui..."
          />
        </div>
      </div>

      <div className="crm-footer">
        <button
          onClick={save}
          disabled={!dirty || saving}
          className={`btn-save ${dirty ? 'dirty' : ''}`}
        >
          {saving ? 'Guardando...' : dirty ? 'Guardar CRM' : 'Guardado'}
        </button>
        {status && <div className="status-msg">{status}</div>}
      </div>
    </div>
  );
};

// --- COMPONENTE PRINCIPAL ---
export default function App() {
  const [activeTab, setActiveTab] = useState('inbox');
  const [inboxViewMode, setInboxViewMode] = useState("messages"); // messages|comments
  const [conversations, setConversations] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [inboxMobileView, setInboxMobileView] = useState("list");
  const { isMobile, isTablet } = useViewport();

  // filtros inbox
  const [q, setQ] = useState(""); // server-side search
  const [filterTakeover, setFilterTakeover] = useState("all"); // all|on|off
  const [filterUnread, setFilterUnread] = useState("all");     // all|yes|no
  const [filterTags, setFilterTags] = useState("");            // "vip,pago pendiente"
  const [inboxChannel, setInboxChannel] = useState("all");
  const [conversationsError, setConversationsError] = useState("");

  useEffect(() => {
    const normalized = normalizeInboxChannel(inboxChannel);
    if (normalized !== inboxChannel) setInboxChannel(normalized);
  }, [inboxChannel]);

  // Attachments
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [attachment, setAttachment] = useState(null);

  const fileInputRef = useRef(null);
  const [filePickKind, setFilePickKind] = useState("image"); // image|video|audio|document

  // Productos (WooCommerce)
  const [showProductModal, setShowProductModal] = useState(false);
  const [prodQ, setProdQ] = useState("");
  const [products, setProducts] = useState([]);
  const [prodLoading, setProdLoading] = useState(false);
  const [prodError, setProdError] = useState("");
  const [sendingProductId, setSendingProductId] = useState(null);

  // Audio recorder (WhatsApp-style)
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [recordWaveBars, setRecordWaveBars] = useState(Array.from({ length: 22 }, () => 0.12));
  const [audioWaveforms, setAudioWaveforms] = useState({});
  const recorderRef = useRef(null);
  const recChunksRef = useRef([]);
  const recTimerRef = useRef(null);
  const recordLevelsRef = useRef([]);
  const audioWaveformsRef = useRef({});
  const waveLoadingRef = useRef(new Set());
  const waveAnimRef = useRef(null);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);

  const bottomRef = useRef(null);
  const messagesRef = useRef(null);
  const userNearBottomRef = useRef(true);

  const prevConversationsRef = useRef(new Map());
  const didFirstLoadRef = useRef(false);

  const isNearBottom = (el, threshold = 120) => {
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  };

  // Ding (WebAudio) - sin archivos
  const playDing = async () => {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = "sine";
      o.frequency.value = 880;

      g.gain.setValueAtTime(0.001, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.12, ctx.currentTime + 0.01);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);

      o.connect(g);
      g.connect(ctx.destination);
      o.start();
      o.stop(ctx.currentTime + 0.2);

      setTimeout(() => ctx.close?.(), 350);
    } catch { }
  };

  const buildConversationsUrl = (forcedChannel = null) => {
    const params = new URLSearchParams();
    params.set("search", q || "");
    params.set("takeover", filterTakeover || "all");
    params.set("unread", filterUnread || "all");
    params.set("channel", normalizeInboxChannel(forcedChannel ?? inboxChannel));
    if ((filterTags || "").trim()) params.set("tags", filterTags.trim());
    return `${API_BASE}/api/conversations?${params.toString()}`;
  };

  const loadConversations = async () => {
    try {
      const activeChannel = normalizeInboxChannel(inboxChannel);
      const url = buildConversationsUrl(activeChannel);
      const r = await fetch(url);
      if (!r.ok) {
        if (r.status === 503) {
          throw new Error("backend_unavailable_503");
        }
        throw new Error(`conversations_http_${r.status}`);
      }
      const data = await r.json();
      let list = Array.isArray(data?.conversations) ? data.conversations : [];

      // Fallback defensivo: si el filtro de canal no trae datos, probamos "all".
      if (!list.length && activeChannel !== "all") {
        const fallback = await fetch(buildConversationsUrl("all"));
        if (fallback.ok) {
          const fallbackData = await fallback.json();
          const fallbackList = Array.isArray(fallbackData?.conversations) ? fallbackData.conversations : [];
          if (fallbackList.length) {
            list = fallbackList;
            setInboxChannel("all");
          }
        }
      }

      // detectar nuevos mensajes (updated_at cambio)
      if (didFirstLoadRef.current) {
        const prev = prevConversationsRef.current;
        for (const c of list) {
          const prevTs = prev.get(c.phone) || 0;
          const curTs = c.updated_at ? new Date(c.updated_at).getTime() : 0;

          // si subio y NO estas en ese chat -> ding
          if (curTs && curTs > prevTs && c.phone !== selectedPhone) {
            await playDing();
            break;
          }
        }
      } else {
        didFirstLoadRef.current = true;
      }

      // actualizar prev map
      const nextMap = new Map();
      for (const c of list) {
        const curTs = c.updated_at ? new Date(c.updated_at).getTime() : 0;
        nextMap.set(c.phone, curTs);
      }
      prevConversationsRef.current = nextMap;

      setConversations(list);
      setConversationsError("");
    } catch (e) {
      console.error("Error cargando conversaciones", e);
      const token = String(e?.message || e || "").toLowerCase();
      if (token.includes("backend_unavailable_503")) {
        setConversationsError("Backend no disponible (503). Verifica el despliegue del API en Coolify.");
      } else if (token.includes("failed to fetch")) {
        setConversationsError("No se pudo conectar con el backend. Revisa dominio, SSL y CORS.");
      } else {
        setConversationsError("Error cargando conversaciones. Revisa logs del backend.");
      }
    }
  };

  const scrollToBottom = (smooth = false) => {
    requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "auto" });
    });
  };

  const loadMessages = async (phone) => {
    if (!phone) return;
    try {
      const activeChannel = normalizeInboxChannel(inboxChannel);
      const r = await fetch(
        `${API_BASE}/api/conversations/${encodeURIComponent(phone)}/messages?channel=${encodeURIComponent(activeChannel)}`
      );
      const data = await r.json();
      setMessages(data.messages || []);
      if (userNearBottomRef.current) scrollToBottom(false);
    } catch (e) { console.error(e); }
  };

  const markRead = async (phone) => {
    if (!phone) return;
    try {
      await fetch(`${API_BASE}/api/conversations/${encodeURIComponent(phone)}/read`, { method: "POST" });
    } catch { }
  };

  const selectChat = async (phone) => {
    setSelectedPhone(phone);
    if (isMobile) setInboxMobileView("chat");
    await markRead(phone);
    // recargar para que el badge de unread se quite en el inbox (segun last_read_at)
    loadConversations();
  };

  const loadWCProducts = async (search = "") => {
    setProdLoading(true);
    setProdError("");
    try {
      const url = `${API_BASE}/api/wc/products?q=${encodeURIComponent(search)}&page=1&per_page=12`;
      const r = await fetch(url);
      if (!r.ok) throw new Error(`Woo products failed: ${r.status}`);
      const data = await r.json();
      setProducts(data.products || []);
    } catch (e) {
      console.error(e);
      setProdError("No se pudo cargar el catalogo (WooCommerce).");
      setProducts([]);
    } finally {
      setProdLoading(false);
    }
  };

  const sendWCProduct = async (product) => {
    if (!selectedPhone) return;
    if (sendingProductId === product.id) return;

    setSendingProductId(product.id);

    try {
      const r = await fetch(`${API_BASE}/api/wc/send-product`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: selectedPhone,
          product_id: product.id,
          caption: ""
        }),
      });

      if (!r.ok) {
        const t = await r.text();
        throw new Error(`send-product failed ${r.status}: ${t}`);
      }

      const out = await r.json();
      if (out && out.sent === false) {
        console.error("WhatsApp send failed:", out);
        alert("Se guardo en la plataforma, pero WhatsApp NO lo envio. Revisa consola/network.");
        return;
      }

      await loadMessages(selectedPhone);
      await loadConversations();

      setShowProductModal(false);
      setProdQ("");
      setProducts([]);
    } catch (e) {
      console.error(e);
      alert("Error enviando producto por WhatsApp");
    } finally {
      setSendingProductId(null);
    }
  };

  const sendMessage = async () => {
    if (!selectedPhone) return;

    const hasText = !!text.trim();
    const hasAttachment = !!attachment;
    if (!hasText && !hasAttachment) return;

    const resolveOutboundChannel = () => {
      const current = normalizeInboxChannel(inboxChannel, "all");
      if (current !== "all") return current;
      const conv = (conversations || []).find((c) => c.phone === selectedPhone);
      const last = normalizeInboxChannel(conv?.last_channel, "");
      return last || "whatsapp";
    };
    const outboundChannel = resolveOutboundChannel();

    let payload = {
      phone: selectedPhone,
      channel: outboundChannel,
      direction: "out",
      msg_type: "text",
      text: text.trim()
    };

    if (hasAttachment && attachment.kind === "media") {
      payload = {
        phone: selectedPhone,
        channel: outboundChannel,
        direction: "out",
        msg_type: attachment.msg_type,
        text: "",
        media_id: attachment.media_id,
        media_caption: text.trim() || "",
        mime_type: attachment.mime_type || null,
        file_name: attachment.filename || null,
        file_size: attachment.file_size || null,
        duration_sec: attachment.duration_sec || null,
      };
    }

    if (hasAttachment && attachment.kind === "product") {
      payload = {
        phone: selectedPhone,
        channel: outboundChannel,
        direction: "out",
        msg_type: "product",
        text: attachment.text || "",
        featured_image: attachment.featured_image || null,
        real_image: attachment.real_image || null,
        permalink: attachment.permalink || null,
      };
    }

    try {
      const r = await fetch(`${API_BASE}/api/messages/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!r.ok) throw new Error("No se pudo enviar/guardar el mensaje");

      await loadMessages(selectedPhone);
      setText("");
      setAttachment(null);
      setShowAttachMenu(false);
      loadConversations();
    } catch (e) {
      console.error(e);
      alert("Error enviando mensaje");
    }
  };

  const fmtTimer = (sec) => {
    const m = String(Math.floor(sec / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    return `${m}:${s}`;
  };

  const stopWaveMonitor = () => {
    try {
      if (waveAnimRef.current) {
        cancelAnimationFrame(waveAnimRef.current);
        waveAnimRef.current = null;
      }
      analyserRef.current = null;
      if (audioCtxRef.current) {
        audioCtxRef.current.close?.();
        audioCtxRef.current = null;
      }
    } catch { }
  };

  const startWaveMonitor = async (stream) => {
    try {
      stopWaveMonitor();
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      analyser.smoothingTimeConstant = 0.78;
      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);
      audioCtxRef.current = ctx;
      analyserRef.current = analyser;

      const data = new Uint8Array(analyser.fftSize);
      let bars = Array.from({ length: 22 }, () => 0.12);
      const tick = () => {
        if (!analyserRef.current) return;
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / data.length);
        const level = Math.max(0.08, Math.min(1, rms * 3.8));
        recordLevelsRef.current.push(level);
        if (recordLevelsRef.current.length > 4000) {
          recordLevelsRef.current = recordLevelsRef.current.slice(-4000);
        }
        bars = [...bars.slice(1), level];
        setRecordWaveBars(bars);
        waveAnimRef.current = requestAnimationFrame(tick);
      };
      waveAnimRef.current = requestAnimationFrame(tick);
    } catch {
      setRecordWaveBars(Array.from({ length: 22 }, () => 0.12));
    }
  };

  const startRecording = async () => {
    if (!selectedPhone) return;
    setAttachment(null);
    setRecordWaveBars(Array.from({ length: 22 }, () => 0.12));
    recordLevelsRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      startWaveMonitor(stream);

      const mr = new MediaRecorder(stream);
      recorderRef.current = mr;
      recChunksRef.current = [];

      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) recChunksRef.current.push(e.data);
      };

      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        stopWaveMonitor();

        const blob = new Blob(recChunksRef.current, { type: mr.mimeType || "audio/webm" });
        const file = new File([blob], `audio_${Date.now()}.webm`, { type: blob.type });

        try {
          const fd = new FormData();
          fd.append("file", file);
          fd.append("kind", "audio");

          const r = await fetch(`${API_BASE}/api/media/upload`, { method: "POST", body: fd });
          if (!r.ok) {
            const t = await r.text();
            throw new Error(`upload failed ${r.status}: ${t}`);
          }
          const data = await r.json();

          setAttachment({
            kind: "media",
            msg_type: "audio",
            media_id: data.media_id,
            filename: data.filename || file.name,
            mime_type: data.mime_type || blob.type,
            duration_sec: recordSeconds || null,
            file_size: file.size || null,
          });

          const compressed = normalizeWaveBars(recordLevelsRef.current, 48);
          setAudioWaveforms((prev) => ({
            ...prev,
            [data.media_id]: compressed,
          }));
        } catch (err) {
          console.error(err);
          alert("Error subiendo el audio grabado");
        }
      };

      mr.start();
      setIsRecording(true);
      setRecordSeconds(0);

      recTimerRef.current = setInterval(() => {
        setRecordSeconds(s => s + 1);
      }, 1000);

    } catch (e) {
      console.error(e);
      alert("No se pudo acceder al microfono. Revisa permisos del navegador.");
    }
  };

  const stopRecording = async () => {
    try {
      if (recTimerRef.current) {
        clearInterval(recTimerRef.current);
        recTimerRef.current = null;
      }
      setIsRecording(false);
      stopWaveMonitor();

      const mr = recorderRef.current;
      recorderRef.current = null;

      if (mr && mr.state !== "inactive") mr.stop();
    } catch (e) { console.error(e); }
  };

  const toggleTakeover = async () => {
    if (!selectedPhone) return;
    const current = conversations.find(c => c.phone === selectedPhone)?.takeover || false;
    await fetch(`${API_BASE}/api/conversations/takeover`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: selectedPhone, takeover: !current }),
    });
    loadConversations();
  };

  const onClearFilters = () => {
    setQ("");
    setFilterTakeover("all");
    setFilterUnread("all");
    setFilterTags("");
    setConversationsError("");
  };

  const handleTabChange = (nextTab) => {
    setActiveTab(nextTab);
    setShowAttachMenu(false);
    if (nextTab !== "inbox") return;
    if (isMobile && !selectedPhone) {
      setInboxMobileView("list");
    }
  };

  // Poll conversations
  useEffect(() => {
    if (activeTab !== "inbox" || inboxViewMode !== "messages") return;
    loadConversations();
    const interval = setInterval(loadConversations, 2500);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, inboxViewMode, selectedPhone, filterTakeover, filterUnread, filterTags, q, inboxChannel]);

  // Poll messages for selected
  useEffect(() => {
    if (activeTab !== "inbox" || inboxViewMode !== "messages") return;
    if (selectedPhone) {
      loadMessages(selectedPhone);
      const interval = setInterval(() => loadMessages(selectedPhone), 2500);
      return () => clearInterval(interval);
    }
  }, [activeTab, inboxViewMode, selectedPhone, inboxChannel]);

  useEffect(() => {
    audioWaveformsRef.current = audioWaveforms;
  }, [audioWaveforms]);

  useEffect(() => {
    const ids = (messages || [])
      .filter((m) => m?.msg_type === "audio" && m?.media_id)
      .map((m) => String(m.media_id));
    if (!ids.length) return;

    const pendingIds = ids.filter((id) => !audioWaveformsRef.current[id] && !waveLoadingRef.current.has(id));
    if (!pendingIds.length) return;

    let cancelled = false;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();

    const run = async () => {
      for (const mediaId of pendingIds) {
        if (cancelled) break;
        waveLoadingRef.current.add(mediaId);
        try {
          const r = await fetch(mediaProxyUrl(mediaId));
          if (!r.ok) throw new Error(`wave fetch failed: ${r.status}`);
          const ab = await r.arrayBuffer();
          const decoded = await ctx.decodeAudioData(ab.slice(0));
          const bars = waveformFromAudioBuffer(decoded, 42);
          if (!cancelled) {
            setAudioWaveforms((prev) => (prev[mediaId] ? prev : { ...prev, [mediaId]: bars }));
          }
        } catch {
          // no-op: fallback waveform will still render
        } finally {
          waveLoadingRef.current.delete(mediaId);
        }
      }
    };

    run();

    return () => {
      cancelled = true;
      try { ctx.close?.(); } catch { }
    };
  }, [messages, inboxChannel]);

  // Auto-scroll on new messages if user near bottom
  useEffect(() => {
    if (userNearBottomRef.current) scrollToBottom(true);
  }, [messages.length]);

  // cada vez que se abre chat o llega update, marcamos leido
  useEffect(() => {
    if (activeTab !== "inbox" || inboxViewMode !== "messages") return;
    if (!selectedPhone) return;
    markRead(selectedPhone);
    // y refrescamos inbox para quitar unread badge
    loadConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, inboxViewMode, selectedPhone]);

  useEffect(() => {
    return () => {
      try {
        if (recTimerRef.current) clearInterval(recTimerRef.current);
      } catch { }
      stopWaveMonitor();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!isMobile) {
      setInboxMobileView("chat");
      return;
    }
    if (activeTab !== "inbox") return;
    if (!selectedPhone) {
      setInboxMobileView("list");
    }
  }, [isMobile, activeTab, selectedPhone]);

  const selectedConversation = conversations.find(c => c.phone === selectedPhone);
  const selectedConversationChannel = normalizeInboxChannel(
    normalizeInboxChannel(inboxChannel, "all") === "all" ? selectedConversation?.last_channel : inboxChannel,
    "whatsapp"
  );
  const selectedConversationChannelMeta = getInboxChannelMeta(selectedConversationChannel, "whatsapp");
  const showInboxList = !isMobile || inboxMobileView === "list";
  const showInboxChat = !isMobile || inboxMobileView === "chat";
  const showInboxCRM = !isMobile || inboxMobileView === "crm";

  return (
    <div className={`app-layout ${isMobile ? "layout-mobile" : isTablet ? "layout-tablet" : "layout-desktop"}`}>
      <MainNav activeTab={activeTab} onChangeTab={handleTabChange} isMobile={isMobile} />

      <div className={`app-content ${activeTab === "inbox" ? "app-content-inbox" : "app-content-page"}`}>
        {activeTab === 'inbox' ? (
          <div className="inbox-shell">
            <div className="inbox-mode-tabs">
              <button
                type="button"
                className={`inbox-mode-tab ${inboxViewMode === "messages" ? "active" : ""}`}
                onClick={() => setInboxViewMode("messages")}
              >
                Mensajeria instantanea
              </button>
              <button
                type="button"
                className={`inbox-mode-tab ${inboxViewMode === "comments" ? "active" : ""}`}
                onClick={() => setInboxViewMode("comments")}
              >
                Comentarios
              </button>
            </div>

            {inboxViewMode === "messages" ? (
            <div className={`inbox-layout ${isMobile ? "inbox-mobile" : isTablet ? "inbox-tablet" : "inbox-desktop"}`}>
            {showInboxList && (
              <ChatList
                conversations={conversations}
                selectedPhone={selectedPhone}
                onSelect={selectChat}
                channel={inboxChannel}
                setChannel={setInboxChannel}
                q={q}
                setQ={setQ}
                filterTakeover={filterTakeover}
                setFilterTakeover={setFilterTakeover}
                filterUnread={filterUnread}
                setFilterUnread={setFilterUnread}
                filterTags={filterTags}
                setFilterTags={setFilterTags}
                onClearFilters={onClearFilters}
                loadError={conversationsError}
              />
            )}

            {showInboxChat && (
              <div className={`chat-window ${isMobile ? "chat-window-mobile" : ""}`}>
                            <header className="chat-header">
                  <div className="header-info">
                    {isMobile && (
                      <button type="button" className="mobile-nav-btn" onClick={() => setInboxMobileView("list")}>
                        Inbox
                      </button>
                    )}
                    {selectedPhone ? (
                      <>
                        <div className="avatar-circle">
                          {initialsFromConversation(selectedConversation)}
                        </div>
                        <div>
                          <h3 className="chat-title">{displayName(selectedConversation)}</h3>
                          <div className="chat-subtitle">
                            <span style={{ marginRight: 6, opacity: 0.9, fontWeight: 600 }}>Canal:</span>
                            <span
                              className={`channel-chip channel-${selectedConversationChannel}`}
                              style={{ marginRight: 6 }}
                              title={`Canal: ${selectedConversationChannelMeta.label}`}
                            >
                              {selectedConversationChannelMeta.short}
                            </span>
                            <span style={{ marginRight: 8, opacity: 0.9, fontWeight: 600 }}>
                              {selectedConversationChannelMeta.label}
                            </span>
                            {selectedConversation?.updated_at ? `Ultimo: ${fmtDateTime(selectedConversation.updated_at)}` : ''}
                          </div>
                        </div>
                      </>
                    ) : (
                      <h3 className="chat-title">Selecciona una conversacion</h3>
                    )}
                  </div>

                  <div className="chat-header-actions">
                    {isMobile && selectedPhone && (
                      <button type="button" className="mobile-nav-btn" onClick={() => setInboxMobileView("crm")}>
                        CRM
                      </button>
                    )}
                    {selectedPhone && (
                      <button
                        onClick={toggleTakeover}
                        className={`takeover-btn ${selectedConversation?.takeover ? 'active' : ''}`}
                      >
                        {selectedConversation?.takeover ? <IconUser /> : <IconBot />}
                        <span className="takeover-label">Takeover: {selectedConversation?.takeover ? 'ON' : 'OFF'}</span>
                      </button>
                    )}
                  </div>
                </header>

            <div
              ref={messagesRef}
              className="messages-area custom-scrollbar"
              onScroll={() => { userNearBottomRef.current = isNearBottom(messagesRef.current); }}
            >
              {messages.map((m) => (
                <div key={m.id} className={`message-row ${m.direction === 'out' ? 'out' : 'in'}`}>
                  <div className={`message-bubble ${m.direction === 'out' ? 'out' : 'in'}`}>

                    {(m.featured_image || m.media_url) && (
                      <div className="msg-image-container">
                        <img
                          src={m.featured_image || m.media_url}
                          alt=""
                          style={{
                            width: "100%",
                            maxWidth: "360px",
                            maxHeight: "280px",
                            objectFit: "contain",
                            borderRadius: "14px",
                            display: "block",
                            marginTop: "10px",
                          }}
                        />
                      </div>
                    )}

                    {m.msg_type === "image" && m.media_id && (
                      <div className="msg-image-container">
                        <img
                          src={mediaProxyUrl(m.media_id)}
                          alt={m.file_name || ""}
                          style={{
                            width: "100%",
                            maxWidth: "360px",
                            maxHeight: "280px",
                            objectFit: "contain",
                            borderRadius: "14px",
                            display: "block",
                            marginTop: "10px",
                          }}
                        />
                      </div>
                    )}

                    {m.msg_type === "video" && m.media_id && (
                      <div style={{ marginTop: 10 }}>
                        <video
                          controls
                          preload="metadata"
                          style={{ width: "100%", maxWidth: 360, borderRadius: 14 }}
                          src={mediaProxyUrl(m.media_id)}
                        />
                      </div>
                    )}

                    {m.msg_type === "audio" && m.media_id && (
                      <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 12, opacity: 0.85, marginBottom: 6 }}>
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                            <IconAudioMessage />
                            <span>
                              {m.file_name || "audio"} {m.duration_sec ? `| ${formatDur(m.duration_sec)}` : ""} {m.file_size ? `| ${formatBytes(m.file_size)}` : ""}
                            </span>
                          </span>
                        </div>
                        <div className="msg-audio-wave">
                          {(audioWaveforms[m.media_id] || defaultWaveBars(m.media_id, 42)).map((v, idx) => (
                            <span key={`msg-wave-${m.id}-${idx}`} style={{ height: `${Math.max(5, Math.round(16 * Number(v || 0.2)))}px` }} />
                          ))}
                        </div>
                        <audio controls preload="metadata" style={{ width: 280 }} src={mediaProxyUrl(m.media_id)} />
                      </div>
                    )}

                    {m.msg_type === "document" && m.media_id && (
                      <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 6 }}>
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                            <IconFile />
                            <span>{m.file_name || "documento"} {m.file_size ? `| ${formatBytes(m.file_size)}` : ""}</span>
                          </span>
                        </div>
                        <a
                          href={mediaProxyUrl(m.media_id)}
                          target="_blank"
                          rel="noreferrer"
                          className="btn-action"
                          style={{ display: "inline-flex", gap: 8, alignItems: "center" }}
                        >
                          Descargar / Ver
                        </a>
                      </div>
                    )}

                    <div className="msg-text">{m.text || m.media_caption || ""}</div>

                    {m.real_image && m.real_image !== m.featured_image && (
                      <div className="msg-actions">
                        <button onClick={() => window.open(m.real_image, '_blank')} className="btn-action">
                          <IconImage /> Ver foto real
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="msg-meta">
                    <span>{m.direction === 'out' ? 'Asesor/Bot' : 'Cliente'}</span>
                    <span>|</span>
                    <span>{fmtDateTime(m.created_at)}</span>
                    {m.direction === "out" && (
                      <>
                        <span style={{ margin: "0 6px" }}>|</span>
                        <span className={`wa-ticks ${waTickClass(m)}`} title={m.wa_error || m.wa_status || ""}>
                          {waTicks(m)}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} className="spacer" />
            </div>

            {/* COMPOSER */}
            <div className="composer-area" style={{ position: "relative" }}>

              <input
                ref={fileInputRef}
                type="file"
                style={{ display: "none" }}
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (!f || !selectedPhone) return;

                  try {
                    const fd = new FormData();
                    fd.append("file", f);
                    fd.append("kind", filePickKind);

                    const r = await fetch(`${API_BASE}/api/media/upload`, {
                      method: "POST",
                      body: fd
                    });

                    if (!r.ok) {
                      const t = await r.text();
                      throw new Error(`upload failed ${r.status}: ${t}`);
                    }
                    const data = await r.json();

                    setAttachment({
                      kind: "media",
                      msg_type: filePickKind,
                      media_id: data.media_id,
                      filename: data.filename,
                      mime_type: data.mime_type,
                      file_size: f.size || null,
                      duration_sec: null,
                    });

                  } catch (err) {
                    console.error(err);
                    alert("Error subiendo el archivo");
                  } finally {
                    e.target.value = "";
                  }
                }}
              />

              {showAttachMenu && (
                <div className="attach-menu">
                  <button onClick={() => { setFilePickKind("image"); fileInputRef.current?.click(); setShowAttachMenu(false); }}>
                    <IconImage /> Imagen
                  </button>
                  <button onClick={() => { setFilePickKind("video"); fileInputRef.current?.click(); setShowAttachMenu(false); }}>
                    <IconVideo /> Video
                  </button>
                  <button onClick={() => { setFilePickKind("document"); fileInputRef.current?.click(); setShowAttachMenu(false); }}>
                    <IconFile /> Documento
                  </button>
                  <button onClick={() => { setFilePickKind("audio"); fileInputRef.current?.click(); setShowAttachMenu(false); }}>
                    <IconAudio /> Audio
                  </button>
                  <button onClick={() => {
                    setShowProductModal(true);
                    setShowAttachMenu(false);
                    loadWCProducts(prodQ);
                  }}>
                    <IconBag /> Producto (Catalogo)
                  </button>
                </div>
              )}

              <div className="composer-input-wrapper">
                <button
                  className="btn-attach"
                  onClick={() => setShowAttachMenu(v => !v)}
                  disabled={!selectedPhone}
                  title="Adjuntar"
                >
                  <IconPaperclip />
                </button>

                <button
                  className={`btn-attach ${isRecording ? "recording" : ""}`}
                  onClick={() => (isRecording ? stopRecording() : startRecording())}
                  disabled={!selectedPhone}
                  title={isRecording ? "Detener grabacion" : "Grabar audio"}
                >
                  <IconMic />
                </button>

                {isRecording ? (
                  <div className="recording-wave-wrap" aria-live="polite">
                    <span className="recording-dot" />
                    <span className="recording-time">{fmtTimer(recordSeconds)}</span>
                    <div className="recording-wave" aria-hidden="true">
                      {recordWaveBars.map((level, idx) => (
                        <span
                          key={`wave-${idx}`}
                          style={{ height: `${Math.max(12, Math.round(24 * Number(level || 0.12)))}px` }}
                        />
                      ))}
                    </div>
                    <span className="recording-label">Grabando...</span>
                  </div>
                ) : (
                  <input
                    className="composer-input"
                    placeholder="Escribe un mensaje..."
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                    disabled={!selectedPhone}
                  />
                )}

                <EmojiPickerButton
                  disabled={!selectedPhone || isRecording}
                  onSelect={(emoji) => setText((prev) => `${prev || ""}${emoji}`)}
                  title="Agregar emoji al mensaje"
                />

                <button
                  onClick={sendMessage}
                  disabled={!text.trim() && !attachment}
                  className="btn-send"
                >
                  <IconSend />
                </button>
              </div>

              {!isRecording && selectedPhone && text.trim() && (
                <div className="typing-indicator">
                  <span>Escribiendo</span>
                  <span className="typing-dots">
                    <span />
                    <span />
                    <span />
                  </span>
                </div>
              )}

              {attachment && (
                <div className="attach-preview">
                  <div className="ap-meta">
                    <p className="ap-title">
                      {attachment.kind === "product" ? "Producto adjunto OK" : "Archivo adjunto OK"}
                    </p>
                    <p className="ap-sub">
                      {attachment.kind === "product"
                        ? (attachment.permalink || "")
                        : (attachment.filename || attachment.mime_type || attachment.media_id)
                      }
                    </p>
                  </div>
                  <button className="ap-remove" onClick={() => setAttachment(null)} title="Quitar">X</button>
                </div>
              )}
            </div>

            {/* MODAL PRODUCTOS */}
            {showProductModal && (
              <div className="modal-backdrop" onClick={() => setShowProductModal(false)}>
                <div className="modal" onClick={(e) => e.stopPropagation()}>
                  <div className="modal-header">
                    <h4>Adjuntar producto</h4>
                    <button className="modal-close" onClick={() => setShowProductModal(false)}>X</button>
                  </div>
                  <div className="modal-body">
                    <div className="modal-search">
                      <input
                        placeholder="Buscar perfume..."
                        value={prodQ}
                        onChange={(e) => {
                          const v = e.target.value;
                          setProdQ(v);
                          loadWCProducts(v);
                        }}
                        autoFocus
                      />
                    </div>

                    <div className="product-grid">
                      {prodLoading && <div style={{ color: "#94a3b8" }}>Cargando catalogo...</div>}
                      {prodError && <div style={{ color: "#e74c3c" }}>{prodError}</div>}

                      {!prodLoading && !prodError && (products || []).map(p => (
                        <div key={p.id} className="product-card">
                          <img src={p.featured_image} alt="" />
                          <div style={{ minWidth: 0 }}>
                            <h5 style={{ margin: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                              {p.name}
                            </h5>
                            <p style={{ margin: "4px 0 0" }}>{p.price ? `$${p.price}` : ""}</p>
                            {p.brand && <p style={{ margin: "4px 0 0", fontSize: 11, opacity: 0.8 }}>{p.brand}</p>}
                          </div>

                          <div className="pc-actions">
                            <button onClick={() => sendWCProduct(p)} disabled={sendingProductId === p.id}>
                              {sendingProductId === p.id ? "Enviando..." : "Enviar"}
                            </button>
                          </div>
                        </div>
                      ))}

                      {!prodLoading && !prodError && (!products || products.length === 0) && (
                        <div style={{ color: "#94a3b8" }}>No hay productos para esa busqueda.</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

              </div>
            )}

            {showInboxCRM && (
              <CustomerCardCRM
                phone={selectedPhone}
                takeover={selectedConversation?.takeover}
                isMobile={isMobile}
                onBack={() => setInboxMobileView("chat")}
              />
            )}
          </div>
            ) : (
              <InboxCommentsPanel apiBase={API_BASE} />
            )}
          </div>
      ) : activeTab === "dashboard" ? (
        <DashboardPanel apiBase={API_BASE} />
      ) : activeTab === "crm" ? (
        <CustomersPanel apiBase={API_BASE} />
      ) : activeTab === "labels" ? (
        <LabelsPanel apiBase={API_BASE} />
      ) : activeTab === "marketing" ? (
        <MarketingPanel apiBase={API_BASE} />
      ) : activeTab === "mass_messaging" ? (
        <MassMessagingPanel apiBase={API_BASE} />
      ) : activeTab === "ads_manager" ? (
        <AdsManagerPanel />
      ) : activeTab === "settings" ? (
        <SettingsPanel apiBase={API_BASE} />
      ) : (
        <div className="placeholder-view">
          Modulo en construccion
        </div>
      )}
      </div>
    </div>
  );
}








