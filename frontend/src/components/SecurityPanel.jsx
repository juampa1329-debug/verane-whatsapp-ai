import React, { useMemo, useState } from "react";
import useViewport from "../hooks/useViewport";

const panel = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 14,
  background: "rgba(255,255,255,0.02)",
};

const card = {
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

const btn = {
  padding: "8px 12px",
  borderRadius: 9,
  border: "1px solid rgba(255,255,255,0.16)",
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
};

const dangerBtn = {
  ...btn,
  border: "1px solid rgba(255,120,120,0.55)",
  color: "#ffb7b7",
};

const roleColor = {
  admin: "rgba(251,191,36,0.28)",
  supervisor: "rgba(96,165,250,0.28)",
  agente: "rgba(52,211,153,0.28)",
};

function fmtDate(v) {
  if (!v) return "-";
  try {
    return new Date(v).toLocaleString();
  } catch {
    return String(v);
  }
}

function maskKey(v) {
  const s = String(v || "");
  if (s.length <= 8) return "********";
  return `${s.slice(0, 4)}****${s.slice(-4)}`;
}

export default function SecurityPanel({ apiBase }) {
  const API = (apiBase || "").replace(/\/$/, "");
  const { isMobile, isTablet } = useViewport();

  const [status, setStatus] = useState("");
  const [policy, setPolicy] = useState({
    password_min_length: 10,
    require_special_chars: true,
    access_token_minutes: 15,
    refresh_token_days: 15,
    session_idle_minutes: 30,
    session_absolute_hours: 12,
    max_failed_attempts: 5,
    lock_minutes: 15,
    force_password_rotation_days: 90,
  });

  const [mfa, setMfa] = useState({
    enforce_for_admins: true,
    enforce_for_supervisors: true,
    allow_for_agents: false,
    backup_codes_enabled: true,
  });

  const [alerts, setAlerts] = useState({
    failed_login_alert: true,
    suspicious_ip_alert: true,
    security_change_alert: true,
    webhook_failure_alert: true,
    channel_email: true,
    channel_whatsapp: false,
  });

  const [users, setUsers] = useState([
    { id: 1, name: "Administrador", email: "admin@verane.com", role: "admin", twofa: true, active: true, last_login: new Date().toISOString() },
    { id: 2, name: "Supervisor CRM", email: "supervisor@verane.com", role: "supervisor", twofa: true, active: true, last_login: new Date(Date.now() - 3600 * 1000 * 4).toISOString() },
    { id: 3, name: "Asesor Ventas", email: "asesor@verane.com", role: "agente", twofa: false, active: true, last_login: new Date(Date.now() - 3600 * 1000 * 28).toISOString() },
  ]);

  const [draftUser, setDraftUser] = useState({
    name: "",
    email: "",
    role: "agente",
    require_2fa: false,
  });

  const [sessions, setSessions] = useState([
    { id: "s_1", user: "Administrador", device: "Chrome / Windows", ip: "186.31.90.21", created_at: new Date(Date.now() - 1000 * 60 * 55).toISOString(), last_seen: new Date().toISOString() },
    { id: "s_2", user: "Supervisor CRM", device: "Safari / iPhone", ip: "190.66.10.7", created_at: new Date(Date.now() - 1000 * 60 * 240).toISOString(), last_seen: new Date(Date.now() - 1000 * 60 * 8).toISOString() },
  ]);

  const [keys, setKeys] = useState([
    { id: "k_wa", name: "WhatsApp Cloud Token", value: "EAAJZZxxa1b2c3d4e5f6", updated_at: new Date(Date.now() - 86400000 * 2).toISOString(), scope: "mensajeria" },
    { id: "k_wc", name: "WooCommerce Consumer Key", value: "ck_1234567890abcdef", updated_at: new Date(Date.now() - 86400000 * 7).toISOString(), scope: "catalogo" },
    { id: "k_ai", name: "Proveedor IA Principal", value: "sk-abc123xyz987", updated_at: new Date(Date.now() - 86400000).toISOString(), scope: "inferencia" },
  ]);

  const [auditFilter, setAuditFilter] = useState("all");
  const [auditEvents] = useState([
    { id: "a1", level: "high", action: "Cambio de política de sesión", actor: "Administrador", ip: "186.31.90.21", created_at: new Date(Date.now() - 1000 * 60 * 40).toISOString() },
    { id: "a2", level: "medium", action: "Usuario bloqueado temporalmente", actor: "Sistema", ip: "190.66.10.7", created_at: new Date(Date.now() - 1000 * 60 * 180).toISOString() },
    { id: "a3", level: "low", action: "Rotación de API key (Woo)", actor: "Administrador", ip: "186.31.90.21", created_at: new Date(Date.now() - 1000 * 60 * 520).toISOString() },
  ]);

  const summary = useMemo(() => {
    const activeUsers = users.filter((u) => u.active).length;
    const with2fa = users.filter((u) => u.twofa).length;
    return [
      { title: "Usuarios activos", value: activeUsers },
      { title: "2FA habilitado", value: `${with2fa}/${users.length}` },
      { title: "Sesiones abiertas", value: sessions.length },
      { title: "Eventos críticos (24h)", value: auditEvents.filter((e) => e.level === "high").length },
    ];
  }, [users, sessions, auditEvents]);

  const filteredAudit = useMemo(() => {
    if (auditFilter === "all") return auditEvents;
    return auditEvents.filter((e) => e.level === auditFilter);
  }, [auditEvents, auditFilter]);

  const summaryCols = isMobile ? "1fr" : isTablet ? "repeat(2, minmax(0, 1fr))" : "repeat(4, minmax(0, 1fr))";
  const formCols = isMobile ? "1fr" : "repeat(2, minmax(0, 1fr))";

  const pingStatus = (txt) => {
    setStatus(txt);
    setTimeout(() => setStatus(""), 2400);
  };

  const createUser = () => {
    const name = String(draftUser.name || "").trim();
    const email = String(draftUser.email || "").trim();
    if (!name || !email) {
      pingStatus("Completa nombre y email para crear usuario.");
      return;
    }
    const id = Math.max(0, ...users.map((u) => Number(u.id || 0))) + 1;
    setUsers((prev) => [
      {
        id,
        name,
        email,
        role: draftUser.role || "agente",
        twofa: !!draftUser.require_2fa,
        active: true,
        last_login: null,
      },
      ...prev,
    ]);
    setDraftUser({ name: "", email: "", role: "agente", require_2fa: false });
    pingStatus("Usuario agregado (UI). Pendiente conexión backend.");
  };

  const toggleUserActive = (id) => {
    setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, active: !u.active } : u)));
    pingStatus("Estado de usuario actualizado (UI).");
  };

  const revokeSession = (id) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    pingStatus("Sesión revocada (UI).");
  };

  const revokeAllSessions = () => {
    setSessions([]);
    pingStatus("Todas las sesiones fueron revocadas (UI).");
  };

  const rotateKey = (id) => {
    setKeys((prev) =>
      prev.map((k) => {
        if (k.id !== id) return k;
        const tail = Math.random().toString(36).slice(2, 10);
        return {
          ...k,
          value: `${k.value.slice(0, 4)}${tail}`,
          updated_at: new Date().toISOString(),
        };
      })
    );
    pingStatus("Clave rotada (UI). Pendiente conexión segura backend.");
  };

  return (
    <div className="custom-scrollbar" style={{ width: "100%", minHeight: 0, overflowY: "auto", display: "grid", gap: 12 }}>
      <div style={{ ...panel, padding: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <div>
            <h2 style={{ margin: 0 }}>Seguridad</h2>
            <div style={{ fontSize: 12, opacity: 0.8 }}>Diseño funcional listo para conectar a backend.</div>
            <div style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>API base: {API || "(no definida)"}</div>
          </div>
          <button style={btn} onClick={() => pingStatus("Configuración de seguridad guardada (UI).")}>Guardar diseño</button>
        </div>
        {status ? <div style={{ marginTop: 8, fontSize: 12, color: "#9be15d" }}>{status}</div> : null}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: summaryCols, gap: 10 }}>
        {summary.map((s) => (
          <div key={s.title} style={card}>
            <div style={{ fontSize: 12, opacity: 0.75 }}>{s.title}</div>
            <div style={{ fontSize: 28, fontWeight: 800, lineHeight: 1.1, marginTop: 4 }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ ...panel, padding: 14, display: "grid", gap: 10 }}>
        <h3 style={{ margin: 0 }}>Autenticación y políticas</h3>
        <div style={{ display: "grid", gridTemplateColumns: formCols, gap: 8 }}>
          <label>
            <div style={{ fontSize: 12, marginBottom: 4 }}>Mínimo caracteres contraseña</div>
            <input style={input} type="number" min={8} value={policy.password_min_length} onChange={(e) => setPolicy((p) => ({ ...p, password_min_length: Number(e.target.value || 8) }))} />
          </label>
          <label>
            <div style={{ fontSize: 12, marginBottom: 4 }}>Access token (min)</div>
            <input style={input} type="number" min={5} value={policy.access_token_minutes} onChange={(e) => setPolicy((p) => ({ ...p, access_token_minutes: Number(e.target.value || 15) }))} />
          </label>
          <label>
            <div style={{ fontSize: 12, marginBottom: 4 }}>Refresh token (días)</div>
            <input style={input} type="number" min={1} value={policy.refresh_token_days} onChange={(e) => setPolicy((p) => ({ ...p, refresh_token_days: Number(e.target.value || 15) }))} />
          </label>
          <label>
            <div style={{ fontSize: 12, marginBottom: 4 }}>Bloqueo por intentos fallidos (min)</div>
            <input style={input} type="number" min={1} value={policy.lock_minutes} onChange={(e) => setPolicy((p) => ({ ...p, lock_minutes: Number(e.target.value || 15) }))} />
          </label>
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={policy.require_special_chars} onChange={(e) => setPolicy((p) => ({ ...p, require_special_chars: e.target.checked }))} />
            Requerir caracteres especiales
          </label>
        </div>
      </div>

      <div style={{ ...panel, padding: 14, display: "grid", gap: 10 }}>
        <h3 style={{ margin: 0 }}>Usuarios y roles</h3>
        <div style={{ display: "grid", gridTemplateColumns: formCols, gap: 8 }}>
          <input style={input} placeholder="Nombre" value={draftUser.name} onChange={(e) => setDraftUser((p) => ({ ...p, name: e.target.value }))} />
          <input style={input} placeholder="Email" value={draftUser.email} onChange={(e) => setDraftUser((p) => ({ ...p, email: e.target.value }))} />
          <select style={input} value={draftUser.role} onChange={(e) => setDraftUser((p) => ({ ...p, role: e.target.value }))}>
            <option value="admin">admin</option>
            <option value="supervisor">supervisor</option>
            <option value="agente">agente</option>
          </select>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={draftUser.require_2fa} onChange={(e) => setDraftUser((p) => ({ ...p, require_2fa: e.target.checked }))} />
            Requerir 2FA al crear
          </label>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button style={btn} onClick={createUser}>Crear usuario</button>
        </div>

        <div className="custom-scrollbar" style={{ maxHeight: 320, overflowY: "auto", display: "grid", gap: 8, paddingRight: 4 }}>
          {users.map((u) => (
            <div key={u.id} style={{ ...card, display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <div>
                <div style={{ fontWeight: 700 }}>{u.name}</div>
                <div style={{ fontSize: 12, opacity: 0.8 }}>{u.email}</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                  <span style={{ fontSize: 11, borderRadius: 999, padding: "3px 8px", border: "1px solid rgba(255,255,255,0.2)", background: roleColor[u.role] || "transparent" }}>{u.role}</span>
                  <span style={{ fontSize: 11, borderRadius: 999, padding: "3px 8px", border: "1px solid rgba(255,255,255,0.2)" }}>{u.twofa ? "2FA ON" : "2FA OFF"}</span>
                  <span style={{ fontSize: 11, borderRadius: 999, padding: "3px 8px", border: "1px solid rgba(255,255,255,0.2)" }}>{u.active ? "Activo" : "Bloqueado"}</span>
                </div>
                <div style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>Último login: {fmtDate(u.last_login)}</div>
              </div>
              <button style={u.active ? dangerBtn : btn} onClick={() => toggleUserActive(u.id)}>{u.active ? "Bloquear" : "Activar"}</button>
            </div>
          ))}
        </div>
      </div>

      <div style={{ ...panel, padding: 14, display: "grid", gap: 10 }}>
        <h3 style={{ margin: 0 }}>2FA y sesiones</h3>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={mfa.enforce_for_admins} onChange={(e) => setMfa((p) => ({ ...p, enforce_for_admins: e.target.checked }))} />
            Forzar 2FA en admins
          </label>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={mfa.enforce_for_supervisors} onChange={(e) => setMfa((p) => ({ ...p, enforce_for_supervisors: e.target.checked }))} />
            Forzar 2FA en supervisores
          </label>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={mfa.allow_for_agents} onChange={(e) => setMfa((p) => ({ ...p, allow_for_agents: e.target.checked }))} />
            Permitir 2FA en agentes
          </label>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={mfa.backup_codes_enabled} onChange={(e) => setMfa((p) => ({ ...p, backup_codes_enabled: e.target.checked }))} />
            Códigos de respaldo
          </label>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <h4 style={{ margin: 0 }}>Sesiones activas</h4>
          <button style={dangerBtn} onClick={revokeAllSessions}>Revocar todas</button>
        </div>

        <div className="custom-scrollbar" style={{ maxHeight: 280, overflowY: "auto", display: "grid", gap: 8, paddingRight: 4 }}>
          {sessions.map((s) => (
            <div key={s.id} style={{ ...card, display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 700 }}>{s.user}</div>
                <div style={{ fontSize: 12, opacity: 0.82 }}>{s.device} | IP: {s.ip}</div>
                <div style={{ fontSize: 11, opacity: 0.72 }}>Creada: {fmtDate(s.created_at)} | Última actividad: {fmtDate(s.last_seen)}</div>
              </div>
              <button style={dangerBtn} onClick={() => revokeSession(s.id)}>Revocar</button>
            </div>
          ))}
          {sessions.length === 0 ? <div style={{ opacity: 0.75 }}>No hay sesiones activas.</div> : null}
        </div>
      </div>

      <div style={{ ...panel, padding: 14, display: "grid", gap: 10 }}>
        <h3 style={{ margin: 0 }}>Claves y secretos</h3>
        <div className="custom-scrollbar" style={{ maxHeight: 260, overflowY: "auto", display: "grid", gap: 8, paddingRight: 4 }}>
          {keys.map((k) => (
            <div key={k.id} style={{ ...card, display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <div>
                <div style={{ fontWeight: 700 }}>{k.name}</div>
                <div style={{ fontSize: 12, opacity: 0.85 }}>Scope: {k.scope}</div>
                <div style={{ fontFamily: "monospace", fontSize: 12, opacity: 0.88, marginTop: 4 }}>{maskKey(k.value)}</div>
                <div style={{ fontSize: 11, opacity: 0.72, marginTop: 3 }}>Última rotación: {fmtDate(k.updated_at)}</div>
              </div>
              <button style={btn} onClick={() => rotateKey(k.id)}>Rotar</button>
            </div>
          ))}
        </div>
      </div>

      <div style={{ ...panel, padding: 14, display: "grid", gap: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <h3 style={{ margin: 0 }}>Auditoría y alertas</h3>
          <select style={{ ...input, width: isMobile ? "100%" : 220 }} value={auditFilter} onChange={(e) => setAuditFilter(e.target.value)}>
            <option value="all">Eventos: todos</option>
            <option value="high">Eventos: alta severidad</option>
            <option value="medium">Eventos: media severidad</option>
            <option value="low">Eventos: baja severidad</option>
          </select>
        </div>

        <div className="custom-scrollbar" style={{ maxHeight: 220, overflowY: "auto", display: "grid", gap: 8, paddingRight: 4 }}>
          {filteredAudit.map((e) => (
            <div key={e.id} style={{ ...card, display: "grid", gap: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <strong>{e.action}</strong>
                <span style={{ fontSize: 11, opacity: 0.78 }}>{e.level}</span>
              </div>
              <div style={{ fontSize: 12, opacity: 0.8 }}>actor: {e.actor} | ip: {e.ip}</div>
              <div style={{ fontSize: 11, opacity: 0.7 }}>{fmtDate(e.created_at)}</div>
            </div>
          ))}
          {filteredAudit.length === 0 ? <div style={{ opacity: 0.75 }}>Sin eventos para ese filtro.</div> : null}
        </div>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={alerts.failed_login_alert} onChange={(e) => setAlerts((p) => ({ ...p, failed_login_alert: e.target.checked }))} />
            Alertar intentos fallidos
          </label>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={alerts.suspicious_ip_alert} onChange={(e) => setAlerts((p) => ({ ...p, suspicious_ip_alert: e.target.checked }))} />
            Alertar IP sospechosa
          </label>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={alerts.security_change_alert} onChange={(e) => setAlerts((p) => ({ ...p, security_change_alert: e.target.checked }))} />
            Alertar cambios críticos
          </label>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={alerts.webhook_failure_alert} onChange={(e) => setAlerts((p) => ({ ...p, webhook_failure_alert: e.target.checked }))} />
            Alertar fallas webhook
          </label>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={alerts.channel_email} onChange={(e) => setAlerts((p) => ({ ...p, channel_email: e.target.checked }))} />
            Canal email
          </label>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={alerts.channel_whatsapp} onChange={(e) => setAlerts((p) => ({ ...p, channel_whatsapp: e.target.checked }))} />
            Canal WhatsApp
          </label>
        </div>
      </div>
    </div>
  );
}

