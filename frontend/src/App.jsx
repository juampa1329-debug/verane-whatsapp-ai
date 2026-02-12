import React, { useState, useEffect, useRef, useMemo } from 'react';
import './App.css';

// --- CONFIGURACIÓN ---
// Nota: Para producción en Vite, normalmente usarías import.meta.env.VITE_API_BASE
// Pero para asegurar que compile en todos los entornos ahora mismo, usaremos el fallback directo.
const API_BASE = "https://backend.perfumesverane.com";

// --- AYUDAS (Fix para visualización) ---
const mediaProxyUrl = (mediaId) => {
  if (!mediaId) return "";
  return `${API_BASE}/api/media/proxy/${mediaId}`;
};

const formatBytes = (bytes, decimals = 2) => {
  if (!+bytes) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

const formatDur = (seconds) => {
  if (!seconds) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
};

// --- ICONOS SVG ---
const IconMessage = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>;
const IconUsers = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>;
const IconZap = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>;
const IconSettings = () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>;
const IconSearch = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>;
const IconSend = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>;
const IconBot = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="10" rx="2" /><circle cx="12" cy="5" r="2" /><path d="M12 7v4" /><line x1="8" y1="16" x2="8" y2="16" /><line x1="16" y1="16" x2="16" y2="16" /></svg>;
const IconUser = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>;
const IconImage = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>;
const IconTag = () => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" /><line x1="7" y1="7" x2="7.01" y2="7" /></svg>;
const IconBag = () => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><line x1="3" y1="6" x2="21" y2="6" /><path d="M16 10a4 4 0 0 1-8 0" /></svg>;
const IconPaperclip = () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-8.49 8.49a5 5 0 0 1-7.07-7.07l8.49-8.49a3.5 3.5 0 0 1 4.95 4.95l-8.5 8.5a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg>);

function fmtDateTime(s) {
  if (!s) return '';
  try { return new Date(s).toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' }); }
  catch { return s; }
}

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
          <button key={item.id} onClick={() => setActiveTab(item.id)} className={`nav-btn ${activeTab === item.id ? 'active' : ''}`}>
            <item.icon /><span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="nav-footer"><div className="avatar-placeholder">A</div></div>
    </div>
  );
};

const ChatList = ({ conversations, selectedPhone, onSelect, q, setQ }) => {
  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return conversations;
    return conversations.filter(c => (c.phone || "").toLowerCase().includes(term) || (c.text || "").toLowerCase().includes(term));
  }, [conversations, q]);

  return (
    <div className="chat-list-panel">
      <div className="chat-list-header">
        <div className="header-row"><h2>Inbox</h2><span className="badge">Local</span></div>
        <div className="search-box"><div className="search-icon"><IconSearch /></div><input placeholder="Buscar..." value={q} onChange={(e) => setQ(e.target.value)} /></div>
      </div>
      <div className="chat-list-items custom-scrollbar">
        {filtered.map(c => (
          <button key={c.phone} onClick={() => onSelect(c.phone)} className={`chat-item ${selectedPhone === c.phone ? 'selected' : ''}`}>
            <div className="chat-item-top"><span className="chat-phone">{c.phone}</span><span className="chat-date">{fmtDateTime(c.updated_at).split(',')[0]}</span></div>
            <div className="chat-tags"><span className={`pill ${c.takeover ? 'pill-human' : 'pill-bot'}`}>{c.takeover ? 'Humano' : 'Bot'}</span></div>
            <p className="chat-preview">{c.text || ""}</p>
          </button>
        ))}
      </div>
    </div>
  );
};

const CustomerCardCRM = ({ phone, takeover }) => {
  const [form, setForm] = useState({ first_name: "", last_name: "", city: "", customer_type: "", interests: "", tags: "", notes: "" });
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (phone) fetch(`${API_BASE}/api/crm/${encodeURIComponent(phone)}`).then(r => r.json()).then(d => setForm({ ...form, ...d })).catch(console.error);
  }, [phone]);

  const save = async () => {
    setSaving(true); setStatus("");
    try {
      await fetch(`${API_BASE}/api/crm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone, ...form }) });
      setDirty(false); setStatus("Guardado ✅");
    } catch { setStatus("Error al guardar ❌"); }
    finally { setSaving(false); setTimeout(() => setStatus(""), 2500); }
  };

  if (!phone) return <div className="crm-panel empty" />;

  return (
    <div className="crm-panel">
      <div className="crm-header"><h3><span className="icon-green"><IconUsers /></span> CRM – Cliente</h3></div>
      <div className="crm-content custom-scrollbar">
        <div className="crm-card-info">
          <div className="crm-row"><span className="crm-label">Teléfono</span><span className="crm-value mono">{phone}</span></div>
          <div className="crm-row"><span className="crm-label">Modo</span><span className={`pill ${takeover ? "pill-human" : "pill-bot"}`}>{takeover ? "Humano" : "Bot"}</span></div>
        </div>
        <div className="form-group-row">
          <div className="form-group"><label>Nombre</label><input value={form.first_name} onChange={e => { setForm({ ...form, first_name: e.target.value }); setDirty(true) }} /></div>
          <div className="form-group"><label>Apellido</label><input value={form.last_name} onChange={e => { setForm({ ...form, last_name: e.target.value }); setDirty(true) }} /></div>
        </div>
        <div className="form-group"><label>Ciudad</label><input value={form.city} onChange={e => { setForm({ ...form, city: e.target.value }); setDirty(true) }} /></div>
        <div className="form-group"><label className="flex-label"><IconBag /> Notas</label><textarea className="notes-area" value={form.notes} onChange={e => { setForm({ ...form, notes: e.target.value }); setDirty(true) }} /></div>
      </div>
      <div className="crm-footer"><button onClick={save} disabled={!dirty || saving} className={`btn-save ${dirty ? 'dirty' : ''}`}>{saving ? '...' : 'Guardar CRM'}</button>{status && <div className="status-msg">{status}</div>}</div>
    </div>
  );
};

export default function App() {
  const [activeTab, setActiveTab] = useState('inbox');
  const [conversations, setConversations] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [attachment, setAttachment] = useState(null);
  const fileInputRef = useRef(null);
  const [filePickKind, setFilePickKind] = useState("image");
  const [showProductModal, setShowProductModal] = useState(false);
  const [prodQ, setProdQ] = useState("");
  const [products, setProducts] = useState([]);
  const [prodLoading, setProdLoading] = useState(false);
  const [sendingProductId, setSendingProductId] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const recorderRef = useRef(null);
  const recChunksRef = useRef([]);
  const bottomRef = useRef(null);

  const loadConversations = async () => {
    try {
      const r = await fetch(`${API_BASE}/api/conversations`);
      const data = await r.json();
      setConversations(data.conversations || []);
    } catch (e) { console.error(e); }
  };

  const loadMessages = async (phone) => {
    if (!phone) return;
    try {
      const r = await fetch(`${API_BASE}/api/conversations/${encodeURIComponent(phone)}/messages`);
      const data = await r.json();
      setMessages(data.messages || []);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { loadConversations(); setInterval(loadConversations, 3000); }, []);
  useEffect(() => { if (selectedPhone) { loadMessages(selectedPhone); const i = setInterval(() => loadMessages(selectedPhone), 3000); return () => clearInterval(i); } }, [selectedPhone]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length, selectedPhone]);

  const loadWCProducts = async (search) => {
    setProdLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/wc/products?q=${encodeURIComponent(search)}`);
      const data = await r.json();
      setProducts(data.products || []);
    } catch { setProducts([]); } finally { setProdLoading(false); }
  };

  const sendMessage = async () => {
    if (!selectedPhone || (!text.trim() && !attachment)) return;
    const payload = {
      phone: selectedPhone, direction: "out", msg_type: attachment?.msg_type || "text",
      text: text.trim(),
      ...attachment
    };

    // Limpieza de campos redundantes si es producto
    if (attachment?.kind === 'product') {
      payload.msg_type = 'product';
      payload.text = attachment.text;
    }

    try {
      await fetch(`${API_BASE}/api/messages/ingest`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      setText(""); setAttachment(null); setShowAttachMenu(false); loadMessages(selectedPhone);
    } catch (e) { alert("Error enviando"); }
  };

  const handleFileUpload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData(); fd.append("file", f); fd.append("kind", filePickKind);
    try {
      const r = await fetch(`${API_BASE}/api/media/upload`, { method: "POST", body: fd });
      const d = await r.json();
      setAttachment({ kind: "media", msg_type: filePickKind, media_id: d.media_id, mime_type: d.mime_type, filename: d.filename });
    } catch { alert("Error subiendo archivo"); }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      recorderRef.current = mr; recChunksRef.current = [];
      mr.ondataavailable = e => recChunksRef.current.push(e.data);
      mr.onstop = async () => {
        const blob = new Blob(recChunksRef.current, { type: "audio/webm" });
        const fd = new FormData(); fd.append("file", blob, "audio.webm"); fd.append("kind", "audio");
        const r = await fetch(`${API_BASE}/api/media/upload`, { method: "POST", body: fd });
        const d = await r.json();
        setAttachment({ kind: "media", msg_type: "audio", media_id: d.media_id, mime_type: "audio/ogg", duration_sec: recordSeconds });
      };
      mr.start(); setIsRecording(true); setRecordSeconds(0);
      const interval = setInterval(() => setRecordSeconds(s => s + 1), 1000);
      mr.onstop = () => { clearInterval(interval); stream.getTracks().forEach(t => t.stop()); setIsRecording(false); };
    } catch { alert("Error micrófono"); }
  };

  return (
    <div className="app-layout">
      <MainNav activeTab={activeTab} setActiveTab={setActiveTab} />
      {activeTab === 'inbox' ? (
        <>
          <ChatList conversations={conversations} selectedPhone={selectedPhone} onSelect={setSelectedPhone} q={q} setQ={setQ} />
          <div className="chat-window">
            <header className="chat-header">
              {selectedPhone && <div className="header-info"><div className="avatar-circle">{selectedPhone.slice(-2)}</div><h3>{selectedPhone}</h3></div>}
            </header>
            <div className="messages-area custom-scrollbar">
              {messages.map((m) => (
                <div key={m.id} className={`message-row ${m.direction === 'out' ? 'out' : 'in'}`}>
                  <div className={`message-bubble ${m.direction === 'out' ? 'out' : 'in'}`}>
                    {(m.featured_image || m.media_url) && <img src={m.featured_image || m.media_url} style={{ maxWidth: 200, borderRadius: 8, display: 'block', marginBottom: 5 }} />}
                    {m.media_id && m.msg_type === 'image' && <img src={mediaProxyUrl(m.media_id)} style={{ maxWidth: 200, borderRadius: 8, display: 'block', marginBottom: 5 }} />}
                    {m.media_id && m.msg_type === 'audio' && <audio controls src={mediaProxyUrl(m.media_id)} style={{ marginTop: 5 }} />}
                    {m.media_id && m.msg_type === 'video' && <video controls src={mediaProxyUrl(m.media_id)} style={{ maxWidth: 200, borderRadius: 8 }} />}
                    <div className="msg-text">{m.text || m.media_caption}</div>
                  </div>
                  <div className="msg-meta">{fmtDateTime(m.created_at)}</div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            <div className="composer-area">
              <input ref={fileInputRef} type="file" style={{ display: 'none' }} onChange={handleFileUpload} />
              {showAttachMenu && <div className="attach-menu">
                <button onClick={() => { setFilePickKind("image"); fileInputRef.current.click(); setShowAttachMenu(false) }}>📷 Imagen</button>
                <button onClick={() => { setFilePickKind("video"); fileInputRef.current.click(); setShowAttachMenu(false) }}>🎥 Video</button>
                <button onClick={() => { setShowProductModal(true); setShowAttachMenu(false); loadWCProducts("") }}>🛍️ Producto</button>
              </div>}

              <div className="composer-input-wrapper">
                <button onClick={() => setShowAttachMenu(!showAttachMenu)} className="btn-attach"><IconPaperclip /></button>
                <button onClick={isRecording ? () => recorderRef.current.stop() : startRecording} className={`btn-attach ${isRecording ? 'recording' : ''}`}>🎤</button>
                <input className="composer-input" value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendMessage()} placeholder={isRecording ? `Grabando ${recordSeconds}s...` : "Escribe..."} />
                <button onClick={sendMessage} className="btn-send"><IconSend /></button>
              </div>
              {attachment && <div className="attach-preview">Adjunto: {attachment.msg_type} <button onClick={() => setAttachment(null)}>✕</button></div>}
            </div>
          </div>
          <CustomerCardCRM phone={selectedPhone} />

          {/* Modal Productos */}
          {showProductModal && <div className="modal-backdrop" onClick={() => setShowProductModal(false)}>
            <div className="modal" onClick={e => e.stopPropagation()}>
              <div className="modal-header"><h4>Enviar Producto</h4><button onClick={() => setShowProductModal(false)}>✕</button></div>
              <div className="modal-body">
                <div className="modal-search"><input autoFocus placeholder="Buscar..." value={prodQ} onChange={e => { setProdQ(e.target.value); loadWCProducts(e.target.value) }} /></div>
                <div className="product-grid">
                  {products.map(p => (
                    <div key={p.id} className="product-card">
                      <img src={p.featured_image} />
                      <div><h5>{p.name}</h5><p>${p.price}</p></div>
                      <button onClick={() => {
                        setAttachment({ kind: 'product', featured_image: p.featured_image, permalink: p.permalink, text: `✨ ${p.name}\n💰 $${p.price}` });
                        setShowProductModal(false);
                      }}>Seleccionar</button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>}
        </>
      ) : <div className="placeholder-view">En construcción</div>}
    </div>
  );
}