package com.verane.mobile.feature.setup

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.verane.mobile.core.repository.VeraneRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SetupUiState(
    val apiBase: String = "",
    val securityToken: String = "",
    val webAppBase: String = "",
    val backgroundSyncEnabled: Boolean = true,
    val securityRole: String = "admin",
    val actorName: String = "",
    val saving: Boolean = false,
    val error: String = "",
    val success: String = "",
)

class SetupViewModel(
    private val repository: VeraneRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(SetupUiState())
    val uiState: StateFlow<SetupUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            val cfg = repository.configFlow.first()
            _uiState.update {
                it.copy(
                    apiBase = cfg.apiBase,
                    securityToken = cfg.securityToken,
                    webAppBase = cfg.webAppBase,
                    backgroundSyncEnabled = cfg.backgroundSyncEnabled,
                    securityRole = cfg.securityRole,
                    actorName = cfg.actorName,
                )
            }
        }
    }

    fun updateApiBase(value: String) = _uiState.update { it.copy(apiBase = value, error = "", success = "") }
    fun updateToken(value: String) = _uiState.update { it.copy(securityToken = value, error = "", success = "") }
    fun updateWebBase(value: String) = _uiState.update { it.copy(webAppBase = value, error = "", success = "") }
    fun updateSecurityRole(value: String) = _uiState.update { it.copy(securityRole = value, error = "", success = "") }
    fun updateActorName(value: String) = _uiState.update { it.copy(actorName = value, error = "", success = "") }
    fun updateBackgroundSync(value: Boolean) = _uiState.update {
        it.copy(backgroundSyncEnabled = value, error = "", success = "")
    }

    fun save(onSaved: () -> Unit) {
        val current = _uiState.value
        if (current.apiBase.isBlank()) {
            _uiState.update { it.copy(error = "Ingresa la URL del backend (API_BASE).") }
            return
        }
        if (current.webAppBase.isBlank()) {
            _uiState.update { it.copy(error = "Ingresa la URL de la app web.") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(saving = true, error = "", success = "") }
            runCatching {
                repository.saveConfig(
                    apiBase = current.apiBase,
                    securityToken = current.securityToken,
                    webAppBase = current.webAppBase,
                    backgroundSyncEnabled = current.backgroundSyncEnabled,
                    securityRole = current.securityRole,
                    actorName = current.actorName,
                )
            }.onSuccess {
                _uiState.update { it.copy(saving = false, success = "Configuracion guardada") }
                onSaved()
            }.onFailure { e ->
                _uiState.update { it.copy(saving = false, error = e.message ?: "No se pudo guardar") }
            }
        }
    }
}
