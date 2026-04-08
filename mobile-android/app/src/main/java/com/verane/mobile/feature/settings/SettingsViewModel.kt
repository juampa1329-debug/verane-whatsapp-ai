package com.verane.mobile.feature.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.verane.mobile.core.repository.VeraneRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException

data class SettingsUiState(
    val apiBase: String = "",
    val webAppBase: String = "",
    val securityToken: String = "",
    val backgroundSyncEnabled: Boolean = true,
    val securityRole: String = "admin",
    val actorName: String = "",
    val firebaseToken: String = "",
    val pushTestTitle: String = "Prueba push Verane",
    val pushTestBody: String = "Push de prueba enviado desde app",
    val loading: Boolean = true,
    val saving: Boolean = false,
    val error: String = "",
    val success: String = "",
)

class SettingsViewModel(
    private val repository: VeraneRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            repository.configFlow.collect { cfg ->
                _uiState.update {
                    it.copy(
                        apiBase = cfg.apiBase,
                        webAppBase = cfg.webAppBase,
                        securityToken = cfg.securityToken,
                        backgroundSyncEnabled = cfg.backgroundSyncEnabled,
                        securityRole = cfg.securityRole,
                        actorName = cfg.actorName,
                        firebaseToken = cfg.firebaseToken,
                        loading = false,
                    )
                }
            }
        }
    }

    fun updateApi(value: String) = _uiState.update { it.copy(apiBase = value, error = "", success = "") }
    fun updateWeb(value: String) = _uiState.update { it.copy(webAppBase = value, error = "", success = "") }
    fun updateToken(value: String) = _uiState.update { it.copy(securityToken = value, error = "", success = "") }
    fun updateSecurityRole(value: String) = _uiState.update { it.copy(securityRole = value, error = "", success = "") }
    fun updateActorName(value: String) = _uiState.update { it.copy(actorName = value, error = "", success = "") }
    fun updatePushTestTitle(value: String) = _uiState.update { it.copy(pushTestTitle = value, error = "", success = "") }
    fun updatePushTestBody(value: String) = _uiState.update { it.copy(pushTestBody = value, error = "", success = "") }
    fun updateBackgroundSync(value: Boolean) = _uiState.update {
        it.copy(backgroundSyncEnabled = value, error = "", success = "")
    }

    fun save(onSaved: () -> Unit = {}) {
        val state = _uiState.value
        if (state.apiBase.isBlank()) {
            _uiState.update { it.copy(error = "API Base URL es requerida") }
            return
        }
        if (state.webAppBase.isBlank()) {
            _uiState.update { it.copy(error = "Web App URL es requerida") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(saving = true, error = "", success = "") }
            runCatching {
                repository.saveConfig(
                    apiBase = state.apiBase,
                    securityToken = state.securityToken,
                    webAppBase = state.webAppBase,
                    backgroundSyncEnabled = state.backgroundSyncEnabled,
                    securityRole = state.securityRole,
                    actorName = state.actorName,
                )
            }.onSuccess {
                _uiState.update { it.copy(saving = false, success = "Ajustes guardados") }
                onSaved()
            }.onFailure { e ->
                _uiState.update { it.copy(saving = false, error = e.message ?: "No se pudo guardar") }
            }
        }
    }

    fun sendBackendPushTest() {
        val state = _uiState.value
        val title = state.pushTestTitle.trim().ifBlank { "Prueba push Verane" }
        val body = state.pushTestBody.trim().ifBlank { "Push de prueba" }
        viewModelScope.launch {
            _uiState.update { it.copy(saving = true, error = "", success = "") }
            runCatching {
                repository.testMobilePush(
                    title = title,
                    body = body,
                    eventType = "manual_test",
                    roleScope = "all",
                )
            }.onSuccess {
                _uiState.update { it.copy(saving = false, success = "Push test enviado al backend") }
            }.onFailure { e ->
                val message = when (e) {
                    is HttpException -> {
                        if (e.code() == 404) {
                            "Backend sin endpoints de push. Actualiza API a la fase movil/push."
                        } else {
                            "Push test fallo (${e.code()})"
                        }
                    }

                    else -> e.message ?: "No se pudo enviar push test"
                }
                _uiState.update { it.copy(saving = false, error = message) }
            }
        }
    }
}
