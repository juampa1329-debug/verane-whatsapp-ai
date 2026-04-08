package com.verane.mobile.feature.inbox

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.verane.mobile.core.network.ConversationDto
import com.verane.mobile.core.network.CustomerDto
import com.verane.mobile.core.network.MessageDto
import com.verane.mobile.core.network.WcProductDto
import com.verane.mobile.core.notifications.NotificationHelper
import com.verane.mobile.core.repository.VeraneRepository
import com.verane.mobile.core.util.DateTimeUtils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class InboxUiState(
    val apiBase: String = "",
    val search: String = "",
    val channel: String = "all",
    val loadingConversations: Boolean = false,
    val loadingMessages: Boolean = false,
    val sending: Boolean = false,
    val error: String = "",
    val conversations: List<ConversationDto> = emptyList(),
    val selectedPhone: String? = null,
    val messages: List<MessageDto> = emptyList(),
    val draft: String = "",
    val productCatalogOpen: Boolean = false,
    val productSearch: String = "",
    val productsLoading: Boolean = false,
    val productsError: String = "",
    val products: List<WcProductDto> = emptyList(),
    val sendingProductId: Long? = null,
    val contactInfoOpen: Boolean = false,
    val contactInfoLoading: Boolean = false,
    val contactInfoError: String = "",
    val contactInfoCustomer: CustomerDto? = null,
)

class InboxViewModel(
    private val repository: VeraneRepository,
    private val appContext: Context,
) : ViewModel() {
    private val _uiState = MutableStateFlow(InboxUiState())
    val uiState: StateFlow<InboxUiState> = _uiState.asStateFlow()

    private var didFirstConversationsLoad = false
    private val previousConversationTs = mutableMapOf<String, Long>()
    private var searchJob: Job? = null
    private var productSearchJob: Job? = null

    init {
        viewModelScope.launch {
            repository.configFlow.collect { cfg ->
                _uiState.update { it.copy(apiBase = cfg.apiBase) }
            }
        }

        viewModelScope.launch {
            refreshConversations(notifyNew = false)
            while (isActive) {
                delay(5000)
                refreshConversations(notifyNew = true)
                val selected = _uiState.value.selectedPhone
                if (!selected.isNullOrBlank()) {
                    loadMessages(selected)
                }
            }
        }
    }

    fun updateSearch(search: String) {
        _uiState.update { it.copy(search = search) }
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            delay(350)
            refreshConversations(notifyNew = false)
        }
    }

    fun setChannel(value: String) {
        _uiState.update { it.copy(channel = value) }
        viewModelScope.launch {
            refreshConversations(notifyNew = false)
            _uiState.value.selectedPhone?.let { loadMessages(it) }
        }
    }

    fun updateDraft(value: String) {
        _uiState.update { it.copy(draft = value) }
    }

    fun refreshNow() {
        viewModelScope.launch {
            refreshConversations(notifyNew = false)
            _uiState.value.selectedPhone?.let { loadMessages(it) }
        }
    }

    fun selectConversation(phone: String) {
        _uiState.update { it.copy(selectedPhone = phone, messages = emptyList(), error = "") }
        viewModelScope.launch {
            markRead(phone)
            loadMessages(phone)
            refreshConversations(notifyNew = false)
        }
    }

    fun clearSelection() {
        _uiState.update {
            it.copy(
                selectedPhone = null,
                messages = emptyList(),
                error = "",
                contactInfoOpen = false,
                contactInfoLoading = false,
                contactInfoError = "",
                contactInfoCustomer = null,
            )
        }
    }

    fun toggleTakeover() {
        val state = _uiState.value
        val phone = state.selectedPhone ?: return
        val current = state.conversations.firstOrNull { it.phone == phone }?.takeover ?: false
        viewModelScope.launch {
            runCatching {
                repository.setTakeover(phone, !current)
            }.onFailure { e ->
                _uiState.update { it.copy(error = e.message ?: "No se pudo actualizar takeover") }
            }
            refreshConversations(notifyNew = false)
        }
    }

    fun sendTextMessage() {
        val state = _uiState.value
        val phone = state.selectedPhone ?: return
        val text = state.draft.trim()
        if (text.isBlank()) return

        viewModelScope.launch {
            _uiState.update { it.copy(sending = true, error = "") }
            runCatching {
                repository.sendTextMessage(
                    phone = phone,
                    channel = resolveOutboundChannel(state),
                    text = text,
                )
            }.onSuccess {
                _uiState.update { it.copy(draft = "", sending = false) }
                loadMessages(phone)
                refreshConversations(notifyNew = false)
            }.onFailure { e ->
                _uiState.update { it.copy(sending = false, error = e.message ?: "No se pudo enviar mensaje") }
            }
        }
    }

    fun sendMediaFromUri(uri: Uri) {
        val state = _uiState.value
        val phone = state.selectedPhone ?: return
        viewModelScope.launch {
            _uiState.update { it.copy(sending = true, error = "") }
            runCatching {
                val metadata = readBytesFromUri(uri)
                repository.sendMediaMessage(
                    phone = phone,
                    channel = resolveOutboundChannel(state),
                    bytes = metadata.bytes,
                    fileName = metadata.fileName,
                    mimeType = metadata.mimeType,
                    kind = metadata.kind,
                    caption = state.draft.trim(),
                )
            }.onSuccess {
                _uiState.update { it.copy(draft = "", sending = false) }
                loadMessages(phone)
                refreshConversations(notifyNew = false)
            }.onFailure { e ->
                _uiState.update { it.copy(sending = false, error = e.message ?: "No se pudo enviar adjunto") }
            }
        }
    }

    fun sendRecordedAudio(
        bytes: ByteArray,
        fileName: String,
        mimeType: String = "audio/mp4",
        durationSec: Int = 0,
    ) {
        val state = _uiState.value
        val phone = state.selectedPhone ?: return
        if (bytes.isEmpty()) {
            _uiState.update { it.copy(error = "Audio vacio, intenta de nuevo") }
            return
        }
        if (bytes.size > 15 * 1024 * 1024) {
            _uiState.update { it.copy(error = "El audio supera 15MB") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(sending = true, error = "") }
            runCatching {
                repository.sendMediaMessage(
                    phone = phone,
                    channel = resolveOutboundChannel(state),
                    bytes = bytes,
                    fileName = fileName.ifBlank { "audio_${System.currentTimeMillis()}.m4a" },
                    mimeType = mimeType.ifBlank { "audio/mp4" },
                    kind = "audio",
                    caption = state.draft.trim(),
                    durationSec = durationSec.takeIf { it > 0 },
                )
            }.onSuccess {
                _uiState.update { it.copy(draft = "", sending = false) }
                loadMessages(phone)
                refreshConversations(notifyNew = false)
            }.onFailure { e ->
                _uiState.update { it.copy(sending = false, error = e.message ?: "No se pudo enviar audio") }
            }
        }
    }

    fun openProductCatalog() {
        _uiState.update { it.copy(productCatalogOpen = true, productsError = "") }
        if (_uiState.value.products.isEmpty()) {
            viewModelScope.launch { loadProducts(_uiState.value.productSearch) }
        }
    }

    fun closeProductCatalog() {
        _uiState.update { it.copy(productCatalogOpen = false) }
    }

    fun updateProductSearch(value: String) {
        _uiState.update { it.copy(productSearch = value, productsError = "") }
        productSearchJob?.cancel()
        productSearchJob = viewModelScope.launch {
            delay(300)
            loadProducts(value)
        }
    }

    fun sendCatalogProduct(productId: Long) {
        val state = _uiState.value
        val phone = state.selectedPhone ?: return
        viewModelScope.launch {
            _uiState.update { it.copy(sending = true, sendingProductId = productId, error = "") }
            runCatching {
                repository.sendWcProduct(
                    phone = phone,
                    productId = productId,
                    caption = state.draft.trim(),
                )
            }.onSuccess {
                _uiState.update {
                    it.copy(
                        sending = false,
                        sendingProductId = null,
                        productCatalogOpen = false,
                        draft = "",
                    )
                }
                loadMessages(phone)
                refreshConversations(notifyNew = false)
            }.onFailure { e ->
                _uiState.update {
                    it.copy(
                        sending = false,
                        sendingProductId = null,
                        error = e.message ?: "No se pudo enviar producto",
                    )
                }
            }
        }
    }

    fun openContactInfo() {
        val phone = _uiState.value.selectedPhone ?: return
        _uiState.update {
            it.copy(
                contactInfoOpen = true,
                contactInfoLoading = true,
                contactInfoError = "",
                contactInfoCustomer = null,
            )
        }
        viewModelScope.launch {
            runCatching { repository.getCustomer(phone) }
                .onSuccess { customer ->
                    _uiState.update {
                        it.copy(
                            contactInfoLoading = false,
                            contactInfoCustomer = customer,
                            contactInfoError = if (customer == null) "No se encontro el perfil del cliente" else "",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(
                            contactInfoLoading = false,
                            contactInfoError = e.message ?: "No se pudo cargar el perfil del cliente",
                        )
                    }
                }
        }
    }

    fun closeContactInfo() {
        _uiState.update { it.copy(contactInfoOpen = false, contactInfoLoading = false, contactInfoError = "") }
    }

    fun mediaUrl(message: MessageDto): String {
        val base = _uiState.value.apiBase.trim().removeSuffix("/")
        val direct = message.mediaUrl.orEmpty().trim()
        if (direct.isNotBlank()) return resolveMediaUrl(base, direct)
        val mediaId = message.mediaId.orEmpty().trim()
        if (mediaId.isBlank() || base.isBlank()) return ""
        return "$base/api/media/proxy/$mediaId"
    }

    fun uiTime(raw: String?): String = DateTimeUtils.formatForUi(raw)

    private suspend fun refreshConversations(notifyNew: Boolean) {
        val stateBefore = _uiState.value
        _uiState.update { it.copy(loadingConversations = true, error = "") }
        runCatching {
            repository.listConversations(
                search = stateBefore.search.trim(),
                channel = stateBefore.channel,
            )
        }.onSuccess { list ->
            maybeNotifyIncoming(list, notifyNew)
            _uiState.update { current ->
                current.copy(
                    loadingConversations = false,
                    conversations = list,
                    error = "",
                )
            }
        }.onFailure { e ->
            _uiState.update { it.copy(loadingConversations = false, error = e.message ?: "Error de carga") }
        }
    }

    private suspend fun loadMessages(phone: String) {
        _uiState.update { it.copy(loadingMessages = true, error = "") }
        runCatching {
            repository.listMessages(phone = phone, channel = _uiState.value.channel)
        }.onSuccess { list ->
            _uiState.update { it.copy(loadingMessages = false, messages = list) }
        }.onFailure { e ->
            _uiState.update { it.copy(loadingMessages = false, error = e.message ?: "No se pudieron cargar mensajes") }
        }
    }

    private suspend fun markRead(phone: String) {
        runCatching { repository.markConversationRead(phone) }
    }

    private suspend fun loadProducts(query: String) {
        _uiState.update { it.copy(productsLoading = true, productsError = "") }
        runCatching {
            repository.listWcProducts(
                q = query.trim(),
                page = 1,
                perPage = 24,
            )
        }.onSuccess { list ->
            _uiState.update {
                it.copy(
                    productsLoading = false,
                    products = list,
                    productsError = "",
                )
            }
        }.onFailure { e ->
            _uiState.update {
                it.copy(
                    productsLoading = false,
                    productsError = e.message ?: "No se pudo cargar catalogo",
                )
            }
        }
    }

    private fun resolveOutboundChannel(state: InboxUiState): String {
        val current = state.channel.lowercase().trim()
        if (current in setOf("whatsapp", "facebook", "instagram", "tiktok")) return current
        val conv = state.conversations.firstOrNull { it.phone == state.selectedPhone }
        val fromConversation = conv?.lastChannel?.trim()?.lowercase().orEmpty()
        return if (fromConversation in setOf("whatsapp", "facebook", "instagram", "tiktok")) {
            fromConversation
        } else {
            "whatsapp"
        }
    }

    private fun maybeNotifyIncoming(list: List<ConversationDto>, notifyNew: Boolean) {
        val selected = _uiState.value.selectedPhone
        if (!didFirstConversationsLoad) {
            didFirstConversationsLoad = true
            previousConversationTs.clear()
            list.forEach { item ->
                val ts = DateTimeUtils.toEpochMillis(item.updatedAt) ?: 0L
                previousConversationTs[item.phone] = ts
            }
            return
        }
        if (!notifyNew) {
            list.forEach { item ->
                val ts = DateTimeUtils.toEpochMillis(item.updatedAt) ?: 0L
                previousConversationTs[item.phone] = ts
            }
            return
        }

        for (conv in list) {
            val current = DateTimeUtils.toEpochMillis(conv.updatedAt) ?: 0L
            val previous = previousConversationTs[conv.phone] ?: 0L
            if (current > previous && conv.phone != selected) {
                val preview = conv.lastText.ifBlank { conv.text }
                NotificationHelper.notifyIncomingMessage(
                    context = appContext,
                    phone = conv.phone,
                    preview = preview,
                )
                break
            }
        }

        list.forEach { item ->
            val ts = DateTimeUtils.toEpochMillis(item.updatedAt) ?: 0L
            previousConversationTs[item.phone] = ts
        }
    }

    private suspend fun readBytesFromUri(uri: Uri): PickedFile = withContext(Dispatchers.IO) {
        val resolver = appContext.contentResolver
        val mime = resolver.getType(uri).orEmpty().ifBlank { "application/octet-stream" }
        val displayName = queryDisplayName(uri) ?: "archivo_${System.currentTimeMillis()}"
        val bytes = resolver.openInputStream(uri)?.use { it.readBytes() }
            ?: throw IllegalStateException("No se pudo leer el archivo")
        if (bytes.isEmpty()) throw IllegalStateException("El archivo esta vacio")
        if (bytes.size > 15 * 1024 * 1024) {
            throw IllegalStateException("El archivo supera 15MB")
        }
        PickedFile(
            bytes = bytes,
            fileName = displayName,
            mimeType = mime,
            kind = guessKind(mime),
        )
    }

    private fun queryDisplayName(uri: Uri): String? {
        val resolver = appContext.contentResolver
        resolver.query(uri, null, null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && cursor.moveToFirst()) {
                return cursor.getString(index)
            }
        }
        return null
    }

    private fun guessKind(mime: String): String {
        return when {
            mime.startsWith("image/") -> "image"
            mime.startsWith("video/") -> "video"
            mime.startsWith("audio/") -> "audio"
            else -> "document"
        }
    }

    private fun resolveMediaUrl(apiBase: String, rawUrl: String): String {
        val clean = rawUrl.trim()
        if (clean.isBlank()) return ""

        val lower = clean.lowercase()
        if (lower.startsWith("http://") || lower.startsWith("https://")) return clean
        if (clean.startsWith("//")) return "https:$clean"
        if (apiBase.isBlank()) return clean
        if (clean.startsWith("/")) return "$apiBase$clean"
        return "$apiBase/$clean"
    }

    private data class PickedFile(
        val bytes: ByteArray,
        val fileName: String,
        val mimeType: String,
        val kind: String,
    )
}
