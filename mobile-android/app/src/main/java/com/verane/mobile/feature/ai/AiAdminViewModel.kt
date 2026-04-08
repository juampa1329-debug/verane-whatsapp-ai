package com.verane.mobile.feature.ai

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.verane.mobile.core.network.AiModelsCatalogResponse
import com.verane.mobile.core.network.AiSettingsDto
import com.verane.mobile.core.network.AiSettingsUpdateRequest
import com.verane.mobile.core.network.KnowledgeFileDto
import com.verane.mobile.core.network.KnowledgeWebSourceDto
import com.verane.mobile.core.repository.VeraneRepository
import com.verane.mobile.core.security.canAccessAi
import com.verane.mobile.core.security.normalizeRole
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

data class AiAdminUiState(
    val loading: Boolean = true,
    val processing: Boolean = false,
    val role: String = "agente",
    val canAccess: Boolean = false,
    val settings: AiSettingsDto = AiSettingsDto(),
    val providers: List<String> = emptyList(),
    val providerModels: Map<String, List<String>> = emptyMap(),
    val ttsProviders: List<String> = emptyList(),
    val files: List<KnowledgeFileDto> = emptyList(),
    val webSources: List<KnowledgeWebSourceDto> = emptyList(),
    val isEnabled: Boolean = true,
    val provider: String = "google",
    val model: String = "",
    val fallbackProvider: String = "",
    val fallbackModel: String = "",
    val maxTokens: String = "512",
    val temperature: String = "0.7",
    val timeoutSec: String = "25",
    val maxRetries: String = "1",
    val systemPrompt: String = "",
    val voiceEnabled: Boolean = false,
    val voiceLanguage: String = "es-CO",
    val voiceAccent: String = "colombiano",
    val voiceTtsProvider: String = "google",
    val voiceTtsVoiceId: String = "",
    val voiceTtsModelId: String = "",
    val voiceSpeakingRate: String = "1.0",
    val mmEnabled: Boolean = true,
    val mmProvider: String = "google",
    val mmModel: String = "gemini-2.5-flash",
    val testPhone: String = "",
    val testText: String = "",
    val testTtsText: String = "",
    val testReply: String = "",
    val testTtsResult: String = "",
    val uploadNotes: String = "",
    val webUrl: String = "",
    val webSourceName: String = "",
    val webNotes: String = "",
    val webSyncInterval: String = "360",
    val webTimeoutSec: String = "20",
    val webActive: Boolean = true,
    val webAutoSync: Boolean = true,
    val error: String = "",
    val success: String = "",
)

class AiAdminViewModel(
    private val repository: VeraneRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(AiAdminUiState())
    val uiState: StateFlow<AiAdminUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            repository.configFlow.collect { cfg ->
                val role = normalizeRole(cfg.securityRole)
                _uiState.update {
                    it.copy(
                        role = role,
                        canAccess = canAccessAi(role),
                    )
                }
                refresh()
            }
        }
    }

    fun updateIsEnabled(value: Boolean) = _uiState.update { it.copy(isEnabled = value, error = "", success = "") }
    fun updateProvider(value: String) = _uiState.update { it.copy(provider = value, error = "", success = "") }
    fun updateModel(value: String) = _uiState.update { it.copy(model = value, error = "", success = "") }
    fun updateFallbackProvider(value: String) = _uiState.update { it.copy(fallbackProvider = value, error = "", success = "") }
    fun updateFallbackModel(value: String) = _uiState.update { it.copy(fallbackModel = value, error = "", success = "") }
    fun updateMaxTokens(value: String) = _uiState.update { it.copy(maxTokens = value, error = "", success = "") }
    fun updateTemperature(value: String) = _uiState.update { it.copy(temperature = value, error = "", success = "") }
    fun updateTimeoutSec(value: String) = _uiState.update { it.copy(timeoutSec = value, error = "", success = "") }
    fun updateMaxRetries(value: String) = _uiState.update { it.copy(maxRetries = value, error = "", success = "") }
    fun updateSystemPrompt(value: String) = _uiState.update { it.copy(systemPrompt = value, error = "", success = "") }
    fun updateVoiceEnabled(value: Boolean) = _uiState.update { it.copy(voiceEnabled = value, error = "", success = "") }
    fun updateVoiceLanguage(value: String) = _uiState.update { it.copy(voiceLanguage = value, error = "", success = "") }
    fun updateVoiceAccent(value: String) = _uiState.update { it.copy(voiceAccent = value, error = "", success = "") }
    fun updateVoiceTtsProvider(value: String) = _uiState.update { it.copy(voiceTtsProvider = value, error = "", success = "") }
    fun updateVoiceTtsVoiceId(value: String) = _uiState.update { it.copy(voiceTtsVoiceId = value, error = "", success = "") }
    fun updateVoiceTtsModelId(value: String) = _uiState.update { it.copy(voiceTtsModelId = value, error = "", success = "") }
    fun updateVoiceSpeakingRate(value: String) = _uiState.update { it.copy(voiceSpeakingRate = value, error = "", success = "") }
    fun updateMmEnabled(value: Boolean) = _uiState.update { it.copy(mmEnabled = value, error = "", success = "") }
    fun updateMmProvider(value: String) = _uiState.update { it.copy(mmProvider = value, error = "", success = "") }
    fun updateMmModel(value: String) = _uiState.update { it.copy(mmModel = value, error = "", success = "") }

    fun updateTestPhone(value: String) = _uiState.update { it.copy(testPhone = value, error = "", success = "") }
    fun updateTestText(value: String) = _uiState.update { it.copy(testText = value, error = "", success = "") }
    fun updateTestTtsText(value: String) = _uiState.update { it.copy(testTtsText = value, error = "", success = "") }
    fun updateUploadNotes(value: String) = _uiState.update { it.copy(uploadNotes = value, error = "", success = "") }

    fun updateWebUrl(value: String) = _uiState.update { it.copy(webUrl = value, error = "", success = "") }
    fun updateWebSourceName(value: String) = _uiState.update { it.copy(webSourceName = value, error = "", success = "") }
    fun updateWebNotes(value: String) = _uiState.update { it.copy(webNotes = value, error = "", success = "") }
    fun updateWebSyncInterval(value: String) = _uiState.update { it.copy(webSyncInterval = value, error = "", success = "") }
    fun updateWebTimeoutSec(value: String) = _uiState.update { it.copy(webTimeoutSec = value, error = "", success = "") }
    fun updateWebActive(value: Boolean) = _uiState.update { it.copy(webActive = value, error = "", success = "") }
    fun updateWebAutoSync(value: Boolean) = _uiState.update { it.copy(webAutoSync = value, error = "", success = "") }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = "", success = "") }
            runCatching {
                if (!_uiState.value.canAccess) {
                    _uiState.update {
                        it.copy(
                            loading = false,
                            error = "El rol '${it.role}' no tiene acceso al modulo AI.",
                        )
                    }
                    return@runCatching
                }

                val settings = repository.getAiSettings()
                val models = repository.getAiModelsCatalog()
                val files = repository.listKnowledgeFiles(active = "all", limit = 200)
                val webSources = repository.listKnowledgeWebSources(active = "all", limit = 200)

                val providers = parseProviders(models)
                val providerModels = parseProviderModels(models)
                val ttsProviders = parseTtsProviders(models)

                _uiState.update {
                    it.copy(
                        loading = false,
                        settings = settings,
                        providers = providers,
                        providerModels = providerModels,
                        ttsProviders = ttsProviders,
                        files = files,
                        webSources = webSources,
                        isEnabled = settings.isEnabled,
                        provider = settings.provider,
                        model = settings.model,
                        fallbackProvider = settings.fallbackProvider,
                        fallbackModel = settings.fallbackModel,
                        maxTokens = settings.maxTokens.toString(),
                        temperature = settings.temperature.toString(),
                        timeoutSec = settings.timeoutSec.toString(),
                        maxRetries = settings.maxRetries.toString(),
                        systemPrompt = settings.systemPrompt,
                        voiceEnabled = settings.voiceEnabled,
                        voiceLanguage = settings.voiceLanguage,
                        voiceAccent = settings.voiceAccent,
                        voiceTtsProvider = settings.voiceTtsProvider,
                        voiceTtsVoiceId = settings.voiceTtsVoiceId,
                        voiceTtsModelId = settings.voiceTtsModelId,
                        voiceSpeakingRate = settings.voiceSpeakingRate.toString(),
                        mmEnabled = settings.mmEnabled,
                        mmProvider = settings.mmProvider,
                        mmModel = settings.mmModel,
                    )
                }
            }.onFailure { e ->
                _uiState.update { it.copy(loading = false, error = e.message ?: "No se pudo cargar AI") }
            }
        }
    }

    fun saveAiSettings() {
        val state = _uiState.value
        if (!state.canAccess) {
            _uiState.update { it.copy(error = "No tienes permisos para AI") }
            return
        }

        val maxTokens = state.maxTokens.trim().toIntOrNull()
        val temperature = state.temperature.trim().toDoubleOrNull()
        val timeoutSec = state.timeoutSec.trim().toIntOrNull()
        val maxRetries = state.maxRetries.trim().toIntOrNull()
        val voiceRate = state.voiceSpeakingRate.trim().toDoubleOrNull()

        if (maxTokens == null || temperature == null || timeoutSec == null || maxRetries == null || voiceRate == null) {
            _uiState.update { it.copy(error = "Valores numericos invalidos en AI settings") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.updateAiSettings(
                    payload = AiSettingsUpdateRequest(
                        isEnabled = state.isEnabled,
                        provider = state.provider.trim().ifBlank { "google" },
                        model = state.model.trim(),
                        fallbackProvider = state.fallbackProvider.trim().ifBlank { null },
                        fallbackModel = state.fallbackModel.trim().ifBlank { null },
                        maxTokens = maxTokens,
                        temperature = temperature,
                        timeoutSec = timeoutSec,
                        maxRetries = maxRetries,
                        systemPrompt = state.systemPrompt,
                        voiceEnabled = state.voiceEnabled,
                        voiceLanguage = state.voiceLanguage.trim(),
                        voiceAccent = state.voiceAccent.trim(),
                        voiceTtsProvider = state.voiceTtsProvider.trim().ifBlank { "google" },
                        voiceTtsVoiceId = state.voiceTtsVoiceId.trim(),
                        voiceTtsModelId = state.voiceTtsModelId.trim(),
                        voiceSpeakingRate = voiceRate,
                        mmEnabled = state.mmEnabled,
                        mmProvider = state.mmProvider.trim().ifBlank { "google" },
                        mmModel = state.mmModel.trim().ifBlank { "gemini-2.5-flash" },
                    )
                )
            }.onSuccess {
                _uiState.update { it.copy(processing = false, success = "AI settings guardados") }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo guardar AI settings") }
            }
        }
    }

    fun testProcessMessage() {
        val state = _uiState.value
        val phone = state.testPhone.trim()
        if (!state.canAccess) {
            _uiState.update { it.copy(error = "No tienes permisos para AI") }
            return
        }
        if (phone.isBlank()) {
            _uiState.update { it.copy(error = "Ingresa telefono para test AI") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.processAiMessage(phone = phone, text = state.testText)
            }.onSuccess { res ->
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = if (res.ok) "Test AI ejecutado" else "Test AI con error",
                        testReply = buildString {
                            append("provider=${res.provider} model=${res.model} fallback=${res.usedFallback}\n")
                            if (res.error != null) append("error=${res.error}\n")
                            append(res.replyText)
                        },
                    )
                }
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo probar AI") }
            }
        }
    }

    fun testTts() {
        val state = _uiState.value
        val text = state.testTtsText.trim()
        if (!state.canAccess) {
            _uiState.update { it.copy(error = "No tienes permisos para TTS") }
            return
        }
        if (text.isBlank()) {
            _uiState.update { it.copy(error = "Texto TTS requerido") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.testAiTts(
                    text = text,
                    provider = state.voiceTtsProvider,
                    voiceId = state.voiceTtsVoiceId.trim().ifBlank { null },
                    modelId = state.voiceTtsModelId.trim().ifBlank { null },
                )
            }.onSuccess { result ->
                val (mime, bytes) = result
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "TTS ejecutado",
                        testTtsResult = "mime=${mime.ifBlank { "-" }} bytes=${bytes.size}",
                    )
                }
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo probar TTS") }
            }
        }
    }

    fun uploadKnowledgeFile(
        bytes: ByteArray,
        fileName: String,
        mimeType: String,
    ) {
        if (!_uiState.value.canAccess) {
            _uiState.update { it.copy(error = "No tienes permisos para KB") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.uploadKnowledgeFile(
                    bytes = bytes,
                    fileName = fileName,
                    mimeType = mimeType,
                    notes = _uiState.value.uploadNotes,
                )
            }.onSuccess {
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "Archivo KB cargado",
                        uploadNotes = "",
                    )
                }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo subir archivo KB") }
            }
        }
    }

    fun reindexFile(fileId: String) {
        runSimpleAction("No se pudo reindexar archivo", "Archivo reindexado") {
            repository.reindexKnowledgeFile(fileId = fileId)
        }
    }

    fun deleteFile(fileId: String) {
        runSimpleAction("No se pudo eliminar archivo", "Archivo eliminado") {
            repository.deleteKnowledgeFile(fileId = fileId)
        }
    }

    fun createWebSource() {
        val state = _uiState.value
        val url = state.webUrl.trim()
        val interval = state.webSyncInterval.trim().toIntOrNull()
        val timeout = state.webTimeoutSec.trim().toIntOrNull()
        if (url.isBlank() || interval == null || timeout == null) {
            _uiState.update { it.copy(error = "URL, intervalo y timeout validos son requeridos") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.createKnowledgeWebSource(
                    url = url,
                    sourceName = state.webSourceName,
                    notes = state.webNotes,
                    isActive = state.webActive,
                    autoSync = state.webAutoSync,
                    syncIntervalMin = interval,
                    timeoutSec = timeout,
                )
            }.onSuccess {
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "Web source creada",
                        webUrl = "",
                        webSourceName = "",
                        webNotes = "",
                    )
                }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo crear web source") }
            }
        }
    }

    fun toggleWebSourceActive(source: KnowledgeWebSourceDto) {
        runSimpleAction("No se pudo actualizar web source", "Web source actualizada") {
            repository.updateKnowledgeWebSource(
                sourceId = source.id,
                isActive = !source.isActive,
            )
        }
    }

    fun syncWebSource(sourceId: String) {
        runSimpleAction("No se pudo sincronizar web source", "Web source sincronizada") {
            repository.syncKnowledgeWebSource(sourceId = sourceId)
        }
    }

    fun syncDueWebSources() {
        runSimpleAction("No se pudo sincronizar fuentes vencidas", "Sync due ejecutado") {
            repository.syncDueKnowledgeWebSources(limit = 10)
        }
    }

    fun deleteWebSource(sourceId: String) {
        runSimpleAction("No se pudo eliminar web source", "Web source eliminada") {
            repository.deleteKnowledgeWebSource(sourceId = sourceId)
        }
    }

    private fun runSimpleAction(
        errorMessage: String,
        successMessage: String,
        action: suspend () -> Unit,
    ) {
        if (!_uiState.value.canAccess) {
            _uiState.update { it.copy(error = "No tienes permisos para este modulo") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching { action() }
                .onSuccess {
                    _uiState.update { it.copy(processing = false, success = successMessage) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(processing = false, error = e.message ?: errorMessage) }
                }
        }
    }

    private fun parseProviders(models: AiModelsCatalogResponse): List<String> {
        return models.providers.keys.sorted()
    }

    private fun parseProviderModels(models: AiModelsCatalogResponse): Map<String, List<String>> {
        val out = mutableMapOf<String, List<String>>()
        models.providers.forEach { (provider, payload) ->
            val arr = (payload as? JsonArray) ?: JsonArray(emptyList())
            out[provider] = arr.mapNotNull { el ->
                runCatching { el.jsonPrimitive.content }.getOrNull()
            }.filter { it.isNotBlank() }
        }
        return out
    }

    private fun parseTtsProviders(models: AiModelsCatalogResponse): List<String> {
        val ttsRoot = models.tts
        val providers = (ttsRoot["providers"] as? JsonArray) ?: return emptyList()
        return providers.mapNotNull { runCatching { it.jsonPrimitive.content }.getOrNull() }
    }
}
