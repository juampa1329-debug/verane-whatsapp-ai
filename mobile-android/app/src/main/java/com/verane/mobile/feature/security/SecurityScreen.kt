package com.verane.mobile.feature.security

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

private val roleOptions = listOf("admin", "supervisor", "agente")
private val auditLevels = listOf("all", "high", "medium", "low")

@Composable
fun SecurityScreen(
    viewModel: SecurityViewModel,
    modifier: Modifier = Modifier,
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

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
                        Text("Seguridad", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                        IconButton(onClick = viewModel::refresh) {
                            Icon(Icons.Default.Refresh, contentDescription = "Recargar")
                        }
                    }
                    KpiLine("Rol activo", state.role)
                    KpiLine("Auth habilitada", state.authEnabled)
                    KpiLine("Open mode", state.authOpenMode)
                    KpiLine("Roles configurados", state.configuredRoles.joinToString(", ").ifBlank { "-" })
                    KpiLine("Rotation running", state.rotationRunning)
                    KpiLine("Rotation interval", state.rotationIntervalSec)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        TextButton(onClick = viewModel::clearOutputSecrets) {
                            Text("Limpiar secretos")
                        }
                        if (state.isAdmin) {
                            TextButton(onClick = viewModel::runRotationTick) {
                                Text("Tick rotation")
                            }
                        }
                    }
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

        if (state.error.isNotBlank()) {
            item { Text(state.error, color = MaterialTheme.colorScheme.error) }
        }
        if (state.success.isNotBlank()) {
            item { Text(state.success, color = MaterialTheme.colorScheme.primary) }
        }
        if (state.processing) {
            item { Text("Procesando...", style = MaterialTheme.typography.bodySmall) }
        }

        if (state.lastTempPassword.isNotBlank() || state.lastPlainSecret.isNotBlank() || state.lastTwofaSecret.isNotBlank()) {
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Text("Salida sensible", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        if (state.lastTempPassword.isNotBlank()) {
                            Text("Temp password: ${state.lastTempPassword}")
                        }
                        if (state.lastPlainSecret.isNotBlank()) {
                            Text("API key plain secret: ${state.lastPlainSecret}")
                        }
                        if (state.lastTwofaSecret.isNotBlank()) {
                            Text("2FA secret: ${state.lastTwofaSecret}")
                        }
                        if (state.lastTwofaUri.isNotBlank()) {
                            Text("2FA URI: ${state.lastTwofaUri}")
                        }
                    }
                }
            }
        }

        item {
            SummaryCard(state = state)
        }

        if (state.canAccess) {
            item { AlertsCard(state = state, viewModel = viewModel) }
            item { SessionsCard(state = state, viewModel = viewModel) }
            item { AuditCard(state = state, viewModel = viewModel) }
        }

        if (state.isAdmin) {
            item { PolicyCard(state = state, viewModel = viewModel) }
            item { MfaCard(state = state, viewModel = viewModel) }
            item { UsersCard(state = state, viewModel = viewModel) }
            item { KeysCard(state = state, viewModel = viewModel) }
        } else {
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Modo supervisor/agente: politicas MFA, usuarios y API keys en solo lectura.",
                        modifier = Modifier.padding(12.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun SummaryCard(state: SecurityUiState) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text("Resumen", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            KpiLine("Usuarios totales", state.summary.totalUsers)
            KpiLine("Usuarios activos", state.summary.activeUsers)
            KpiLine("Usuarios con 2FA", state.summary.usersWith2fa)
            KpiLine("Sesiones abiertas", state.summary.openSessions)
            KpiLine("Eventos criticos 24h", state.summary.criticalEvents24h)
        }
    }
}

@Composable
private fun PolicyCard(state: SecurityUiState, viewModel: SecurityViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Politicas", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = state.policyPasswordMinLength,
                onValueChange = viewModel::updatePolicyPasswordMinLength,
                label = { Text("Password min length") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.policyAccessTokenMinutes,
                onValueChange = viewModel::updatePolicyAccessTokenMinutes,
                label = { Text("Access token minutes") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.policySessionIdleMinutes,
                onValueChange = viewModel::updatePolicySessionIdleMinutes,
                label = { Text("Session idle minutes") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.policyForceRotationDays,
                onValueChange = viewModel::updatePolicyForceRotationDays,
                label = { Text("Force password rotation days") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Require special chars")
                Switch(
                    checked = state.policyRequireSpecialChars,
                    onCheckedChange = viewModel::updatePolicyRequireSpecialChars,
                )
            }
            TextButton(onClick = viewModel::savePolicy) {
                Text("Guardar politicas")
            }
        }
    }
}

@Composable
private fun MfaCard(state: SecurityUiState, viewModel: SecurityViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text("MFA", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            SwitchLine("Enforce admins", state.mfaEnforceAdmins, viewModel::updateMfaEnforceAdmins)
            SwitchLine("Enforce supervisors", state.mfaEnforceSupervisors, viewModel::updateMfaEnforceSupervisors)
            SwitchLine("Allow agents", state.mfaAllowAgents, viewModel::updateMfaAllowAgents)
            SwitchLine("Backup codes", state.mfaBackupCodes, viewModel::updateMfaBackupCodes)
            TextButton(onClick = viewModel::saveMfaPolicy) {
                Text("Guardar MFA")
            }
        }
    }
}

@Composable
private fun AlertsCard(state: SecurityUiState, viewModel: SecurityViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text("Alertas", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            SwitchLine("Failed login", state.alertsFailedLogin, viewModel::updateAlertsFailedLogin)
            SwitchLine("Suspicious IP", state.alertsSuspiciousIp, viewModel::updateAlertsSuspiciousIp)
            SwitchLine("Security changes", state.alertsSecurityChange, viewModel::updateAlertsSecurityChange)
            SwitchLine("Webhook failures", state.alertsWebhookFailure, viewModel::updateAlertsWebhookFailure)
            SwitchLine("Canal email", state.alertsChannelEmail, viewModel::updateAlertsChannelEmail)
            SwitchLine("Canal whatsapp", state.alertsChannelWhatsapp, viewModel::updateAlertsChannelWhatsapp)
            TextButton(onClick = viewModel::saveAlertsPolicy) {
                Text("Guardar alertas")
            }
        }
    }
}

@Composable
private fun UsersCard(state: SecurityUiState, viewModel: SecurityViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Usuarios", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = state.userName,
                onValueChange = viewModel::updateUserName,
                label = { Text("Nombre") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.userEmail,
                onValueChange = viewModel::updateUserEmail,
                label = { Text("Email") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.userPassword,
                onValueChange = viewModel::updateUserPassword,
                label = { Text("Password (opcional)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            Text("Rol", fontWeight = FontWeight.SemiBold)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                roleOptions.forEach { role ->
                    AssistChip(
                        onClick = { viewModel.updateUserRole(role) },
                        label = {
                            val marker = if (state.userRole == role) "*" else ""
                            Text("$marker$role")
                        },
                    )
                }
            }
            SwitchLine("Activo", state.userActive, viewModel::updateUserActive)
            SwitchLine("2FA setup", state.userTwofa, viewModel::updateUserTwofa)
            TextButton(onClick = viewModel::createUser) {
                Text("Crear usuario")
            }

            HorizontalDivider()
            Text("Lista", fontWeight = FontWeight.SemiBold)
            state.users.forEach { user ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("${user.name} (${user.email})", fontWeight = FontWeight.SemiBold)
                        KpiLine("Rol", user.role)
                        KpiLine("Activo", user.active)
                        KpiLine("2FA", user.twofa)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            TextButton(onClick = { viewModel.toggleUserActive(user) }) { Text("Toggle active") }
                            TextButton(onClick = { viewModel.promoteUser(user, "admin") }) { Text("Set admin") }
                            TextButton(onClick = { viewModel.promoteUser(user, "supervisor") }) { Text("Set supervisor") }
                            TextButton(onClick = { viewModel.promoteUser(user, "agente") }) { Text("Set agente") }
                        }
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            TextButton(onClick = { viewModel.resetUserPassword(user.id) }) { Text("Reset password") }
                            TextButton(onClick = { viewModel.setupUser2fa(user.id) }) { Text("Setup 2FA") }
                            TextButton(onClick = { viewModel.verifyUser2fa(user.id) }) { Text("Verify 2FA") }
                            TextButton(onClick = { viewModel.disableUser2fa(user.id) }) { Text("Disable 2FA") }
                        }
                    }
                }
            }

            OutlinedTextField(
                value = state.twofaCode,
                onValueChange = viewModel::updateTwofaCode,
                label = { Text("Codigo 2FA para Verify") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
        }
    }
}

@Composable
private fun SessionsCard(state: SecurityUiState, viewModel: SecurityViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text("Sesiones abiertas", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            if (state.isAdmin) {
                TextButton(onClick = viewModel::revokeAllSessions) {
                    Text("Revocar todas")
                }
            }
            state.sessions.forEach { session ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(session.userName.ifBlank { "Sin usuario" }, fontWeight = FontWeight.SemiBold)
                        Text("${session.device} | ${session.ip}", style = MaterialTheme.typography.bodySmall)
                    }
                    TextButton(onClick = { viewModel.revokeSession(session.id) }) {
                        Text("Revocar")
                    }
                }
            }
        }
    }
}

@Composable
private fun KeysCard(state: SecurityUiState, viewModel: SecurityViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("API keys", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = state.keyName,
                onValueChange = viewModel::updateKeyName,
                label = { Text("Nombre key") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.keyScope,
                onValueChange = viewModel::updateKeyScope,
                label = { Text("Scope") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.keyRotationDays,
                onValueChange = viewModel::updateKeyRotationDays,
                label = { Text("Rotation days") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            TextButton(onClick = viewModel::createKey) {
                Text("Crear key")
            }

            HorizontalDivider()
            state.keys.forEach { key ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(key.name, fontWeight = FontWeight.SemiBold)
                        KpiLine("Scope", key.scope)
                        KpiLine("Preview", key.value)
                        KpiLine("Activa", key.isActive)
                        KpiLine("Rotation days", key.rotationDays)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            TextButton(onClick = { viewModel.toggleKeyActive(key) }) { Text("Toggle active") }
                            TextButton(onClick = { viewModel.rotateKey(key.id) }) { Text("Rotar") }
                            TextButton(onClick = { viewModel.revealKey(key.id) }) { Text("Revelar") }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AuditCard(state: SecurityUiState, viewModel: SecurityViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Auditoria", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                auditLevels.forEach { level ->
                    AssistChip(
                        onClick = { viewModel.setAuditLevel(level) },
                        label = {
                            val marker = if (state.auditLevel == level) "*" else ""
                            Text("$marker$level")
                        },
                    )
                }
            }
            state.auditEvents.take(40).forEach { event ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(event.action, fontWeight = FontWeight.SemiBold)
                        Text(
                            "${event.level} | ${event.actor} | ${event.ip}",
                            style = MaterialTheme.typography.bodySmall,
                        )
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
        Text(label, style = MaterialTheme.typography.bodyMedium)
        Text(value.toString(), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
    }
}
