package com.verane.mobile.feature.setup

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

private val roleOptions = listOf("admin", "supervisor", "agente")

@Composable
fun SetupScreen(
    viewModel: SetupViewModel,
    onSaved: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text("Configuracion inicial", style = MaterialTheme.typography.headlineSmall)
                Text(
                    "Conecta la app movil al backend actual. Puedes editar estos valores despues.",
                    style = MaterialTheme.typography.bodyMedium,
                )

                OutlinedTextField(
                    value = state.apiBase,
                    onValueChange = viewModel::updateApiBase,
                    label = { Text("API Base URL") },
                    placeholder = { Text("https://backend.perfumesverane.com") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )

                OutlinedTextField(
                    value = state.webAppBase,
                    onValueChange = viewModel::updateWebBase,
                    label = { Text("Web App URL") },
                    placeholder = { Text("https://app.perfumesverane.com") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )

                OutlinedTextField(
                    value = state.securityToken,
                    onValueChange = viewModel::updateToken,
                    label = { Text("Security Bearer Token (opcional)") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
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
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Sincronizacion en segundo plano (15 min)")
                    Switch(
                        checked = state.backgroundSyncEnabled,
                        onCheckedChange = viewModel::updateBackgroundSync,
                    )
                }

                if (state.error.isNotBlank()) {
                    Text(
                        text = state.error,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
                if (state.success.isNotBlank()) {
                    Text(
                        text = state.success,
                        color = MaterialTheme.colorScheme.primary,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }

                Button(
                    onClick = { viewModel.save(onSaved) },
                    enabled = !state.saving,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(if (state.saving) "Guardando..." else "Guardar y continuar")
                }
            }
        }
    }
}
