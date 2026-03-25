import React, { useEffect, useMemo, useState } from "react";
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

const POLICY_FIELDS = [
  "password_min_length",
  "require_special_chars",
  "access_token_minutes",
  "refresh_token_days",
  "session_idle_minutes",
  "session_absolute_hours",
  "max_failed_attempts",
  "lock_minutes",
  "force_password_rotation_days",
];

const MFA_FIELDS = [
  "enforce_for_admins",
  "enforce_for_supervisors",
  "allow_for_agents",
  "backup_codes_enabled",
];

const ALERT_FIELDS = [
  "failed_login_alert",
  "suspicious_ip_alert",
  "security_change_alert",
  "webhook_failure_alert",
  "channel_email",
  "channel_whatsapp",
];

const TOKEN_STORAGE_KEY = "verane_security_bearer_token";

function pickFields(source, fields) {
  const out = {};
  for (const key of fields) {
    if (Object.prototype.hasOwnProperty.call(source || {}, key)) {
      out[key] = source[key];
    }
  }
  return out;
}

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
  if (!s) return "********";
  if (s.includes("...")) return s;
  if (s.length <= 8) return "********";
  return `${s.slice(0, 4)}****${s.slice(-4)}`;
}

export default function SecurityPanel({ apiBase }) {
  const API = (apiBase || "").replace(/\/$/, "");
  const { isMobile, isTablet } = useViewport();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [statusTone, setStatusTone] = useState("ok");
  const [authMode, setAuthMode] = useState({ enabled: false, open_mode: true, configured_roles: [] });
  const [rotationStatus, setRotationStatus] = useState({ enabled: false, running: false, interval_sec: 0 });
  const [securityToken, setSecurityToken] = useState(() => {
    try {
      const fromStorage = localStorage.getItem(TOKEN_STORAGE_KEY) || "";
      const fromEnv = import.meta.env.VITE_SECURITY_BEARER_TOKEN || "";
      return String(fromStorage || fromEnv || "").trim();
    } catch {
      return "";
    }
  });

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

  const [users, setUsers] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [keys, setKeys] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [auditFilter, setAuditFilter] = useState("all");

  const [draftUser, setDraftUser] = useState({
    name: "",
    email: "",
    role: "agente",
    require_2fa: false,
  });
  const [draftKey, setDraftKey] = useState({
    name: "",
    scope: "general",
    rotation_days: 90,
  });

  const summary = useMemo(() => {
    const activeUsers = users.filter((u) => u.active).length;
    const with2fa = users.filter((u) => u.twofa).length;
    return [
      { title: "Usuarios activos", value: activeUsers },
      { title: "2FA habilitado", value: `${with2fa}/${users.length}` },
      { title: "Sesiones abiertas", value: sessions.length },
      { title: "Eventos criticos (24h)", value: auditEvents.filter((e) => String(e.level || "").toLowerCase() === "high").length },
    ];
  }, [users, sessions, auditEvents]);

  const summaryCols = isMobile ? "1fr" : isTablet ? "repeat(2, minmax(0, 1fr))" : "repeat(4, minmax(0, 1fr))";
  const formCols = isMobile ? "1fr" : "repeat(2, minmax(0, 1fr))";

  const pingStatus = (text, tone = "ok") => {
    setStatus(text);
    setStatusTone(tone);
    setTimeout(() => setStatus(""), 3500);
  };

  const apiCall = async (path, options = {}) => {
    const url = `${API}${path}`;
    const opts = {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(securityToken ? { Authorization: `Bearer ${securityToken}` } : {}),
        ...(options.headers || {}),
      },
    };
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = String(data?.detail || data?.error || `HTTP ${res.status}`);
      throw new Error(detail);
    }
    return data;
  };

  const loadAuthMode = async () => {
    if (!API) return;
    try {
      const res = await fetch(`${API}/api/security/auth/mode`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return;
      setAuthMode({
        enabled: !!data?.enabled,
        open_mode: !!data?.open_mode,
        configured_roles: Array.isArray(data?.configured_roles) ? data.configured_roles : [],
      });
    } catch {
      // noop
    }
  };

  const loadRotationStatus = async () => {
    if (!API) return;
    try {
      const data = await apiCall("/api/security/rotation/status");
      setRotationStatus({
        enabled: !!data?.enabled,
        running: !!data?.running,
        interval_sec: Number(data?.interval_sec || 0),
      });
    } catch {
      // noop
    }
  };

  const loadState = async (showLoading = false) => {
    if (!API) return;
    if (showLoading) setLoading(true);
    try {
      const data = await apiCall(`/api/security/state?audit_level=${encodeURIComponent(auditFilter)}&audit_limit=80`);
      setPolicy((prev) => ({ ...prev, ...(data?.policy || {}) }));
      setMfa((prev) => ({ ...prev, ...(data?.mfa || {}) }));
      setAlerts((prev) => ({ ...prev, ...(data?.alerts || {}) }));
      setUsers(Array.isArray(data?.users) ? data.users : []);
      setSessions(Array.isArray(data?.sessions) ? data.sessions : []);
      setKeys(Array.isArray(data?.keys) ? data.keys : []);
      setAuditEvents(Array.isArray(data?.audit_events) ? data.audit_events : []);
    } catch (err) {
      pingStatus(`No se pudo cargar seguridad: ${String(err.message || err)}`, "error");
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const loadAudit = async (level) => {
    if (!API) return;
    try {
      const data = await apiCall(`/api/security/audit?level=${encodeURIComponent(level || "all")}&limit=120`);
      setAuditEvents(Array.isArray(data?.events) ? data.events : []);
    } catch (err) {
      pingStatus(`No se pudo cargar auditoria: ${String(err.message || err)}`, "error");
    }
  };

  const saveSecurityToken = () => {
    try {
      const tok = String(securityToken || "").trim();
      if (tok) localStorage.setItem(TOKEN_STORAGE_KEY, tok);
      else localStorage.removeItem(TOKEN_STORAGE_KEY);
      pingStatus(tok ? "Token de seguridad guardado." : "Token de seguridad eliminado.");
    } catch {
      pingStatus("No se pudo guardar token local.", "error");
    }
  };

  useEffect(() => {
    loadAuthMode();
    loadRotationStatus();
    loadState(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [API, securityToken]);

  useEffect(() => {
    if (loading) return;
    loadAudit(auditFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auditFilter]);

  const saveAll = async () => {
    setSaving(true);
    try {
      await apiCall("/api/security/policy", {
        method: "PUT",
        body: JSON.stringify(pickFields(policy, POLICY_FIELDS)),
      });
      await apiCall("/api/security/mfa", {
        method: "PUT",
        body: JSON.stringify(pickFields(mfa, MFA_FIELDS)),
      });
      await apiCall("/api/security/alerts", {
        method: "PUT",
        body: JSON.stringify(pickFields(alerts, ALERT_FIELDS)),
      });
      await loadState(false);
      await loadAudit(auditFilter);
      pingStatus("Seguridad guardada correctamente.");
    } catch (err) {
      pingStatus(`Error guardando seguridad: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const createUser = async () => {
    const name = String(draftUser.name || "").trim();
    const email = String(draftUser.email || "").trim();
    if (!name || !email) {
      pingStatus("Completa nombre y email para crear usuario.", "error");
      return;
    }

    setSaving(true);
    try {
      const data = await apiCall("/api/security/users", {
        method: "POST",
        body: JSON.stringify({
          name,
          email,
          role: draftUser.role || "agente",
          twofa: !!draftUser.require_2fa,
          active: true,
        }),
      });
      setDraftUser({ name: "", email: "", role: "agente", require_2fa: false });
      await loadState(false);
      await loadAudit(auditFilter);
      const tempPassword = String(data?.temp_password || "").trim();
      const twofaPending = !!data?.twofa_pending_setup;
      if (twofaPending) {
        const setupSecret = String(data?.twofa_setup_secret || "").trim();
        const newUserId = Number(data?.user?.id || 0);
        const code = window.prompt(
          `Usuario creado. Clave temporal: ${tempPassword || "(no entregada)"}\n2FA pendiente. Secret OTP: ${setupSecret}\nIngresa el código OTP para activar 2FA ahora:`,
          ""
        );
        if (code && newUserId > 0) {
          await apiCall(`/api/security/users/${newUserId}/2fa/verify`, {
            method: "POST",
            body: JSON.stringify({ code: String(code).trim() }),
          });
          await loadState(false);
          await loadAudit(auditFilter);
          pingStatus("Usuario creado y 2FA activado.");
        } else {
          pingStatus("Usuario creado. 2FA quedó pendiente de verificación.", "error");
        }
      } else if (tempPassword) {
        pingStatus(`Usuario creado. Clave temporal: ${tempPassword}`);
      } else {
        pingStatus("Usuario creado correctamente.");
      }
    } catch (err) {
      pingStatus(`No se pudo crear usuario: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const toggleUserActive = async (id, currentActive) => {
    setSaving(true);
    try {
      await apiCall(`/api/security/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ active: !currentActive }),
      });
      await loadState(false);
      await loadAudit(auditFilter);
      pingStatus("Estado de usuario actualizado.");
    } catch (err) {
      pingStatus(`No se pudo actualizar usuario: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const resetUserPassword = async (id) => {
    setSaving(true);
    try {
      const data = await apiCall(`/api/security/users/${id}/password/reset`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await loadAudit(auditFilter);
      const tempPassword = String(data?.temp_password || "").trim();
      if (tempPassword) {
        pingStatus(`Contraseña reseteada. Nueva clave: ${tempPassword}`);
      } else {
        pingStatus("Contraseña reseteada.");
      }
    } catch (err) {
      pingStatus(`No se pudo resetear contraseña: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const configureUser2fa = async (user) => {
    const userId = Number(user?.id || 0);
    if (userId <= 0) return;
    setSaving(true);
    try {
      if (user?.twofa) {
        await apiCall(`/api/security/users/${userId}/2fa/disable`, { method: "POST" });
        await loadState(false);
        await loadAudit(auditFilter);
        pingStatus("2FA desactivado para el usuario.");
        return;
      }

      const setup = await apiCall(`/api/security/users/${userId}/2fa/setup`, { method: "POST" });
      const secret = String(setup?.secret || "").trim();
      const code = window.prompt(
        `Configura el usuario en tu app OTP y escribe el código de verificación.\nSecret: ${secret}`,
        ""
      );
      if (!code) {
        pingStatus("2FA pendiente de verificación. Vuelve a intentarlo con código OTP.", "error");
        return;
      }
      await apiCall(`/api/security/users/${userId}/2fa/verify`, {
        method: "POST",
        body: JSON.stringify({ code: String(code).trim() }),
      });
      await loadState(false);
      await loadAudit(auditFilter);
      pingStatus("2FA activado correctamente.");
    } catch (err) {
      pingStatus(`No se pudo configurar 2FA: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const revokeSession = async (id) => {
    setSaving(true);
    try {
      await apiCall(`/api/security/sessions/${encodeURIComponent(id)}/revoke`, {
        method: "POST",
      });
      await loadState(false);
      await loadAudit(auditFilter);
      pingStatus("Sesion revocada.");
    } catch (err) {
      pingStatus(`No se pudo revocar sesion: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const revokeAllSessions = async () => {
    setSaving(true);
    try {
      await apiCall("/api/security/sessions/revoke-all", { method: "POST" });
      await loadState(false);
      await loadAudit(auditFilter);
      pingStatus("Todas las sesiones fueron revocadas.");
    } catch (err) {
      pingStatus(`No se pudo revocar sesiones: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const rotateKey = async (id) => {
    setSaving(true);
    try {
      const data = await apiCall(`/api/security/keys/${id}/rotate`, { method: "POST" });
      await loadState(false);
      await loadAudit(auditFilter);
      const plain = String(data?.plain_secret || "").trim();
      if (plain) {
        pingStatus(`Key rotada. Nuevo secreto: ${plain}`);
      } else {
        pingStatus("Key rotada correctamente.");
      }
    } catch (err) {
      pingStatus(`No se pudo rotar key: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const createKey = async () => {
    const name = String(draftKey.name || "").trim();
    const scope = String(draftKey.scope || "general").trim().toLowerCase();
    const rotationDays = Number(draftKey.rotation_days || 90);
    if (!name) {
      pingStatus("Debes indicar nombre para la API key.", "error");
      return;
    }
    setSaving(true);
    try {
      const data = await apiCall("/api/security/keys", {
        method: "POST",
        body: JSON.stringify({
          name,
          scope: scope || "general",
          rotation_days: Math.max(1, Math.min(3650, rotationDays || 90)),
        }),
      });
      await loadState(false);
      await loadAudit(auditFilter);
      const plain = String(data?.plain_secret || "").trim();
      if (plain) {
        pingStatus(`API key creada. Secreto: ${plain}`);
      } else {
        pingStatus("API key creada.");
      }
      setDraftKey({ name: "", scope: "general", rotation_days: 90 });
    } catch (err) {
      pingStatus(`No se pudo crear API key: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const revealKey = async (id) => {
    setSaving(true);
    try {
      const data = await apiCall(`/api/security/keys/${id}/reveal`, { method: "POST" });
      const plain = String(data?.plain_secret || "").trim();
      if (plain) {
        pingStatus(`Secreto actual: ${plain}`);
      } else {
        pingStatus("No se pudo revelar el secreto.", "error");
      }
      await loadAudit(auditFilter);
    } catch (err) {
      pingStatus(`No se pudo revelar key: ${String(err.message || err)}`, "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ ...panel, padding: 14 }}>
        <div>Cargando modulo de seguridad...</div>
      </div>
    );
  }

  return (
    <div className="custom-scrollbar" style={{ width: "100%", minHeight: 0, overflowY: "auto", display: "grid", gap: 12 }}>
      <div style={{ ...panel, padding: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <div>
            <h2 style={{ margin: 0 }}>Seguridad</h2>
            <div style={{ fontSize: 12, opacity: 0.8 }}>Panel conectado a backend para gestionar usuarios, sesiones y llaves.</div>
            <div style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>API base: {API || "(no definida)"}</div>
            <div style={{ fontSize: 11, opacity: 0.7, marginTop: 2 }}>
              Modo auth: {authMode.enabled ? `PROTEGIDO (${(authMode.configured_roles || []).join(", ") || "roles configurados"})` : "ABIERTO"}
            </div>
            <div style={{ fontSize: 11, opacity: 0.7, marginTop: 2 }}>
              Rotación automática: {rotationStatus.enabled ? (rotationStatus.running ? `activa cada ${rotationStatus.interval_sec}s` : "habilitada (sin task)") : "deshabilitada"}
            </div>
          </div>
          <div style={{ display: "grid", gap: 6, minWidth: isMobile ? "100%" : 320 }}>
            <div style={{ display: "flex", gap: 6 }}>
              <input
                style={input}
                type="password"
                placeholder="Bearer token seguridad (opcional)"
                value={securityToken}
                onChange={(e) => setSecurityToken(e.target.value)}
              />
              <button style={btn} onClick={saveSecurityToken}>Token</button>
            </div>
            <button style={btn} onClick={saveAll} disabled={saving}>{saving ? "Guardando..." : "Guardar cambios"}</button>
          </div>
        </div>
        {status ? (
          <div style={{ marginTop: 8, fontSize: 12, color: statusTone === "error" ? "#fca5a5" : "#9be15d" }}>
            {status}
          </div>
        ) : null}
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
        <h3 style={{ margin: 0 }}>Autenticacion y politicas</h3>
        <div style={{ display: "grid", gridTemplateColumns: formCols, gap: 8 }}>
          <label>
            <div style={{ fontSize: 12, marginBottom: 4 }}>Minimo caracteres contrasena</div>
            <input style={input} type="number" min={8} value={policy.password_min_length} onChange={(e) => setPolicy((p) => ({ ...p, password_min_length: Number(e.target.value || 8) }))} />
          </label>
          <label>
            <div style={{ fontSize: 12, marginBottom: 4 }}>Access token (min)</div>
            <input style={input} type="number" min={5} value={policy.access_token_minutes} onChange={(e) => setPolicy((p) => ({ ...p, access_token_minutes: Number(e.target.value || 15) }))} />
          </label>
          <label>
            <div style={{ fontSize: 12, marginBottom: 4 }}>Refresh token (dias)</div>
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
          <button style={btn} onClick={createUser} disabled={saving}>{saving ? "Procesando..." : "Crear usuario"}</button>
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
                <div style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>Ultimo login: {fmtDate(u.last_login)}</div>
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <button style={btn} onClick={() => configureUser2fa(u)} disabled={saving}>{u.twofa ? "2FA OFF" : "2FA ON"}</button>
                <button style={btn} onClick={() => resetUserPassword(u.id)} disabled={saving}>Clave</button>
                <button style={u.active ? dangerBtn : btn} onClick={() => toggleUserActive(u.id, !!u.active)} disabled={saving}>{u.active ? "Bloquear" : "Activar"}</button>
              </div>
            </div>
          ))}
          {users.length === 0 ? <div style={{ opacity: 0.75 }}>No hay usuarios registrados.</div> : null}
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
            Codigos de respaldo
          </label>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <h4 style={{ margin: 0 }}>Sesiones activas</h4>
          <button style={dangerBtn} onClick={revokeAllSessions} disabled={saving}>Revocar todas</button>
        </div>

        <div className="custom-scrollbar" style={{ maxHeight: 280, overflowY: "auto", display: "grid", gap: 8, paddingRight: 4 }}>
          {sessions.map((s) => (
            <div key={s.id} style={{ ...card, display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 700 }}>{s.user}</div>
                <div style={{ fontSize: 12, opacity: 0.82 }}>{s.device} | IP: {s.ip}</div>
                <div style={{ fontSize: 11, opacity: 0.72 }}>Creada: {fmtDate(s.created_at)} | Ultima actividad: {fmtDate(s.last_seen)}</div>
              </div>
              <button style={dangerBtn} onClick={() => revokeSession(s.id)} disabled={saving}>Revocar</button>
            </div>
          ))}
          {sessions.length === 0 ? <div style={{ opacity: 0.75 }}>No hay sesiones activas.</div> : null}
        </div>
      </div>

      <div style={{ ...panel, padding: 14, display: "grid", gap: 10 }}>
        <h3 style={{ margin: 0 }}>Claves y secretos</h3>
        <div style={{ display: "grid", gridTemplateColumns: formCols, gap: 8 }}>
          <input
            style={input}
            placeholder="Nombre de API key"
            value={draftKey.name}
            onChange={(e) => setDraftKey((p) => ({ ...p, name: e.target.value }))}
          />
          <input
            style={input}
            placeholder="Scope (ej: mensajeria, catalogo)"
            value={draftKey.scope}
            onChange={(e) => setDraftKey((p) => ({ ...p, scope: e.target.value }))}
          />
          <input
            style={input}
            type="number"
            min={1}
            max={3650}
            placeholder="Dias de rotacion"
            value={draftKey.rotation_days}
            onChange={(e) => setDraftKey((p) => ({ ...p, rotation_days: Number(e.target.value || 90) }))}
          />
          <div style={{ display: "flex", alignItems: "center" }}>
            <button style={btn} onClick={createKey} disabled={saving}>
              {saving ? "Procesando..." : "Crear API key"}
            </button>
          </div>
        </div>
        <div className="custom-scrollbar" style={{ maxHeight: 260, overflowY: "auto", display: "grid", gap: 8, paddingRight: 4 }}>
          {keys.map((k) => (
            <div key={k.id} style={{ ...card, display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <div>
                <div style={{ fontWeight: 700 }}>{k.name}</div>
                <div style={{ fontSize: 12, opacity: 0.85 }}>Scope: {k.scope}</div>
                <div style={{ fontSize: 12, opacity: 0.85 }}>Rotacion: {Number(k.rotation_days || 0) > 0 ? `${k.rotation_days} dias` : "manual"}</div>
                <div style={{ fontFamily: "monospace", fontSize: 12, opacity: 0.88, marginTop: 4 }}>{maskKey(k.value)}</div>
                <div style={{ fontSize: 11, opacity: 0.72, marginTop: 3 }}>Ultima rotacion: {fmtDate(k.last_rotated_at || k.updated_at)}</div>
                <div style={{ fontSize: 11, opacity: 0.72, marginTop: 2 }}>Proxima rotacion: {fmtDate(k.next_rotation_at)}</div>
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <button style={btn} onClick={() => revealKey(k.id)} disabled={saving}>Ver</button>
                <button style={btn} onClick={() => rotateKey(k.id)} disabled={saving}>Rotar</button>
              </div>
            </div>
          ))}
          {keys.length === 0 ? <div style={{ opacity: 0.75 }}>No hay API keys registradas.</div> : null}
        </div>
      </div>

      <div style={{ ...panel, padding: 14, display: "grid", gap: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <h3 style={{ margin: 0 }}>Auditoria y alertas</h3>
          <select style={{ ...input, width: isMobile ? "100%" : 220 }} value={auditFilter} onChange={(e) => setAuditFilter(e.target.value)}>
            <option value="all">Eventos: todos</option>
            <option value="high">Eventos: alta severidad</option>
            <option value="medium">Eventos: media severidad</option>
            <option value="low">Eventos: baja severidad</option>
          </select>
        </div>

        <div className="custom-scrollbar" style={{ maxHeight: 220, overflowY: "auto", display: "grid", gap: 8, paddingRight: 4 }}>
          {auditEvents.map((e) => (
            <div key={e.id} style={{ ...card, display: "grid", gap: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <strong>{e.action}</strong>
                <span style={{ fontSize: 11, opacity: 0.78 }}>{e.level}</span>
              </div>
              <div style={{ fontSize: 12, opacity: 0.8 }}>actor: {e.actor} | ip: {e.ip}</div>
              <div style={{ fontSize: 11, opacity: 0.7 }}>{fmtDate(e.created_at)}</div>
            </div>
          ))}
          {auditEvents.length === 0 ? <div style={{ opacity: 0.75 }}>Sin eventos para ese filtro.</div> : null}
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
            Alertar cambios criticos
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
