import React, { useState, useEffect, useRef, useMemo } from 'react';
import './App.css';




// --- CONFIGURACIÓN ---
const API_BASE = import.meta.env.VITE_API_BASE || "https://backend.perfumesverane.com";

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
const IconPaperclip = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21.44 11.05l-8.49 8.49a5 5 0 0 1-7.07-7.07l8.49-8.49a3.5 3.5 0 0 1 4.95 4.95l-8.5 8.5a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
  </svg>
);

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

  // 🎤 Audio recorder (WhatsApp-style)
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const recorderRef = useRef(null);
  const recChunksRef = useRef([]);
  const recTimerRef = useRef(null);




  const bottomRef = useRef(null);
  const messagesRef = useRef(null);
  const userNearBottomRef = useRef(true);

  const isNearBottom = (el, threshold = 120) => {
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  };


  const loadConversations = async () => {
    try {
      const r = await fetch(`${API_BASE}/api/conversations`);
      const data = await r.json();
      const list = data.conversations || [];
      setConversations(list);
    } catch (e) { console.error("Error cargando conversaciones", e); }
  };

  const scrollToBottom = (smooth = false) => {
  requestAnimationFrame(() => {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "auto" });
  });
};

  const loadMessages = async (phone) => {
  if (!phone) return;
  try {
    const r = await fetch(`${API_BASE}/api/conversations/${encodeURIComponent(phone)}/messages`);
    const data = await r.json();
    setMessages(data.messages || []);
    if (userNearBottomRef.current) {
    // 👇 fuerza scroll al final al cargar historial
    scrollToBottom(false);}
  } catch (e) { console.error(e); }
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
    setProdError("No se pudo cargar el catálogo (WooCommerce).");
    setProducts([]);
  } finally {
    setProdLoading(false);
  }
};

  const sendWCProduct = async (product) => {
    if (!selectedPhone) return;
    if (sendingProductId === product.id) return; // evita doble click

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

      // si backend devolvió error, muéstralo
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`send-product failed ${r.status}: ${t}`);
      }

      const out = await r.json();

      // si WhatsApp falló, el backend debería devolver sent:false + detalle
      if (out && out.sent === false) {
        console.error("WhatsApp send failed:", out);
        alert("Se guardó en la plataforma, pero WhatsApp NO lo envió. Revisa el error en consola/network.");
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
  ;

  const sendMessage = async () => {
    if (!selectedPhone) return;

    const hasText = !!text.trim();
    const hasAttachment = !!attachment;

    if (!hasText && !hasAttachment) return;

    let payload = {
      phone: selectedPhone,
      direction: "out",
      msg_type: "text",
      text: text.trim()
    };

    if (hasAttachment && attachment.kind === "media") {
      payload = {
        phone: selectedPhone,
        direction: "out",
        msg_type: attachment.msg_type,   // image|video|audio|document
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

const startRecording = async () => {
  if (!selectedPhone) return;

  // Si ya hay un adjunto, lo quitamos para evitar mezcla
  setAttachment(null);

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mr = new MediaRecorder(stream);
    recorderRef.current = mr;
    recChunksRef.current = [];

    mr.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) recChunksRef.current.push(e.data);
    };

    mr.onstop = async () => {
      // detener tracks del mic (importante)
      stream.getTracks().forEach(t => t.stop());

      const blob = new Blob(recChunksRef.current, { type: mr.mimeType || "audio/webm" });
      const file = new File([blob], `audio_${Date.now()}.webm`, { type: blob.type });

      try {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("kind", "audio");

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
          msg_type: "audio",
          media_id: data.media_id,
          filename: data.filename || file.name,
          mime_type: data.mime_type || blob.type,
          duration_sec: recordSeconds || null,
          file_size: file.size || null,
        });
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
    alert("No se pudo acceder al micrófono. Revisa permisos del navegador.");
  }
};

const stopRecording = async () => {
  try {
    if (recTimerRef.current) {
      clearInterval(recTimerRef.current);
      recTimerRef.current = null;
    }
    setIsRecording(false);

    const mr = recorderRef.current;
    recorderRef.current = null;

    if (mr && mr.state !== "inactive") {
      mr.stop();
    }
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
  // cuando llega un mensaje nuevo, sí puede ser smooth
    if (userNearBottomRef.current) {
      scrollToBottom(true);
    }
  }, [messages.length]);


  const selectedConversation = conversations.find(c => c.phone === selectedPhone);

  

  return (
    <div className="app-layout">
      

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
                        {selectedConversation?.updated_at ? `Último: ${fmtDateTime(selectedConversation.updated_at)}` : ''}
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

            <div
              ref={messagesRef}
              className="messages-area custom-scrollbar"
              onScroll={() => {
                userNearBottomRef.current = isNearBottom(messagesRef.current);
              }}
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

                    {/* ✅ PREVIEW: Imagen real enviada por media_id */}
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

                    {/* ✅ PREVIEW: Video */}
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

                    {/* ✅ PREVIEW: Audio */}
                    {m.msg_type === "audio" && m.media_id && (
                      <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 12, opacity: 0.85, marginBottom: 6 }}>
                          🎵 {m.file_name || "audio"} {m.duration_sec ? `• ${formatDur(m.duration_sec)}` : ""} {m.file_size ? `• ${formatBytes(m.file_size)}` : ""}
                        </div>
                        <audio controls preload="metadata" style={{ width: 280 }} src={mediaProxyUrl(m.media_id)} />
                      </div>
                    )}

                    {/* ✅ PREVIEW: Documento */}
                    {m.msg_type === "document" && m.media_id && (
                      <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 6 }}>
                          📄 {m.file_name || "documento"} {m.file_size ? `• ${formatBytes(m.file_size)}` : ""}
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

                    {/* ✅ Texto / caption */}
                   
                    {/* ✅ Foto real (productos) */}
                    

                    <div className="msg-text">{m.text || m.media_caption || ""}</div>


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
                    🎥 Video
                  </button>
                  <button onClick={() => { setFilePickKind("document"); fileInputRef.current?.click(); setShowAttachMenu(false); }}>
                    📄 Documento
                  </button>
                  <button onClick={() => { setFilePickKind("audio"); fileInputRef.current?.click(); setShowAttachMenu(false); }}>
                    🎙️ Audio
                  </button>
                  <button onClick={() => {
                    setShowProductModal(true);
                    setShowAttachMenu(false);
                    loadWCProducts(prodQ);
                  }}>
                    🛍️ Producto (Catálogo)
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
                  title={isRecording ? "Detener grabación" : "Grabar audio"}
                >
                  🎤
                </button>


                <input
                  className="composer-input"
                  placeholder={isRecording ? `Grabando... ${fmtTimer(recordSeconds)} (clic en 🎤 para detener)` : "Escribe un mensaje..."}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                  disabled={!selectedPhone || isRecording}
                />

                <button
                  onClick={sendMessage}
                  disabled={!text.trim() && !attachment}
                  className="btn-send"
                >
                  <IconSend />
                </button>
              </div>

              {attachment && (
                <div className="attach-preview">
                  <div className="ap-meta">
                    <p className="ap-title">
                      {attachment.kind === "product" ? "Producto adjunto ✅" : "Archivo adjunto ✅"}
                    </p>
                    <p className="ap-sub">
                      {attachment.kind === "product"
                        ? (attachment.permalink || "")
                        : (attachment.filename || attachment.mime_type || attachment.media_id)
                      }
                    </p>
                  </div>
                  <button className="ap-remove" onClick={() => setAttachment(null)} title="Quitar">✕</button>
                </div>
              )}
            </div>

            {/* MODAL PRODUCTOS */}
            {showProductModal && (
              <div className="modal-backdrop" onClick={() => setShowProductModal(false)}>
                <div className="modal" onClick={(e) => e.stopPropagation()}>
                  <div className="modal-header">
                    <h4>Adjuntar producto</h4>
                    <button className="modal-close" onClick={() => setShowProductModal(false)}>✕</button>
                  </div>
                  <div className="modal-body">
                    <div className="modal-search">
                      <input
                          placeholder="Buscar perfume..."
                          value={prodQ}
                          onChange={(e) => {
                            const v = e.target.value;
                            setProdQ(v);
                            // búsqueda en vivo (simple)
                            loadWCProducts(v);
                          }}
                          autoFocus
                        />

                    </div>

                    <div className="product-grid">
                        {prodLoading && <div style={{ color: "#94a3b8" }}>Cargando catálogo...</div>}
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
                              <button
                                onClick={() => sendWCProduct(p)}
                                disabled={sendingProductId === p.id}
                              >
                                {sendingProductId === p.id ? "Enviando..." : "Enviar"}
                              </button>

                            </div>
                          </div>
                        ))}

                        {!prodLoading && !prodError && (!products || products.length === 0) && (
                          <div style={{ color: "#94a3b8" }}>No hay productos para esa búsqueda.</div>
                        )}
                      </div>


                  </div>
                </div>
              </div>
            )}

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
