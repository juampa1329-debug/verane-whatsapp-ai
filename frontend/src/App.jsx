import React, { useState, useEffect, useRef, useMemo } from 'react';

// --- ESTILOS CSS (Integrados para asegurar el diseño visual exacto) ---
const styles = `
/* --- Global Reset & Variables --- */
:root {
  --bg-dark: #0b1217;
  --bg-sidebar: #0f1b22;
  --bg-input: rgba(255,255,255,0.05);
  --border-color: rgba(255,255,255,0.1);
  --primary-green: #2ecc71;
  --primary-green-dim: rgba(46, 204, 113, 0.1);
  --text-main: #e2e8f0;
  --text-muted: #94a3b8;
  --danger: #e74c3c;
  --danger-dim: rgba(231, 76, 60, 0.15);
}

body {
  margin: 0;
  padding: 0;
  background-color: var(--bg-dark);
  color: var(--text-main);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  overflow: hidden;
}

/* --- Layout Principal --- */
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

/* --- 1. Navegación Lateral (Izquierda) --- */
.main-nav {
  width: 80px;
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  z-index: 20;
}

.nav-logo {
  margin-bottom: 32px;
  font-weight: 900;
  font-size: 24px;
  color: var(--primary-green);
  letter-spacing: -1px;
}

.nav-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  padding: 0 8px;
}

.nav-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-btn:hover {
  background-color: rgba(255,255,255,0.05);
  color: #fff;
}

.nav-btn.active {
  background-color: var(--primary-green-dim);
  color: var(--primary-green);
}

.nav-btn span {
  font-size: 10px;
  margin-top: 4px;
  font-weight: 500;
}

.nav-footer {
  margin-top: auto;
}

.avatar-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #1e293b;
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: var(--text-muted);
}

/* --- 2. Panel Lista de Chat --- */
.chat-list-panel {
  width: 320px;
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: 10;
}

.chat-list-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-row h2 {
  margin: 0;
  font-size: 18px;
  color: #fff;
}

.badge {
  font-size: 10px;
  background-color: rgba(255,255,255,0.1);
  padding: 2px 8px;
  border-radius: 99px;
  color: var(--text-muted);
}

.search-box {
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 10px;
  color: var(--text-muted);
}

.search-box input {
  width: 100%;
  background-color: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 10px 10px 10px 36px;
  color: #fff;
  outline: none;
  font-size: 14px;
  transition: border-color 0.2s;
}

.search-box input:focus {
  border-color: var(--primary-green);
}

.chat-list-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.chat-item {
  width: 100%;
  background: transparent;
  border: 1px solid transparent;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 12px;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s;
}

.chat-item:hover {
  background-color: rgba(255,255,255,0.03);
}

.chat-item.selected {
  background-color: var(--primary-green-dim);
  border-color: rgba(46, 204, 113, 0.2);
}

.chat-item-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.chat-phone {
  font-weight: bold;
  font-size: 14px;
  color: #fff;
}

.chat-date {
  font-size: 10px;
  color: var(--text-muted);
}

.chat-tags {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}

.pill {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 99px;
  border: 1px solid transparent;
  font-weight: bold;
}

.pill-bot {
  background-color: var(--primary-green-dim);
  color: var(--primary-green);
  border-color: rgba(46, 204, 113, 0.2);
}

.pill-human {
  background-color: var(--danger-dim);
  color: #e74c3c;
  border-color: rgba(231, 76, 60, 0.2);
}

.chat-preview {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
  opacity: 0.8;
}

/* --- 3. Ventana de Chat --- */
.chat-window {
  flex: 1;
  background-color: var(--bg-dark);
  display: flex;
  flex-direction: column;
  position: relative;
  min-width: 0;
}

.chat-header {
  height: 64px;
  padding: 0 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--bg-dark);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2ecc71, #16a085);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 12px;
  color: #fff;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.chat-title {
  margin: 0;
  font-size: 14px;
  font-weight: bold;
  color: #fff;
}

.chat-subtitle {
  font-size: 11px;
  color: var(--text-muted);
}

.takeover-btn {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background-color: rgba(46, 204, 113, 0.1);
  color: var(--primary-green);
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.takeover-btn.active {
  background-color: var(--danger-dim);
  color: var(--danger);
  border-color: rgba(231, 76, 60, 0.2);
}

/* Mensajes */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message-row {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

.message-row.in {
  align-items: flex-start;
  align-self: flex-start;
}

.message-row.out {
  align-items: flex-end;
  align-self: flex-end;
}

.message-bubble {
  padding: 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
  position: relative;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.message-bubble.in {
  background-color: rgba(255,255,255,0.1);
  color: var(--text-main);
  border-bottom-left-radius: 2px;
  border: 1px solid rgba(255,255,255,0.05);
}

.message-bubble.out {
  background-color: rgba(46, 204, 113, 0.2);
  color: #fff;
  border-bottom-right-radius: 2px;
  border: 1px solid rgba(46, 204, 113, 0.2);
}

.msg-image-container {
  margin-bottom: 12px;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(0,0,0,0.2);
}

.msg-image-container img {
  max-width: 220px;
  max-height: 220px;
  object-fit: contain;
  border-radius: 12px;
}

.msg-text {
  white-space: pre-wrap;
}

.msg-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.btn-action {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px;
  background-color: #1e293b;
  border: 1px solid #475569;
  border-radius: 8px;
  color: #fff;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
}

.btn-action:hover {
  background-color: #0f172a;
}

.msg-meta {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  padding: 0 4px;
  opacity: 0.6;
  font-size: 10px;
  color: var(--text-muted);
}

/* Composer */
.composer-area {
  padding: 16px;
  background-color: var(--bg-sidebar);
  border-top: 1px solid var(--border-color);
}

.composer-input-wrapper {
  display: flex;
  gap: 12px;
  background-color: var(--bg-dark);
  padding: 4px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
}

.composer-input-wrapper:focus-within {
  border-color: var(--primary-green);
  background-color: rgba(255,255,255,0.02);
}

.composer-input {
  flex: 1;
  background: transparent;
  border: none;
  padding: 12px;
  color: #fff;
  outline: none;
  font-size: 14px;
}

.btn-send {
  background-color: var(--primary-green);
  color: #0b1217;
  border: none;
  border-radius: 10px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.1s;
}

.btn-send:active { transform: scale(0.95); }
.btn-send:disabled { opacity: 0.5; cursor: not-allowed; }

/* --- 4. Panel CRM (Derecha) --- */
.crm-panel {
  width: 380px;
  background-color: var(--bg-sidebar);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: 10;
}

.crm-header {
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
}

.crm-header h3 {
  margin: 0;
  font-size: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
}

.icon-green { color: var(--primary-green); display: flex; }

.crm-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.crm-card-info {
  background-color: rgba(255,255,255,0.03);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
}

.crm-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 14px;
}
.crm-row:last-child { margin-bottom: 0; }

.crm-label { color: var(--text-muted); }
.crm-value.mono { font-family: monospace; font-weight: bold; color: #fff; }

.form-group-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.form-group label {
  font-size: 12px;
  font-weight: bold;
  color: var(--text-muted);
}

.flex-label { display: flex; align-items: center; gap: 6px; }

.form-group input, .form-group select {
  background-color: var(--bg-dark);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px;
  color: #fff;
  outline: none;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input:focus, .form-group textarea:focus, .form-group select:focus {
  border-color: var(--primary-green);
}

.notes-area {
  min-height: 140px;
  resize: none;
  background-color: var(--bg-dark);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  color: #fff;
  outline: none;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
}

.separator {
  height: 1px;
  background-color: var(--border-color);
  margin: 16px 0 24px 0;
}

.crm-footer {
  padding: 24px;
  background-color: var(--bg-sidebar);
  border-top: 1px solid var(--border-color);
}

.btn-save {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid transparent;
  background-color: rgba(255,255,255,0.05);
  color: var(--text-muted);
  font-weight: bold;
  cursor: not-allowed;
  transition: all 0.2s;
}

.btn-save.dirty {
  background-color: rgba(52, 152, 219, 0.15);
  color: #3498db;
  border-color: rgba(52, 152, 219, 0.3);
  cursor: pointer;
}

.btn-save.dirty:hover {
  background-color: rgba(52, 152, 219, 0.25);
}

.status-msg {
  text-align: center;
  font-size: 12px;
  margin-top: 12px;
  color: var(--primary-green);
}

/* Scrollbars */
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

.spacer { height: 1px; }
.placeholder-view { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--text-muted); }
`;

// --- CONFIGURACIÓN ---
const API_BASE = "";

// --- ICONOS SVG (Nativos) ---
const IconMessage = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>;
const IconUsers = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>;
const IconZap = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>;
const IconSettings = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>;
const IconSearch = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>;
const IconSend = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>;
const IconBot = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>;
const IconUser = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>;
const IconImage = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>;
const IconTag = () => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>;
const IconBag = () => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>;

function fmtDateTime(s) {
  if (!s) return '';
  try { return new Date(s).toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' }); }
  catch { return s; }
}

// --- 1. Barra de Navegación Lateral ---
const MainNav = ({ activeTab, setActiveTab }) => {
  const navItems = [
    { id: 'inbox', icon: IconMessage, label: 'Inbox' },
    { id: 'crm', icon: IconUsers, label: 'Clientes' },
    { id: 'marketing', icon: IconZap, label: 'Campañas' },
    { id: 'settings', icon: IconSettings, label: 'Ajustes' },
  ];

  return (
    <div className="main-nav">
      <div className="nav-logo">V.</div>
      <nav className="nav-items">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
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
const ChatList = ({ conversations, selectedPhone, onSelect, q, setQ }) => {
  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return conversations;
    return conversations.filter(c =>
      (c.phone || "").toLowerCase().includes(term) ||
      (c.text || "").toLowerCase().includes(term)
    );
  }, [conversations, q]);

  return (
    <div className="chat-list-panel">
      <div className="chat-list-header">
        <div className="header-row">
          <h2>Inbox</h2>
          <span className="badge">Local</span>
        </div>
        <div className="search-box">
          <div className="search-icon"><IconSearch /></div>
          <input
            placeholder="Buscar..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
      </div>

      <div className="chat-list-items custom-scrollbar">
        {filtered.map(c => (
          <button
            key={c.phone}
            onClick={() => onSelect(c.phone)}
            className={`chat-item ${selectedPhone === c.phone ? 'selected' : ''}`}
          >
            <div className="chat-item-top">
              <span className="chat-phone">{c.phone}</span>
              <span className="chat-date">{fmtDateTime(c.created_at).split(',')[0]}</span>
            </div>

            <div className="chat-tags">
              <span className={`pill ${c.takeover ? 'pill-human' : 'pill-bot'}`}>
                {c.takeover ? 'Humano' : 'Bot'}
              </span>
            </div>

            <p className="chat-preview">
              {c.text}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
};

// --- 3. Panel de CRM (Datos del cliente) ---
const CustomerCardCRM = ({ phone, takeover }) => {
  const [form, setForm] = useState({
    first_name: "", last_name: "", city: "", customer_type: "",
    interests: "", tags: "", notes: ""
  });
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

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
      setDirty(false);
      setStatus("");
    } catch (e) { console.error(e); }
  };

  useEffect(() => { load(); }, [phone]);

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
      setStatus("Guardado ✅");
    } catch {
      setStatus("Error al guardar ❌");
    } finally {
      setSaving(false);
      setTimeout(() => setStatus(""), 2500);
    }
  };

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    setDirty(true);
  };

  if (!phone) return <div className="crm-panel empty" />;

  return (
    <div className="crm-panel">
      <div className="crm-header">
        <h3><span className="icon-green"><IconUsers /></span> CRM – Cliente</h3>
      </div>

      <div className="crm-content custom-scrollbar">
        <div className="crm-card-info">
            <div className="crm-row">
                <span className="crm-label">Teléfono</span>
                <span className="crm-value mono">{phone}</span>
            </div>
            <div className="crm-row">
                <span className="crm-label">Modo</span>
                <span className={`pill ${takeover ? "pill-human" : "pill-bot"}`}>
                    {takeover ? "Humano" : "Bot"}
                </span>
            </div>
        </div>

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
               placeholder="Ej: Pérez"
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
        </div>

        <div className="separator" />

        <div className="form-group">
           <label className="flex-label"><IconBag /> Notas Internas</label>
          <textarea
            className="notes-area"
            value={form.notes}
            onChange={e => handleChange('notes', e.target.value)}
            placeholder="Escribe notas aquí..."
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
  const [conversations, setConversations] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [q, setQ] = useState("");

  const bottomRef = useRef(null);

  const loadConversations = async () => {
    try {
      const r = await fetch(`${API_BASE}/api/conversations`);
      const data = await r.json();
      const list = data.conversations || [];
      setConversations(list);
      if (!selectedPhone && list.length > 0) { /* Opcional: setSelectedPhone(list[0].phone); */ }
    } catch (e) { console.error("Error cargando conversaciones", e); }
  };

  const loadMessages = async (phone) => {
    if (!phone) return;
    try {
      const r = await fetch(`${API_BASE}/api/conversations/${encodeURIComponent(phone)}/messages`);
      const data = await r.json();
      setMessages(data.messages || []);
    } catch (e) { console.error(e); }
  };

     const sendMessage = async () => {
      if (!text.trim() || !selectedPhone) return;

      try {
        // 1) Guardar el mensaje como SALIENTE (Asesor/Humano)
        const r = await fetch(`${API_BASE}/api/messages/ingest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            phone: selectedPhone,
            direction: "out",     // <- CLAVE: esto lo manda al lado del asesor
            text: text
          }),
        });

        if (!r.ok) throw new Error("No se pudo guardar el mensaje");

        // 2) NO llamamos al bot aquí, porque esto es un mensaje humano hacia el cliente
        // (El bot debe responder solo cuando llegue un mensaje entrante real del cliente)

        await loadMessages(selectedPhone);
        setText("");
        loadConversations();
      } catch (e) {
        console.error(e);
      }
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

  useEffect(() => {
    loadConversations();
    const interval = setInterval(loadConversations, 2500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedPhone) {
      loadMessages(selectedPhone);
      const interval = setInterval(() => loadMessages(selectedPhone), 2500);
      return () => clearInterval(interval);
    }
  }, [selectedPhone]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const selectedConversation = conversations.find(c => c.phone === selectedPhone);

  return (
    <div className="app-layout">
        {/* Inyectamos los estilos CSS directamente */}
        <style>{styles}</style>
      <MainNav activeTab={activeTab} setActiveTab={setActiveTab} />

      {activeTab === 'inbox' ? (
        <>
          <ChatList
             conversations={conversations}
             selectedPhone={selectedPhone}
             onSelect={setSelectedPhone}
             q={q}
             setQ={setQ}
          />

          <div className="chat-window">
            <header className="chat-header">
              <div className="header-info">
                {selectedPhone && (
                  <>
                    <div className="avatar-circle">
                      {selectedPhone.slice(-2)}
                    </div>
                    <div>
                      <h3 className="chat-title">{selectedPhone}</h3>
                      <div className="chat-subtitle">
                        {selectedConversation?.created_at ? `Último: ${fmtDateTime(selectedConversation.created_at)}` : ''}
                      </div>
                    </div>
                  </>
                )}
              </div>

              {selectedPhone && (
                <button
                  onClick={toggleTakeover}
                  className={`takeover-btn ${selectedConversation?.takeover ? 'active' : ''}`}
                >
                  {selectedConversation?.takeover ? <IconUser /> : <IconBot />}
                  <span>Takeover: {selectedConversation?.takeover ? 'ON' : 'OFF'}</span>
                </button>
              )}
            </header>

            <div className="messages-area custom-scrollbar">
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
                            maxWidth: "360px",     // <-- controla el tamaño en el bubble
                            maxHeight: "280px",
                            objectFit: "contain",
                            borderRadius: "14px",
                            display: "block",
                            marginTop: "10px",
                          }}
                        />
                      </div>
                    )}


                    <div className="msg-text">{m.text}</div>

                    {m.real_image && m.real_image !== m.featured_image && (
                      <div className="msg-actions">
                          <button
                            onClick={() => window.open(m.real_image, '_blank')}
                            className="btn-action"
                          >
                            <IconImage /> Ver foto real
                          </button>
                      </div>
                    )}
                  </div>

                  <div className="msg-meta">
                      <span>{m.direction === 'out' ? 'Asesor/Bot' : 'Cliente'}</span>
                      <span>•</span>
                      <span>{fmtDateTime(m.created_at)}</span>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} className="spacer" />
            </div>

            <div className="composer-area">
              <div className="composer-input-wrapper">
                <input
                  className="composer-input"
                  placeholder="Escribe un mensaje..."
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                  disabled={!selectedPhone}
                />
                <button
                  onClick={sendMessage}
                  disabled={!text.trim()}
                  className="btn-send"
                >
                  <IconSend />
                </button>
              </div>
            </div>
          </div>

          <CustomerCardCRM
            phone={selectedPhone}
            takeover={selectedConversation?.takeover}
          />
        </>
      ) : (
        <div className="placeholder-view">
           Módulo en construcción
        </div>
      )}
    </div>
  );
}