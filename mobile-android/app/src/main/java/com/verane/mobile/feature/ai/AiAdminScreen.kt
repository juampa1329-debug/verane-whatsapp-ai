package com.verane.mobile.feature.ai

import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@Composable
fun AiAdminScreen(
    viewModel: AiAdminViewModel,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    val filePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent(),
    ) { uri ->
        if (uri != null) {
            val (fileName, mimeType, bytes) = readFileFromUri(context, uri)
            if (bytes != null && fileName.isNotBlank()) {
                viewModel.uploadKnowledgeFile(
                    bytes = bytes,
                    fileName = fileName,
                    mimeType = mimeType.ifBlank { "application/octet-stream" },
                )
            }
        }
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text("AI + Knowledge + TTS", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                        IconButton(onClick = viewModel::refresh) {
                            Icon(Icons.Default.Refresh, contentDescription = "Recargar")
                        }
                    }
                    KpiLine("Rol activo", state.role)
                    KpiLine("Acceso", state.canAccess)
                }
            }
        }

        if (state.loading) {
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                ) {
                    CircularProgressIndicator()
                }
            }
        }

        if (state.processing) {
            item { Text("Procesando...", style = MaterialTheme.typography.bodySmall) }
        }
        if (state.error.isNotBlank()) {
            item { Text(state.error, color = MaterialTheme.colorScheme.error) }
        }
        if (state.success.isNotBlank()) {
            item { Text(state.success, color = MaterialTheme.colorScheme.primary) }
        }

        if (state.canAccess) {
            item { AiSettingsCard(state = state, viewModel = viewModel) }
            item { AiQaCard(state = state, viewModel = viewModel) }
            item { TtsCard(state = state, viewModel = viewModel) }
            item { UploadCard(state = state, onPickFile = { filePicker.launch("*/*") }, viewModel = viewModel) }
            item { FilesCard(state = state, viewModel = viewModel) }
            item { WebSourceComposerCard(state = state, viewModel = viewModel) }
            item { WebSourceListCard(state = state, viewModel = viewModel) }
        }
    }
}

@Composable
private fun AiSettingsCard(state: AiAdminUiState, viewModel: AiAdminViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("AI Settings", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            SwitchLine("AI enabled", state.isEnabled, viewModel::updateIsEnabled)
            Text("Provider")
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                state.providers.forEach { provider ->
                    AssistChip(
                        onClick = { viewModel.updateProvider(provider) },
                        label = {
                            val marker = if (state.provider == provider) "*" else ""
                            Text("$marker$provider")
                        },
                    )
                }
            }
            OutlinedTextField(
                value = state.model,
                onValueChange = viewModel::updateModel,
                label = { Text("Model") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            val providerModels = state.providerModels[state.provider].orEmpty()
            if (providerModels.isNotEmpty()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    providerModels.take(20).forEach { model ->
                        AssistChip(
                            onClick = { viewModel.updateModel(model) },
                            label = { Text(model) },
                        )
                    }
                }
            }
            OutlinedTextField(
                value = state.fallbackProvider,
                onValueChange = viewModel::updateFallbackProvider,
                label = { Text("Fallback provider") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.fallbackModel,
                onValueChange = viewModel::updateFallbackModel,
                label = { Text("Fallback model") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.maxTokens,
                onValueChange = viewModel::updateMaxTokens,
                label = { Text("Max tokens") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.temperature,
                onValueChange = viewModel::updateTemperature,
                label = { Text("Temperature") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.timeoutSec,
                onValueChange = viewModel::updateTimeoutSec,
                label = { Text("Timeout sec") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.maxRetries,
                onValueChange = viewModel::updateMaxRetries,
                label = { Text("Max retries") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.systemPrompt,
                onValueChange = viewModel::updateSystemPrompt,
                label = { Text("System prompt") },
                modifier = Modifier.fillMaxWidth(),
            )

            HorizontalDivider()
            Text("Voice + TTS", fontWeight = FontWeight.SemiBold)
            SwitchLine("Voice enabled", state.voiceEnabled, viewModel::updateVoiceEnabled)
            OutlinedTextField(
                value = state.voiceLanguage,
                onValueChange = viewModel::updateVoiceLanguage,
                label = { Text("Voice language") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.voiceAccent,
                onValueChange = viewModel::updateVoiceAccent,
                label = { Text("Voice accent") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                state.ttsProviders.forEach { provider ->
                    AssistChip(
                        onClick = { viewModel.updateVoiceTtsProvider(provider) },
                        label = {
                            val marker = if (state.voiceTtsProvider == provider) "*" else ""
                            Text("$marker$provider")
                        },
                    )
                }
            }
            OutlinedTextField(
                value = state.voiceTtsVoiceId,
                onValueChange = viewModel::updateVoiceTtsVoiceId,
                label = { Text("TTS voice id") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.voiceTtsModelId,
                onValueChange = viewModel::updateVoiceTtsModelId,
                label = { Text("TTS model id") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.voiceSpeakingRate,
                onValueChange = viewModel::updateVoiceSpeakingRate,
                label = { Text("Voice speaking rate") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            HorizontalDivider()
            Text("Multimodal", fontWeight = FontWeight.SemiBold)
            SwitchLine("MM enabled", state.mmEnabled, viewModel::updateMmEnabled)
            OutlinedTextField(
                value = state.mmProvider,
                onValueChange = viewModel::updateMmProvider,
                label = { Text("MM provider") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.mmModel,
                onValueChange = viewModel::updateMmModel,
                label = { Text("MM model") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            TextButton(onClick = viewModel::saveAiSettings) {
                Text("Guardar AI settings")
            }
        }
    }
}

@Composable
private fun AiQaCard(state: AiAdminUiState, viewModel: AiAdminViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("QA AI", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = state.testPhone,
                onValueChange = viewModel::updateTestPhone,
                label = { Text("Telefono") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.testText,
                onValueChange = viewModel::updateTestText,
                label = { Text("Texto prueba") },
                modifier = Modifier.fillMaxWidth(),
            )
            TextButton(onClick = viewModel::testProcessMessage) {
                Text("Probar process-message")
            }
            if (state.testReply.isNotBlank()) {
                Text(state.testReply, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun TtsCard(state: AiAdminUiState, viewModel: AiAdminViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("TTS test", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = state.testTtsText,
                onValueChange = viewModel::updateTestTtsText,
                label = { Text("Texto TTS") },
                modifier = Modifier.fillMaxWidth(),
            )
            TextButton(onClick = viewModel::testTts) {
                Text("Probar TTS")
            }
            if (state.testTtsResult.isNotBlank()) {
                Text(state.testTtsResult, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun UploadCard(
    state: AiAdminUiState,
    onPickFile: () -> Unit,
    viewModel: AiAdminViewModel,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Knowledge upload", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = state.uploadNotes,
                onValueChange = viewModel::updateUploadNotes,
                label = { Text("Notas del archivo") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            TextButton(onClick = onPickFile) {
                Text("Seleccionar y subir archivo")
            }
        }
    }
}

@Composable
private fun FilesCard(state: AiAdminUiState, viewModel: AiAdminViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Knowledge files", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            state.files.forEach { file ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(file.fileName, fontWeight = FontWeight.SemiBold)
                        KpiLine("Mime", file.mimeType)
                        KpiLine("Size", file.sizeBytes)
                        KpiLine("Active", file.isActive)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            TextButton(onClick = { viewModel.reindexFile(file.id) }) { Text("Reindex") }
                            TextButton(onClick = { viewModel.deleteFile(file.id) }) { Text("Eliminar") }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun WebSourceComposerCard(state: AiAdminUiState, viewModel: AiAdminViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Web sources", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = state.webUrl,
                onValueChange = viewModel::updateWebUrl,
                label = { Text("URL") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.webSourceName,
                onValueChange = viewModel::updateWebSourceName,
                label = { Text("Nombre fuente") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.webNotes,
                onValueChange = viewModel::updateWebNotes,
                label = { Text("Notas") },
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = state.webSyncInterval,
                onValueChange = viewModel::updateWebSyncInterval,
                label = { Text("Sync interval min") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.webTimeoutSec,
                onValueChange = viewModel::updateWebTimeoutSec,
                label = { Text("Timeout sec") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            SwitchLine("Activa", state.webActive, viewModel::updateWebActive)
            SwitchLine("Auto sync", state.webAutoSync, viewModel::updateWebAutoSync)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = viewModel::createWebSource) {
                    Text("Crear web source")
                }
                TextButton(onClick = viewModel::syncDueWebSources) {
                    Text("Sync due")
                }
            }
        }
    }
}

@Composable
private fun WebSourceListCard(state: AiAdminUiState, viewModel: AiAdminViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Lista web sources", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            state.webSources.forEach { source ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(source.sourceName.ifBlank { source.url }, fontWeight = FontWeight.SemiBold)
                        Text(source.url, style = MaterialTheme.typography.bodySmall)
                        KpiLine("Active", source.isActive)
                        KpiLine("Auto sync", source.autoSync)
                        KpiLine("Status", source.lastStatus)
                        if (source.lastError.isNotBlank()) {
                            Text(source.lastError, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                        }
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            TextButton(onClick = { viewModel.toggleWebSourceActive(source) }) { Text("Toggle active") }
                            TextButton(onClick = { viewModel.syncWebSource(source.id) }) { Text("Sync now") }
                            TextButton(onClick = { viewModel.deleteWebSource(source.id) }) { Text("Eliminar") }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SwitchLine(label: String, value: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label)
        Switch(checked = value, onCheckedChange = onChange)
    }
}

@Composable
private fun KpiLine(label: String, value: Any) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label)
        Text(value.toString(), fontWeight = FontWeight.SemiBold)
    }
}

private fun readFileFromUri(context: android.content.Context, uri: Uri): Triple<String, String, ByteArray?> {
    val resolver = context.contentResolver
    val mime = resolver.getType(uri).orEmpty()
    var fileName = ""
    resolver.query(uri, null, null, null, null)?.use { cursor ->
        val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
        if (idx >= 0 && cursor.moveToFirst()) {
            fileName = cursor.getString(idx).orEmpty()
        }
    }
    if (fileName.isBlank()) {
        fileName = "knowledge_upload.bin"
    }
    val bytes = runCatching {
        resolver.openInputStream(uri)?.use { it.readBytes() }
    }.getOrNull()
    return Triple(fileName, mime, bytes)
}
