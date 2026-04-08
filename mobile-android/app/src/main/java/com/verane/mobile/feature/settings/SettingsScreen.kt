package com.verane.mobile.feature.settings

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.verane.mobile.core.notifications.NotificationHelper
import com.verane.mobile.core.work.ConversationSyncWorker

private val roleOptions = listOf("admin", "supervisor", "agente")

@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            NotificationHelper.notifySyncUpdate(
                context,
                "Permiso concedido",
                "Las notificaciones estan habilitadas",
            )
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Ajustes de conexion", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = state.apiBase,
                    onValueChange = viewModel::updateApi,
                    label = { Text("API Base URL") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                OutlinedTextField(
                    value = state.webAppBase,
                    onValueChange = viewModel::updateWeb,
                    label = { Text("Web App URL") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                OutlinedTextField(
                    value = state.securityToken,
                    onValueChange = viewModel::updateToken,
                    label = { Text("Security Bearer Token (opcional)") },
                    modifier = Modifier.fillMaxWidth(),
                    visualTransformation = PasswordVisualTransformation(),
                )
                Text("Rol activo en app")
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    roleOptions.forEach { role ->
                        AssistChip(
                            onClick = { viewModel.updateSecurityRole(role) },
                            label = {
                                val marker = if (state.securityRole == role) "*" else ""
                                Text("$marker$role")
                            },
                        )
                    }
                }
                OutlinedTextField(
                    value = state.actorName,
                    onValueChange = viewModel::updateActorName,
                    label = { Text("Actor para auditoria (opcional)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text("Sync background cada 15 minutos")
                    Switch(
                        checked = state.backgroundSyncEnabled,
                        onCheckedChange = viewModel::updateBackgroundSync,
                    )
                }

                Button(
                    onClick = {
                        viewModel.save {
                            if (state.backgroundSyncEnabled) {
                                ConversationSyncWorker.schedule(context)
                            } else {
                                ConversationSyncWorker.cancel(context)
                            }
                        }
                    },
                    enabled = !state.saving,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(if (state.saving) "Guardando..." else "Guardar ajustes")
                }
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Notificaciones", style = MaterialTheme.typography.titleMedium)
                Button(
                    onClick = {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                            val granted = ContextCompat.checkSelfPermission(
                                context,
                                Manifest.permission.POST_NOTIFICATIONS,
                            ) == PackageManager.PERMISSION_GRANTED
                            if (!granted) {
                                permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Solicitar permiso de notificaciones")
                }
                Button(
                    onClick = {
                        NotificationHelper.notifySyncUpdate(
                            context = context,
                            title = "Prueba Verane",
                            body = "La app movil esta enviando notificaciones correctamente",
                        )
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Enviar notificacion de prueba")
                }
                OutlinedTextField(
                    value = state.pushTestTitle,
                    onValueChange = viewModel::updatePushTestTitle,
                    label = { Text("Push test title (backend)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                OutlinedTextField(
                    value = state.pushTestBody,
                    onValueChange = viewModel::updatePushTestBody,
                    label = { Text("Push test body (backend)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                Button(
                    onClick = viewModel::sendBackendPushTest,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Enviar push test real (FCM backend)")
                }
                Text(
                    text = if (state.firebaseToken.isBlank()) {
                        "FCM token: pendiente (se genera al integrar Firebase)"
                    } else {
                        "FCM token: ${state.firebaseToken.take(20)}..."
                    },
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }

        if (state.error.isNotBlank()) {
            Text(state.error, color = MaterialTheme.colorScheme.error)
        }
        if (state.success.isNotBlank()) {
            Text(state.success, color = MaterialTheme.colorScheme.primary)
        }
    }
}
