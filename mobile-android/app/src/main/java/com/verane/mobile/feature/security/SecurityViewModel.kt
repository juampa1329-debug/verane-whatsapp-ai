package com.verane.mobile.feature.security

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.verane.mobile.core.network.SecurityAlertsDto
import com.verane.mobile.core.network.SecurityApiKeyDto
import com.verane.mobile.core.network.SecurityAuditEventDto
import com.verane.mobile.core.network.SecurityMfaDto
import com.verane.mobile.core.network.SecurityPolicyDto
import com.verane.mobile.core.network.SecuritySessionDto
import com.verane.mobile.core.network.SecuritySummaryDto
import com.verane.mobile.core.network.SecurityUserDto
import com.verane.mobile.core.repository.VeraneRepository
import com.verane.mobile.core.security.canAccessSecurity
import com.verane.mobile.core.security.canManageSecurity
import com.verane.mobile.core.security.normalizeRole
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SecurityUiState(
    val loading: Boolean = true,
    val processing: Boolean = false,
    val role: String = "agente",
    val canAccess: Boolean = false,
    val isAdmin: Boolean = false,
    val authEnabled: Boolean = false,
    val authOpenMode: Boolean = true,
    val configuredRoles: List<String> = emptyList(),
    val rotationEnabled: Boolean = false,
    val rotationRunning: Boolean = false,
    val rotationIntervalSec: Int = 0,
    val auditLevel: String = "all",
    val policy: SecurityPolicyDto = SecurityPolicyDto(),
    val mfa: SecurityMfaDto = SecurityMfaDto(),
    val alerts: SecurityAlertsDto = SecurityAlertsDto(),
    val summary: SecuritySummaryDto = SecuritySummaryDto(),
    val users: List<SecurityUserDto> = emptyList(),
    val sessions: List<SecuritySessionDto> = emptyList(),
    val keys: List<SecurityApiKeyDto> = emptyList(),
    val auditEvents: List<SecurityAuditEventDto> = emptyList(),
    val policyPasswordMinLength: String = "10",
    val policyAccessTokenMinutes: String = "30",
    val policySessionIdleMinutes: String = "30",
    val policyForceRotationDays: String = "90",
    val policyRequireSpecialChars: Boolean = false,
    val mfaEnforceAdmins: Boolean = true,
    val mfaEnforceSupervisors: Boolean = true,
    val mfaAllowAgents: Boolean = true,
    val mfaBackupCodes: Boolean = true,
    val alertsFailedLogin: Boolean = true,
    val alertsSuspiciousIp: Boolean = true,
    val alertsSecurityChange: Boolean = true,
    val alertsWebhookFailure: Boolean = false,
    val alertsChannelEmail: Boolean = true,
    val alertsChannelWhatsapp: Boolean = true,
    val userName: String = "",
    val userEmail: String = "",
    val userRole: String = "agente",
    val userPassword: String = "",
    val userTwofa: Boolean = false,
    val userActive: Boolean = true,
    val twofaCode: String = "",
    val keyName: String = "",
    val keyScope: String = "general",
    val keyRotationDays: String = "90",
    val lastTempPassword: String = "",
    val lastPlainSecret: String = "",
    val lastTwofaSecret: String = "",
    val lastTwofaUri: String = "",
    val error: String = "",
    val success: String = "",
)

class SecurityViewModel(
    private val repository: VeraneRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(SecurityUiState())
    val uiState: StateFlow<SecurityUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            repository.configFlow.collect { cfg ->
                val role = normalizeRole(cfg.securityRole)
                _uiState.update {
                    it.copy(
                        role = role,
                        canAccess = canAccessSecurity(role),
                        isAdmin = canManageSecurity(role),
                    )
                }
                refresh()
            }
        }
    }

    fun setAuditLevel(value: String) {
        _uiState.update { it.copy(auditLevel = value) }
        refresh()
    }

    fun updatePolicyPasswordMinLength(value: String) = _uiState.update {
        it.copy(policyPasswordMinLength = value, error = "", success = "")
    }

    fun updatePolicyAccessTokenMinutes(value: String) = _uiState.update {
        it.copy(policyAccessTokenMinutes = value, error = "", success = "")
    }

    fun updatePolicySessionIdleMinutes(value: String) = _uiState.update {
        it.copy(policySessionIdleMinutes = value, error = "", success = "")
    }

    fun updatePolicyForceRotationDays(value: String) = _uiState.update {
        it.copy(policyForceRotationDays = value, error = "", success = "")
    }

    fun updatePolicyRequireSpecialChars(value: Boolean) = _uiState.update {
        it.copy(policyRequireSpecialChars = value, error = "", success = "")
    }

    fun updateMfaEnforceAdmins(value: Boolean) = _uiState.update { it.copy(mfaEnforceAdmins = value, error = "", success = "") }
    fun updateMfaEnforceSupervisors(value: Boolean) = _uiState.update { it.copy(mfaEnforceSupervisors = value, error = "", success = "") }
    fun updateMfaAllowAgents(value: Boolean) = _uiState.update { it.copy(mfaAllowAgents = value, error = "", success = "") }
    fun updateMfaBackupCodes(value: Boolean) = _uiState.update { it.copy(mfaBackupCodes = value, error = "", success = "") }

    fun updateAlertsFailedLogin(value: Boolean) = _uiState.update { it.copy(alertsFailedLogin = value, error = "", success = "") }
    fun updateAlertsSuspiciousIp(value: Boolean) = _uiState.update { it.copy(alertsSuspiciousIp = value, error = "", success = "") }
    fun updateAlertsSecurityChange(value: Boolean) = _uiState.update { it.copy(alertsSecurityChange = value, error = "", success = "") }
    fun updateAlertsWebhookFailure(value: Boolean) = _uiState.update { it.copy(alertsWebhookFailure = value, error = "", success = "") }
    fun updateAlertsChannelEmail(value: Boolean) = _uiState.update { it.copy(alertsChannelEmail = value, error = "", success = "") }
    fun updateAlertsChannelWhatsapp(value: Boolean) = _uiState.update { it.copy(alertsChannelWhatsapp = value, error = "", success = "") }

    fun updateUserName(value: String) = _uiState.update { it.copy(userName = value, error = "", success = "") }
    fun updateUserEmail(value: String) = _uiState.update { it.copy(userEmail = value, error = "", success = "") }
    fun updateUserRole(value: String) = _uiState.update { it.copy(userRole = value, error = "", success = "") }
    fun updateUserPassword(value: String) = _uiState.update { it.copy(userPassword = value, error = "", success = "") }
    fun updateUserTwofa(value: Boolean) = _uiState.update { it.copy(userTwofa = value, error = "", success = "") }
    fun updateUserActive(value: Boolean) = _uiState.update { it.copy(userActive = value, error = "", success = "") }
    fun updateTwofaCode(value: String) = _uiState.update { it.copy(twofaCode = value, error = "", success = "") }

    fun updateKeyName(value: String) = _uiState.update { it.copy(keyName = value, error = "", success = "") }
    fun updateKeyScope(value: String) = _uiState.update { it.copy(keyScope = value, error = "", success = "") }
    fun updateKeyRotationDays(value: String) = _uiState.update { it.copy(keyRotationDays = value, error = "", success = "") }

    fun clearOutputSecrets() {
        _uiState.update {
            it.copy(
                lastTempPassword = "",
                lastPlainSecret = "",
                lastTwofaSecret = "",
                lastTwofaUri = "",
                error = "",
                success = "",
            )
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = "", success = "") }
            runCatching {
                val role = _uiState.value.role
                val authMode = repository.securityAuthMode()

                if (!canAccessSecurity(role)) {
                    _uiState.update {
                        it.copy(
                            loading = false,
                            authEnabled = authMode.enabled,
                            authOpenMode = authMode.openMode,
                            configuredRoles = authMode.configuredRoles,
                            error = "El rol '$role' no tiene acceso al modulo de seguridad.",
                        )
                    }
                    return@runCatching
                }

                val state = repository.securityState(
                    auditLevel = _uiState.value.auditLevel,
                    auditLimit = 120,
                )
                val rotation = repository.securityRotationStatus()

                _uiState.update { current ->
                    current.copy(
                        loading = false,
                        authEnabled = authMode.enabled,
                        authOpenMode = authMode.openMode,
                        configuredRoles = authMode.configuredRoles,
                        rotationEnabled = rotation.enabled,
                        rotationRunning = rotation.running,
                        rotationIntervalSec = rotation.intervalSec,
                        policy = state.policy,
                        mfa = state.mfa,
                        alerts = state.alerts,
                        summary = state.summary,
                        users = state.users,
                        sessions = state.sessions,
                        keys = state.keys,
                        auditEvents = state.auditEvents,
                        policyPasswordMinLength = state.policy.passwordMinLength.toString(),
                        policyAccessTokenMinutes = state.policy.accessTokenMinutes.toString(),
                        policySessionIdleMinutes = state.policy.sessionIdleMinutes.toString(),
                        policyForceRotationDays = state.policy.forcePasswordRotationDays.toString(),
                        policyRequireSpecialChars = state.policy.requireSpecialChars,
                        mfaEnforceAdmins = state.mfa.enforceForAdmins,
                        mfaEnforceSupervisors = state.mfa.enforceForSupervisors,
                        mfaAllowAgents = state.mfa.allowForAgents,
                        mfaBackupCodes = state.mfa.backupCodesEnabled,
                        alertsFailedLogin = state.alerts.failedLoginAlert,
                        alertsSuspiciousIp = state.alerts.suspiciousIpAlert,
                        alertsSecurityChange = state.alerts.securityChangeAlert,
                        alertsWebhookFailure = state.alerts.webhookFailureAlert,
                        alertsChannelEmail = state.alerts.channelEmail,
                        alertsChannelWhatsapp = state.alerts.channelWhatsapp,
                    )
                }
            }.onFailure { e ->
                _uiState.update { it.copy(loading = false, error = e.message ?: "No se pudo cargar seguridad") }
            }
        }
    }

    fun savePolicy() {
        val state = _uiState.value
        if (!state.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede actualizar politicas") }
            return
        }
        val minLen = state.policyPasswordMinLength.trim().toIntOrNull()
        val accessMin = state.policyAccessTokenMinutes.trim().toIntOrNull()
        val idleMin = state.policySessionIdleMinutes.trim().toIntOrNull()
        val rotationDays = state.policyForceRotationDays.trim().toIntOrNull()
        if (minLen == null || accessMin == null || idleMin == null || rotationDays == null) {
            _uiState.update { it.copy(error = "Valores numericos invalidos en politicas") }
            return
        }

        runMutation("No se pudo actualizar politicas", "Politicas actualizadas") {
            repository.updateSecurityPolicy(
                passwordMinLength = minLen,
                requireSpecialChars = state.policyRequireSpecialChars,
                accessTokenMinutes = accessMin,
                sessionIdleMinutes = idleMin,
                forcePasswordRotationDays = rotationDays,
            )
        }
    }

    fun saveMfaPolicy() {
        val state = _uiState.value
        if (!state.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede actualizar MFA") }
            return
        }
        runMutation("No se pudo actualizar MFA", "Politica MFA actualizada") {
            repository.updateSecurityMfa(
                enforceForAdmins = state.mfaEnforceAdmins,
                enforceForSupervisors = state.mfaEnforceSupervisors,
                allowForAgents = state.mfaAllowAgents,
                backupCodesEnabled = state.mfaBackupCodes,
            )
        }
    }

    fun saveAlertsPolicy() {
        val state = _uiState.value
        if (!state.canAccess) {
            _uiState.update { it.copy(error = "No tienes permisos para alertas") }
            return
        }
        runMutation("No se pudo actualizar alertas", "Alertas actualizadas") {
            repository.updateSecurityAlerts(
                failedLoginAlert = state.alertsFailedLogin,
                suspiciousIpAlert = state.alertsSuspiciousIp,
                securityChangeAlert = state.alertsSecurityChange,
                webhookFailureAlert = state.alertsWebhookFailure,
                channelEmail = state.alertsChannelEmail,
                channelWhatsapp = state.alertsChannelWhatsapp,
            )
        }
    }

    fun runRotationTick() {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede ejecutar rotacion manual") }
            return
        }
        runMutation("No se pudo ejecutar rotacion", "Rotacion ejecutada") {
            repository.securityRotationTick(limit = 80)
        }
    }

    fun createUser() {
        val state = _uiState.value
        if (!state.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede crear usuarios") }
            return
        }
        val name = state.userName.trim()
        val email = state.userEmail.trim()
        if (name.isBlank() || email.isBlank()) {
            _uiState.update { it.copy(error = "Nombre y email son requeridos") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.createSecurityUser(
                    name = name,
                    email = email,
                    role = state.userRole,
                    twofa = state.userTwofa,
                    active = state.userActive,
                    password = state.userPassword.trim().ifBlank { null },
                )
            }.onSuccess { response ->
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "Usuario creado",
                        userName = "",
                        userEmail = "",
                        userPassword = "",
                        lastTempPassword = response.tempPassword ?: "",
                        lastTwofaSecret = response.twofaSetupSecret ?: "",
                        lastTwofaUri = response.twofaSetupUri ?: "",
                    )
                }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo crear usuario") }
            }
        }
    }

    fun toggleUserActive(user: SecurityUserDto) {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede editar usuarios") }
            return
        }
        runMutation("No se pudo actualizar usuario", "Usuario actualizado") {
            repository.patchSecurityUser(userId = user.id, active = !user.active)
        }
    }

    fun promoteUser(user: SecurityUserDto, role: String) {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede cambiar roles") }
            return
        }
        runMutation("No se pudo cambiar rol", "Rol actualizado") {
            repository.patchSecurityUser(userId = user.id, role = role)
        }
    }

    fun resetUserPassword(userId: Int) {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede resetear contrasenas") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.resetSecurityUserPassword(userId = userId)
            }.onSuccess { response ->
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "Password reseteado",
                        lastTempPassword = response.tempPassword,
                    )
                }
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo resetear password") }
            }
        }
    }

    fun setupUser2fa(userId: Int) {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede configurar 2FA") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.setupSecurityUser2fa(userId = userId)
            }.onSuccess { response ->
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "Setup 2FA generado",
                        lastTwofaSecret = response.secret,
                        lastTwofaUri = response.otpauthUri,
                    )
                }
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo iniciar setup 2FA") }
            }
        }
    }

    fun verifyUser2fa(userId: Int) {
        val code = _uiState.value.twofaCode.trim()
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede verificar 2FA") }
            return
        }
        if (code.isBlank()) {
            _uiState.update { it.copy(error = "Ingresa codigo 2FA") }
            return
        }
        runMutation("No se pudo verificar 2FA", "2FA verificado") {
            repository.verifySecurityUser2fa(userId = userId, code = code)
            _uiState.update { it.copy(twofaCode = "") }
        }
    }

    fun disableUser2fa(userId: Int) {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede desactivar 2FA") }
            return
        }
        runMutation("No se pudo desactivar 2FA", "2FA desactivado") {
            repository.disableSecurityUser2fa(userId = userId)
        }
    }

    fun revokeSession(sessionId: String) {
        if (!_uiState.value.canAccess) {
            _uiState.update { it.copy(error = "No tienes permisos para revocar sesiones") }
            return
        }
        runMutation("No se pudo revocar sesion", "Sesion revocada") {
            repository.revokeSecuritySession(sessionId = sessionId)
        }
    }

    fun revokeAllSessions() {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede revocar todas las sesiones") }
            return
        }
        runMutation("No se pudo revocar sesiones", "Todas las sesiones fueron revocadas") {
            repository.revokeAllSecuritySessions()
        }
    }

    fun createKey() {
        val state = _uiState.value
        if (!state.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede crear API keys") }
            return
        }
        val name = state.keyName.trim()
        val days = state.keyRotationDays.trim().toIntOrNull()
        if (name.isBlank() || days == null) {
            _uiState.update { it.copy(error = "Nombre y rotation days validos son requeridos") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.createSecurityKey(
                    name = name,
                    scope = state.keyScope.trim().ifBlank { "general" },
                    rotationDays = days,
                )
            }.onSuccess { response ->
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "API key creada",
                        keyName = "",
                        keyScope = "general",
                        keyRotationDays = "90",
                        lastPlainSecret = response.plainSecret ?: "",
                    )
                }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo crear API key") }
            }
        }
    }

    fun rotateKey(keyId: Int) {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede rotar keys") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.rotateSecurityKey(keyId = keyId)
            }.onSuccess { response ->
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "API key rotada",
                        lastPlainSecret = response.plainSecret ?: "",
                    )
                }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo rotar API key") }
            }
        }
    }

    fun revealKey(keyId: Int) {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede revelar keys") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.revealSecurityKey(keyId = keyId)
            }.onSuccess { response ->
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "API key revelada",
                        lastPlainSecret = response.plainSecret,
                    )
                }
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo revelar API key") }
            }
        }
    }

    fun toggleKeyActive(key: SecurityApiKeyDto) {
        if (!_uiState.value.isAdmin) {
            _uiState.update { it.copy(error = "Solo admin puede activar/desactivar keys") }
            return
        }
        runMutation("No se pudo actualizar API key", "API key actualizada") {
            repository.patchSecurityKey(
                keyId = key.id,
                isActive = !key.isActive,
            )
        }
    }

    private fun runMutation(
        errorMessage: String,
        successMessage: String,
        action: suspend () -> Unit,
    ) {
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                action()
            }.onSuccess {
                _uiState.update { it.copy(processing = false, success = successMessage) }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: errorMessage) }
            }
        }
    }
}
