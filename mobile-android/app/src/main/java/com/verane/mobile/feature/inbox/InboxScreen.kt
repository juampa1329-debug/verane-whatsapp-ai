
package com.verane.mobile.feature.inbox

import android.Manifest
import android.content.pm.PackageManager
import android.view.ViewGroup
import android.media.MediaRecorder
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.EmojiEmotions
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.TextButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView
import androidx.compose.ui.viewinterop.AndroidView
import coil.compose.AsyncImage
import com.verane.mobile.core.network.ConversationDto
import com.verane.mobile.core.network.CustomerDto
import com.verane.mobile.core.network.MessageDto
import com.verane.mobile.core.network.WcProductDto
import kotlinx.coroutines.delay
import java.io.File

private val channels = listOf("all", "whatsapp", "facebook", "instagram", "tiktok")
private val quickEmojis = listOf("😀", "😁", "😂", "🤣", "😊", "😉", "😍", "😎", "🤔", "🙏", "👏", "🔥", "💯", "🎉", "❤️", "👍")

private val WaHeaderGreen = Color(0xFF075E54)
private val WaHeaderDark = Color(0xFF0B3C36)
private val WaAccent = Color(0xFF25D366)
private val WaBubbleIn = Color(0xFFFFFFFF)
private val WaBubbleOut = Color(0xFFD9FDD3)
private val WaChatBg = Color(0xFFEDE5DD)
private val WaListBgTop = Color(0xFFEFF8F3)
private val WaListBgBottom = Color(0xFFF4F6F7)

@Composable
fun InboxScreen(
    viewModel: InboxViewModel,
    modifier: Modifier = Modifier,
    onOpenCustomerCrm: (String) -> Unit = {},
) {
    val context = LocalContext.current
    val uriHandler = LocalUriHandler.current
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    var attachMenuOpen by rememberSaveable { mutableStateOf(false) }
    var emojiMenuOpen by rememberSaveable { mutableStateOf(false) }
    var isRecording by rememberSaveable { mutableStateOf(false) }
    var recordingError by rememberSaveable { mutableStateOf("") }
    var recordingSeconds by rememberSaveable { mutableStateOf(0) }
    var recordingStartMs by remember { mutableLongStateOf(0L) }
    var recorder by remember { mutableStateOf<MediaRecorder?>(null) }
    var recordingFile by remember { mutableStateOf<File?>(null) }
    val pulseTransition = rememberInfiniteTransition(label = "recording_pulse")
    val recordingPulse by pulseTransition.animateFloat(
        initialValue = 0.35f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 750),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "recording_pulse_alpha",
    )

    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent(),
    ) { uri ->
        attachMenuOpen = false
        if (uri != null) viewModel.sendMediaFromUri(uri)
    }

    val micPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (!granted) {
            recordingError = "Debes habilitar permiso de microfono para grabar audio"
        }
    }

    LaunchedEffect(isRecording) {
        while (isRecording) {
            delay(1000)
            recordingSeconds += 1
        }
    }

    fun releaseRecorder() {
        runCatching { recorder?.reset() }
        runCatching { recorder?.release() }
        recorder = null
    }

    fun startRecording() {
        val hasPermission = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.RECORD_AUDIO,
        ) == PackageManager.PERMISSION_GRANTED
        if (!hasPermission) {
            micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            return
        }

        if (isRecording) return

        recordingError = ""
        runCatching {
            val out = File(context.cacheDir, "audio_${System.currentTimeMillis()}.m4a")
            val mediaRecorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                MediaRecorder(context)
            } else {
                MediaRecorder()
            }
            mediaRecorder.setAudioSource(MediaRecorder.AudioSource.MIC)
            mediaRecorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            mediaRecorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            mediaRecorder.setAudioEncodingBitRate(128000)
            mediaRecorder.setAudioSamplingRate(44100)
            mediaRecorder.setOutputFile(out.absolutePath)
            mediaRecorder.prepare()
            mediaRecorder.start()

            recorder = mediaRecorder
            recordingFile = out
            recordingStartMs = System.currentTimeMillis()
            recordingSeconds = 0
            isRecording = true
        }.onFailure {
            releaseRecorder()
            recordingFile = null
            isRecording = false
            recordingError = "No se pudo iniciar grabacion"
        }
    }

    fun stopRecording(send: Boolean) {
        if (!isRecording) return
        isRecording = false

        val file = recordingFile
        val durationSec = ((System.currentTimeMillis() - recordingStartMs) / 1000L).toInt().coerceAtLeast(1)

        val stopOk = runCatching {
            recorder?.stop()
            true
        }.getOrElse { false }

        releaseRecorder()
        recordingFile = null

        if (!stopOk || file == null || !file.exists()) {
            runCatching { file?.delete() }
            recordingError = "No se pudo completar la grabacion"
            return
        }

        if (!send) {
            runCatching { file.delete() }
            return
        }

        val bytes = runCatching { file.readBytes() }.getOrNull()
        runCatching { file.delete() }

        if (bytes == null || bytes.isEmpty()) {
            recordingError = "Audio vacio, intenta de nuevo"
            return
        }

        viewModel.sendRecordedAudio(
            bytes = bytes,
            fileName = file.name,
            mimeType = "audio/mp4",
            durationSec = durationSec,
        )
    }

    DisposableEffect(Unit) {
        onDispose {
            runCatching {
                if (isRecording) {
                    stopRecording(send = false)
                }
            }
            releaseRecorder()
            runCatching { recordingFile?.delete() }
        }
    }

    val selectedConversation = state.conversations.firstOrNull { it.phone == state.selectedPhone }
    val showList = state.selectedPhone == null || selectedConversation == null
    val messagesListState = rememberLazyListState()
    var forceBottomScroll by rememberSaveable(state.selectedPhone) { mutableStateOf(true) }

    LaunchedEffect(state.selectedPhone) {
        forceBottomScroll = true
    }

    LaunchedEffect(state.messages.size, state.selectedPhone, showList) {
        if (showList || state.messages.isEmpty()) return@LaunchedEffect
        val lastIndex = state.messages.lastIndex
        val lastVisible = messagesListState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: -1
        val nearBottom = lastVisible >= lastIndex - 1
        if (forceBottomScroll || nearBottom) {
            messagesListState.scrollToItem(lastIndex)
            forceBottomScroll = false
        }
    }

    if (showList) {
        Column(
            modifier = modifier
                .fillMaxSize()
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(WaListBgTop, WaListBgBottom),
                    ),
                )
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Surface(
                color = Color.Transparent,
                shape = RoundedCornerShape(18.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(
                    modifier = Modifier
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(WaHeaderGreen, WaHeaderDark),
                            ),
                            shape = RoundedCornerShape(18.dp),
                        )
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Chats",
                                style = MaterialTheme.typography.titleLarge,
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                            )
                            Text(
                                text = "${state.conversations.size} conversaciones",
                                color = Color.White.copy(alpha = 0.82f),
                                style = MaterialTheme.typography.labelMedium,
                            )
                        }
                        IconButton(onClick = viewModel::refreshNow) {
                            Icon(Icons.Default.Refresh, contentDescription = "Recargar", tint = Color.White)
                        }
                    }

                    OutlinedTextField(
                        value = state.search,
                        onValueChange = viewModel::updateSearch,
                        label = { Text("Buscar conversaciones") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        channels.forEach { ch ->
                            val active = state.channel == ch
                            AssistChip(
                                onClick = { viewModel.setChannel(ch) },
                                label = { Text(ch) },
                                leadingIcon = if (active) {
                                    { Icon(Icons.Default.Storefront, contentDescription = null) }
                                } else {
                                    null
                                },
                            )
                        }
                    }
                }
            }

            if (state.loadingConversations) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                ) {
                    CircularProgressIndicator(modifier = Modifier.size(28.dp), color = WaHeaderGreen)
                }
            }

            if (state.error.isNotBlank()) {
                Text(state.error, color = MaterialTheme.colorScheme.error)
            }

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.conversations, key = { it.phone }) { conv ->
                    ConversationItem(
                        conversation = conv,
                        onClick = { viewModel.selectConversation(conv.phone) },
                        timeText = viewModel.uiTime(conv.updatedAt),
                    )
                }
            }
        }
        return
    }
    val activeConversation = selectedConversation ?: return

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(WaChatBg),
    ) {
        Surface(
            color = Color.Transparent,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        brush = Brush.horizontalGradient(
                            colors = listOf(WaHeaderGreen, WaHeaderDark),
                        ),
                    )
                    .padding(horizontal = 10.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = viewModel::clearSelection) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Volver", tint = Color.White)
                }

                Row(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(10.dp))
                        .clickable { viewModel.openContactInfo() }
                        .padding(vertical = 2.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF1F7A6B)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = contactInitials(activeConversation),
                            color = Color.White,
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = FontWeight.Bold,
                        )
                    }

                    Spacer(Modifier.width(10.dp))

                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = contactName(activeConversation),
                            color = Color.White,
                            style = MaterialTheme.typography.titleMedium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            text = "Toca para ver perfil - ${activeConversation.phone}",
                            color = Color.White.copy(alpha = 0.85f),
                            style = MaterialTheme.typography.bodySmall,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = null,
                        tint = Color.White.copy(alpha = 0.9f),
                    )
                }

                Column(horizontalAlignment = Alignment.End) {
                    Text("Takeover", color = Color.White, style = MaterialTheme.typography.labelSmall)
                    Switch(
                        checked = activeConversation.takeover,
                        onCheckedChange = { viewModel.toggleTakeover() },
                    )
                }
            }
        }

        if (state.loadingMessages) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.Center,
            ) {
                CircularProgressIndicator(modifier = Modifier.size(22.dp), color = WaHeaderGreen)
            }
        }

        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(WaChatBg),
            )
            Box(
                modifier = Modifier
                    .size(260.dp)
                    .offset(x = (-80).dp, y = (-50).dp)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.13f)),
            )
            Box(
                modifier = Modifier
                    .size(220.dp)
                    .align(Alignment.BottomEnd)
                    .offset(x = 70.dp, y = 40.dp)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.11f)),
            )

            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 10.dp, vertical = 8.dp),
                state = messagesListState,
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.messages, key = { it.id }) { msg ->
                    MessageBubble(
                        message = msg,
                        timeText = viewModel.uiTime(msg.createdAt),
                        mediaUrl = viewModel.mediaUrl(msg),
                        onOpenMedia = { url -> uriHandler.openUri(url) },
                    )
                }
            }
        }

        if (recordingError.isNotBlank()) {
            Text(
                text = recordingError,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 2.dp),
            )
        }

        if (state.error.isNotBlank()) {
            Text(
                text = state.error,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 2.dp),
            )
        }

        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = Color(0xFFF6F6F6),
            shadowElevation = 4.dp,
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                HorizontalDivider()

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 6.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box {
                        IconButton(
                            onClick = {
                                emojiMenuOpen = false
                                attachMenuOpen = true
                            },
                            enabled = !state.sending && !isRecording,
                        ) {
                            Icon(Icons.Default.AttachFile, contentDescription = "Adjuntar")
                        }
                        DropdownMenu(
                            expanded = attachMenuOpen,
                            onDismissRequest = { attachMenuOpen = false },
                        ) {
                            DropdownMenuItem(
                                text = { Text("Imagen") },
                                onClick = { picker.launch("image/*") },
                            )
                            DropdownMenuItem(
                                text = { Text("Video") },
                                onClick = { picker.launch("video/*") },
                            )
                            DropdownMenuItem(
                                text = { Text("Audio") },
                                onClick = { picker.launch("audio/*") },
                            )
                            DropdownMenuItem(
                                text = { Text("Documento") },
                                onClick = { picker.launch("*/*") },
                            )
                            DropdownMenuItem(
                                text = { Text("Producto (Catalogo)") },
                                leadingIcon = { Icon(Icons.Default.Storefront, contentDescription = null) },
                                onClick = {
                                    attachMenuOpen = false
                                    viewModel.openProductCatalog()
                                },
                            )
                        }
                    }

                    Box {
                        IconButton(
                            onClick = {
                                attachMenuOpen = false
                                emojiMenuOpen = true
                            },
                            enabled = !state.sending && !isRecording,
                        ) {
                            Icon(Icons.Default.EmojiEmotions, contentDescription = "Emojis")
                        }
                        DropdownMenu(
                            expanded = emojiMenuOpen,
                            onDismissRequest = { emojiMenuOpen = false },
                        ) {
                            quickEmojis.forEach { emoji ->
                                DropdownMenuItem(
                                    text = {
                                        Text(
                                            text = emoji,
                                            style = MaterialTheme.typography.titleMedium,
                                        )
                                    },
                                    onClick = {
                                        viewModel.updateDraft(state.draft + emoji)
                                        emojiMenuOpen = false
                                    },
                                )
                            }
                        }
                    }

                    IconButton(
                        onClick = {
                            if (isRecording) stopRecording(send = true) else startRecording()
                        },
                        enabled = !state.sending,
                    ) {
                        Icon(
                            if (isRecording) Icons.Default.Stop else Icons.Default.Mic,
                            contentDescription = if (isRecording) "Detener grabacion" else "Grabar audio",
                            tint = if (isRecording) WaAccent else MaterialTheme.colorScheme.onSurface,
                        )
                    }

                    if (isRecording) {
                        Surface(
                            modifier = Modifier
                                .weight(1f)
                                .padding(horizontal = 6.dp),
                            color = Color(0xFFE8F5E9),
                            shape = RoundedCornerShape(18.dp),
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(8.dp)
                                        .clip(CircleShape)
                                        .alpha(recordingPulse)
                                        .background(Color(0xFFD32F2F)),
                                )
                                Text("Grabando ${formatTimer(recordingSeconds)}")
                            }
                        }
                    } else {
                        OutlinedTextField(
                            value = state.draft,
                            onValueChange = viewModel::updateDraft,
                            placeholder = { Text("Escribe un mensaje") },
                            modifier = Modifier.weight(1f),
                            minLines = 1,
                            maxLines = 4,
                            shape = RoundedCornerShape(22.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = Color(0xFF9BC3B8),
                                unfocusedBorderColor = Color(0xFFD5E5DF),
                            ),
                            keyboardOptions = KeyboardOptions(
                                capitalization = KeyboardCapitalization.Sentences,
                            ),
                        )
                    }

                    IconButton(
                        onClick = viewModel::sendTextMessage,
                        enabled = !state.sending && !isRecording,
                    ) {
                        Icon(
                            Icons.AutoMirrored.Filled.Send,
                            contentDescription = "Enviar",
                            tint = WaHeaderGreen,
                        )
                    }
                }
            }
        }
    }

    if (state.contactInfoOpen) {
        ContactInfoDialog(
            conversation = activeConversation,
            customer = state.contactInfoCustomer,
            loading = state.contactInfoLoading,
            error = state.contactInfoError,
            onDismiss = viewModel::closeContactInfo,
            onOpenCrm = {
                viewModel.closeContactInfo()
                onOpenCustomerCrm(activeConversation.phone)
            },
        )
    }

    if (state.productCatalogOpen) {
        ProductCatalogDialog(
            query = state.productSearch,
            loading = state.productsLoading,
            error = state.productsError,
            products = state.products,
            sendingProductId = state.sendingProductId,
            onDismiss = viewModel::closeProductCatalog,
            onQueryChange = viewModel::updateProductSearch,
            onSend = { product -> viewModel.sendCatalogProduct(product.id) },
        )
    }
}

@Composable
private fun ConversationItem(
    conversation: ConversationDto,
    onClick: () -> Unit,
    timeText: String,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        shape = RoundedCornerShape(14.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(Color(0xFFDCF8C6)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = contactInitials(conversation),
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1B5E20),
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = contactName(conversation),
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = channelShort(conversation.lastChannel),
                        style = MaterialTheme.typography.labelSmall,
                        color = Color(0xFF0B3C36),
                        modifier = Modifier
                            .clip(RoundedCornerShape(999.dp))
                            .background(Color(0xFFDDF4E8))
                            .padding(horizontal = 7.dp, vertical = 2.dp),
                    )
                    Text(
                        text = if (conversation.takeover) "Humano" else "Bot",
                        style = MaterialTheme.typography.labelSmall,
                        color = if (conversation.takeover) Color(0xFF6D1B7B) else Color(0xFF1B5E20),
                        modifier = Modifier
                            .clip(RoundedCornerShape(999.dp))
                            .background(if (conversation.takeover) Color(0xFFF3E5F5) else Color(0xFFE8F5E9))
                            .padding(horizontal = 7.dp, vertical = 2.dp),
                    )
                }
                Text(
                    text = conversation.lastText.ifBlank { conversation.text }.ifBlank { "Sin mensajes" },
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Column(horizontalAlignment = Alignment.End) {
                Text(timeText, style = MaterialTheme.typography.labelSmall)
                if (conversation.unreadCount > 0) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Box(
                        modifier = Modifier
                            .clip(CircleShape)
                            .background(WaAccent)
                            .padding(horizontal = 8.dp, vertical = 2.dp),
                    ) {
                        Text(
                            text = "${conversation.unreadCount}",
                            color = Color.White,
                            style = MaterialTheme.typography.labelSmall,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(
    message: MessageDto,
    timeText: String,
    mediaUrl: String,
    onOpenMedia: (String) -> Unit,
) {
    val incoming = message.direction.equals("in", ignoreCase = true)
    val bubbleColor = if (incoming) WaBubbleIn else WaBubbleOut
    val alignment = if (incoming) Alignment.Start else Alignment.End
    val bubbleShape = if (incoming) {
        RoundedCornerShape(topStart = 6.dp, topEnd = 14.dp, bottomEnd = 14.dp, bottomStart = 14.dp)
    } else {
        RoundedCornerShape(topStart = 14.dp, topEnd = 6.dp, bottomEnd = 14.dp, bottomStart = 14.dp)
    }

    Column(modifier = Modifier.fillMaxWidth(), horizontalAlignment = alignment) {
        Surface(
            color = bubbleColor,
            shape = bubbleShape,
            tonalElevation = 1.dp,
            shadowElevation = 1.dp,
            modifier = Modifier.fillMaxWidth(0.88f),
        ) {
            Column(
                modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                val mediaType = resolveBubbleMediaType(message, mediaUrl)
                if (mediaType == "image" && mediaUrl.isNotBlank()) {
                    AsyncImage(
                        model = mediaUrl,
                        contentDescription = "imagen",
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(210.dp)
                            .clip(RoundedCornerShape(10.dp)),
                    )
                } else if (mediaType == "video" && mediaUrl.isNotBlank()) {
                    InlineMediaPlayer(
                        mediaUrl = mediaUrl,
                        isAudio = false,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(220.dp)
                            .clip(RoundedCornerShape(12.dp)),
                    )
                } else if (mediaType == "audio" && mediaUrl.isNotBlank()) {
                    InlineAudioBubble(
                        mediaUrl = mediaUrl,
                        fileName = displayAttachmentName(message, mediaUrl),
                        durationSec = message.durationSec,
                        modifier = Modifier
                            .widthIn(max = 290.dp)
                            .clip(RoundedCornerShape(12.dp)),
                    )
                } else if (mediaType == "document" && mediaUrl.isNotBlank()) {
                    DocumentAttachmentCard(
                        fileName = displayAttachmentName(message, mediaUrl),
                        mimeType = message.mimeType.orEmpty(),
                        onOpen = { onOpenMedia(mediaUrl) },
                    )
                } else if (mediaUrl.isNotBlank()) {
                    Text(
                        text = "Adjunto",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(
                        text = "Abrir",
                        color = WaHeaderGreen,
                        style = MaterialTheme.typography.labelLarge,
                        modifier = Modifier.clickable { onOpenMedia(mediaUrl) },
                    )
                }

                if (message.text.isNotBlank()) {
                    Text(message.text, style = MaterialTheme.typography.bodyMedium)
                }
                if ((message.mediaCaption ?: "").isNotBlank()) {
                    Text(
                        message.mediaCaption.orEmpty(),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        timeText,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    if (!incoming) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = waTickText(message),
                            style = MaterialTheme.typography.labelSmall,
                            color = waTickColor(message),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DocumentAttachmentCard(
    fileName: String,
    mimeType: String,
    onOpen: () -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = Color(0xFFF4F7F5),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onOpen),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 10.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(Color(0xFFDDE8E2)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Default.AttachFile,
                    contentDescription = null,
                    tint = Color(0xFF0B5E53),
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = fileName.ifBlank { "Documento" },
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = mimeType.ifBlank { "Archivo adjunto" },
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Text(
                text = "Abrir",
                color = WaHeaderGreen,
                style = MaterialTheme.typography.labelLarge,
            )
        }
    }
}

@Composable
private fun ContactInfoDialog(
    conversation: ConversationDto,
    customer: CustomerDto?,
    loading: Boolean,
    error: String,
    onDismiss: () -> Unit,
    onOpenCrm: () -> Unit,
) {
    val profile = customer ?: CustomerDto(
        phone = conversation.phone,
        firstName = conversation.firstName,
        lastName = conversation.lastName,
        city = conversation.city,
        customerType = conversation.customerType,
        interests = conversation.interests,
        tags = conversation.tags,
        notes = conversation.notes,
        takeover = conversation.takeover,
    )

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(18.dp),
            tonalElevation = 4.dp,
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("Perfil del cliente", style = MaterialTheme.typography.titleMedium)
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Cerrar")
                    }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(
                        modifier = Modifier
                            .size(52.dp)
                            .clip(CircleShape)
                            .background(Color(0xFFDDF4E8)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = contactInitials(conversation),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF0B5E53),
                        )
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = customerName(profile).ifBlank { conversation.phone },
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text(conversation.phone, style = MaterialTheme.typography.bodySmall)
                    }
                }

                if (loading) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(22.dp))
                    }
                }

                if (error.isNotBlank()) {
                    Text(error, color = MaterialTheme.colorScheme.error)
                }

                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    color = Color(0xFFF4F7F5),
                ) {
                    Column(
                        modifier = Modifier.padding(10.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        ProfileLine("Modo", if (conversation.takeover) "Humano" else "Bot")
                        ProfileLine("Ciudad", profile.city.ifBlank { "-" })
                        ProfileLine("Tipo cliente", profile.customerType.ifBlank { "-" })
                        ProfileLine(
                            "Pago",
                            profile.paymentStatus.ifBlank {
                                profile.paymentReference.ifBlank { "-" }
                            },
                        )
                        if (profile.interests.isNotBlank()) {
                            ProfileLine("Intereses", profile.interests)
                        }
                        if (profile.tags.isNotBlank()) {
                            ProfileLine("Tags", profile.tags)
                        }
                    }
                }

                Button(
                    onClick = onOpenCrm,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Abrir en CRM")
                }
                TextButton(
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Cerrar")
                }
            }
        }
    }
}

@Composable
private fun ProductCatalogDialog(
    query: String,
    loading: Boolean,
    error: String,
    products: List<WcProductDto>,
    sendingProductId: Long?,
    onDismiss: () -> Unit,
    onQueryChange: (String) -> Unit,
    onSend: (WcProductDto) -> Unit,
) {
    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(18.dp),
            tonalElevation = 4.dp,
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("Catalogo WooCommerce", style = MaterialTheme.typography.titleMedium)
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Cerrar")
                    }
                }

                OutlinedTextField(
                    value = query,
                    onValueChange = onQueryChange,
                    label = { Text("Buscar producto") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )

                if (loading) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp))
                    }
                }

                if (error.isNotBlank()) {
                    Text(error, color = MaterialTheme.colorScheme.error)
                }

                LazyColumn(
                    modifier = Modifier.height(380.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(products, key = { it.id }) { product ->
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFF8F8F8)),
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(10.dp),
                                horizontalArrangement = Arrangement.spacedBy(10.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                if (product.featuredImage.isNotBlank()) {
                                    AsyncImage(
                                        model = product.featuredImage,
                                        contentDescription = "producto",
                                        modifier = Modifier
                                            .size(56.dp)
                                            .clip(RoundedCornerShape(10.dp)),
                                    )
                                } else {
                                    Box(
                                        modifier = Modifier
                                            .size(56.dp)
                                            .clip(RoundedCornerShape(10.dp))
                                            .background(Color(0xFFE9ECEF)),
                                        contentAlignment = Alignment.Center,
                                    ) {
                                        Icon(Icons.Default.Storefront, contentDescription = null)
                                    }
                                }

                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        product.name.ifBlank { "Producto" },
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis,
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.SemiBold,
                                    )
                                    val meta = listOf(product.brand, product.size)
                                        .filter { it.isNotBlank() }
                                        .joinToString(" | ")
                                    if (meta.isNotBlank()) {
                                        Text(
                                            text = meta,
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                    if (product.price.isNotBlank()) {
                                        Text(
                                            text = "$${product.price}",
                                            style = MaterialTheme.typography.labelMedium,
                                            color = Color(0xFF0B5D1E),
                                            modifier = Modifier
                                                .padding(top = 2.dp)
                                                .clip(RoundedCornerShape(999.dp))
                                                .background(Color(0xFFDDF6E6))
                                                .padding(horizontal = 8.dp, vertical = 2.dp),
                                        )
                                    }
                                }

                                Button(
                                    onClick = { onSend(product) },
                                    enabled = sendingProductId != product.id,
                                ) {
                                    Text(if (sendingProductId == product.id) "Enviando" else "Enviar")
                                }
                            }
                        }
                    }
                }

                if (!loading && error.isBlank() && products.isEmpty()) {
                    Text("No hay productos para esa busqueda")
                }
            }
        }
    }
}

private fun contactName(conversation: ConversationDto): String {
    val raw = "${conversation.firstName} ${conversation.lastName}".trim()
    return raw.ifBlank { conversation.phone }
}

private fun contactInitials(conversation: ConversationDto): String {
    val name = contactName(conversation)
    if (name.isBlank()) return "*"
    val pieces = name.split(" ").filter { it.isNotBlank() }
    if (pieces.isEmpty()) return "*"
    val first = pieces.first().take(1)
    val second = pieces.getOrNull(1)?.take(1).orEmpty()
    val combined = "$first$second".trim().uppercase()
    return combined.ifBlank { name.takeLast(2) }
}

private fun customerName(customer: CustomerDto): String {
    val raw = "${customer.firstName} ${customer.lastName}".trim()
    return raw.ifBlank { customer.phone }
}

@Composable
private fun ProfileLine(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.widthIn(max = 220.dp),
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

private fun formatTimer(seconds: Int): String {
    val safe = seconds.coerceAtLeast(0)
    val min = safe / 60
    val sec = safe % 60
    return "%02d:%02d".format(min, sec)
}

@Composable
private fun InlineAudioBubble(
    mediaUrl: String,
    fileName: String,
    durationSec: Int?,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    var isPlaying by remember(mediaUrl) { mutableStateOf(false) }
    var positionMs by remember(mediaUrl) { mutableLongStateOf(0L) }
    var totalDurationMs by remember(mediaUrl) { mutableLongStateOf((durationSec ?: 0).coerceAtLeast(0) * 1000L) }

    val exoPlayer = remember(mediaUrl) {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(mediaUrl))
            playWhenReady = false
            prepare()
        }
    }

    DisposableEffect(exoPlayer) {
        val listener = object : Player.Listener {
            override fun onIsPlayingChanged(playing: Boolean) {
                isPlaying = playing
            }

            override fun onPlaybackStateChanged(state: Int) {
                val dur = exoPlayer.duration
                if (dur > 0) totalDurationMs = dur
                if (state == Player.STATE_ENDED) {
                    positionMs = totalDurationMs
                    isPlaying = false
                }
            }
        }
        exoPlayer.addListener(listener)
        onDispose {
            exoPlayer.removeListener(listener)
            exoPlayer.release()
        }
    }

    LaunchedEffect(exoPlayer, isPlaying) {
        while (true) {
            positionMs = exoPlayer.currentPosition.coerceAtLeast(0L)
            val dur = exoPlayer.duration
            if (dur > 0) totalDurationMs = dur
            delay(if (isPlaying) 220 else 700)
        }
    }

    val safeDurationMs = totalDurationMs.coerceAtLeast(0L)
    val progress = if (safeDurationMs > 0) {
        (positionMs.toFloat() / safeDurationMs.toFloat()).coerceIn(0f, 1f)
    } else {
        0f
    }
    val totalSeconds = if (safeDurationMs > 0) (safeDurationMs / 1000L).toInt() else durationSec?.coerceAtLeast(0) ?: 0

    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        color = Color(0xFFF2F6F3),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(
                onClick = {
                    if (exoPlayer.isPlaying) {
                        exoPlayer.pause()
                    } else {
                        exoPlayer.play()
                    }
                },
                modifier = Modifier.size(34.dp),
            ) {
                Icon(
                    imageVector = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                    contentDescription = if (isPlaying) "Pausar audio" else "Reproducir audio",
                    tint = WaHeaderGreen,
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = fileName.ifBlank { "Audio" },
                    style = MaterialTheme.typography.labelMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                InlineAudioWaveform(
                    progress = progress,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 2.dp),
                )
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp)
                        .clip(RoundedCornerShape(999.dp))
                        .background(Color(0xFFC8D7D0)),
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(progress)
                            .height(3.dp)
                            .clip(RoundedCornerShape(999.dp))
                            .background(WaHeaderGreen),
                    )
                }
            }

            Text(
                text = formatTimer(totalSeconds),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun InlineAudioWaveform(
    progress: Float,
    modifier: Modifier = Modifier,
) {
    val bars = listOf(6, 10, 14, 9, 12, 16, 8, 13, 7, 11, 15, 9, 13, 8, 12, 10, 14, 9)
    Row(
        modifier = modifier.height(18.dp),
        horizontalArrangement = Arrangement.spacedBy(1.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        bars.forEachIndexed { index, rawHeight ->
            val ratio = if (bars.size <= 1) 1f else index.toFloat() / (bars.size - 1).toFloat()
            val active = ratio <= progress
            Box(
                modifier = Modifier
                    .width(2.dp)
                    .height((rawHeight * 0.75f).dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(if (active) WaHeaderGreen else Color(0xFF9CB3A8)),
            )
        }
    }
}

@Composable
private fun InlineMediaPlayer(
    mediaUrl: String,
    isAudio: Boolean,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val exoPlayer = remember(mediaUrl) {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(mediaUrl))
            playWhenReady = false
            prepare()
        }
    }

    DisposableEffect(exoPlayer) {
        onDispose { exoPlayer.release() }
    }

    AndroidView(
        modifier = modifier,
        factory = { viewContext ->
            PlayerView(viewContext).apply {
                player = exoPlayer
                useController = true
                resizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT
                setShowBuffering(PlayerView.SHOW_BUFFERING_WHEN_PLAYING)
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT,
                )
                if (isAudio) {
                    setShutterBackgroundColor(android.graphics.Color.TRANSPARENT)
                }
            }
        },
        update = { playerView ->
            if (playerView.player !== exoPlayer) {
                playerView.player = exoPlayer
            }
        },
    )
}

private fun waTickText(message: MessageDto): String {
    return when ((message.waStatus ?: "").trim().lowercase()) {
        "read" -> "\u2713\u2713"
        "delivered" -> "\u2713\u2713"
        "failed" -> "!"
        else -> "\u2713"
    }
}

private fun waTickColor(message: MessageDto): Color {
    return when ((message.waStatus ?: "").trim().lowercase()) {
        "read" -> Color(0xFF34B7F1)
        "failed" -> Color(0xFFD32F2F)
        else -> Color(0xFF6B7280)
    }
}

private fun channelShort(raw: String): String {
    return when (raw.trim().lowercase()) {
        "whatsapp" -> "WA"
        "facebook" -> "FB"
        "instagram" -> "IG"
        "tiktok" -> "TT"
        else -> "ALL"
    }
}

private fun resolveBubbleMediaType(message: MessageDto, mediaUrl: String): String {
    val explicit = message.msgType.trim().lowercase()
    if (explicit in setOf("image", "video", "audio", "document")) return explicit

    val mime = message.mimeType.orEmpty().trim().lowercase()
    if (mime.startsWith("image/")) return "image"
    if (mime.startsWith("video/")) return "video"
    if (mime.startsWith("audio/")) return "audio"
    if (mime.isNotBlank()) return "document"

    val extension = fileExtension(message.fileName.orEmpty())
        .ifBlank { fileExtension(mediaUrl) }
        .lowercase()
    if (extension in setOf("jpg", "jpeg", "png", "gif", "webp", "bmp")) return "image"
    if (extension in setOf("mp4", "mov", "webm", "mkv", "3gp")) return "video"
    if (extension in setOf("mp3", "m4a", "aac", "ogg", "opus", "wav")) return "audio"

    return if (mediaUrl.isNotBlank() || message.fileName.orEmpty().isNotBlank()) "document" else "text"
}

private fun displayAttachmentName(message: MessageDto, mediaUrl: String): String {
    val fileName = message.fileName.orEmpty().trim()
    if (fileName.isNotBlank()) return fileName

    val raw = mediaUrl.trim()
    if (raw.isBlank()) return "Adjunto"
    val clean = raw.substringBefore("?").substringBefore("#").trimEnd('/', '\\')
    val tail = clean.substringAfterLast('/').substringAfterLast('\\')
    return tail.ifBlank { "Adjunto" }
}

private fun fileExtension(raw: String): String {
    val clean = raw.substringBefore("?").substringBefore("#")
    val dot = clean.lastIndexOf('.')
    if (dot < 0 || dot == clean.lastIndex) return ""
    return clean.substring(dot + 1)
}
