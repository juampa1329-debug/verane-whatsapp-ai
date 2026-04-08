package com.verane.mobile.feature.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

private val ranges = listOf("7d", "30d", "90d")

@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel,
    modifier: Modifier = Modifier,
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                ranges.forEach { range ->
                    AssistChip(
                        onClick = { viewModel.setRange(range) },
                        label = { Text(range) },
                    )
                }
            }
            IconButton(onClick = viewModel::refresh) {
                Icon(Icons.Default.Refresh, contentDescription = "Recargar")
            }
        }

        if (state.loading) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
            ) {
                CircularProgressIndicator()
            }
        }

        if (state.error.isNotBlank()) {
            Text(state.error, color = MaterialTheme.colorScheme.error)
        }
        if (state.success.isNotBlank()) {
            Text(state.success, color = MaterialTheme.colorScheme.primary)
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Text("KPIs", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        KpiLine("Conversaciones", state.kpis.conversationsTotal)
                        KpiLine("Activas", state.kpis.activeConversations)
                        KpiLine("Sin leer", state.kpis.unreadConversations)
                        KpiLine("Takeover ON", state.kpis.takeoverOn)
                        KpiLine("Nuevos clientes", state.kpis.newCustomers)
                        KpiLine("Campanas en vivo", state.kpis.campaignsLive)
                        KpiLine("Mensajes IN", state.kpis.messagesIn)
                        KpiLine("Mensajes OUT", state.kpis.messagesOut)
                        KpiLine("Response rate", "${state.kpis.responseRatePct}%")
                    }
                }
            }

            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Text("Funnel", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        state.funnel.forEach { step ->
                            KpiLine("${step.label}", "${step.value} (${step.pctPrev}%)")
                        }
                    }
                }
            }

            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Text("Campanas", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        KpiLine("Pending", state.campaignMetrics.pending)
                        KpiLine("Processing", state.campaignMetrics.processing)
                        KpiLine("Sent", state.campaignMetrics.sent)
                        KpiLine("Delivered", state.campaignMetrics.delivered)
                        KpiLine("Read", state.campaignMetrics.read)
                        KpiLine("Replied", state.campaignMetrics.replied)
                        KpiLine("Failed", state.campaignMetrics.failed)
                        KpiLine("Delivery rate", "${state.campaignMetrics.deliveryRatePct}%")
                        KpiLine("Read rate", "${state.campaignMetrics.readRatePct}%")
                        KpiLine("Reply rate", "${state.campaignMetrics.replyRatePct}%")
                    }
                }
            }

            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Text("Remarketing", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        KpiLine("Flows", state.remarketingFlowsTotal)
                        KpiLine("Flows activos", state.remarketingFlowsActive)
                        KpiLine("Steps", state.remarketingStepsTotal)
                    }
                }
            }

            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Text("Motores", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)

                        Text("Campaign engine", fontWeight = FontWeight.SemiBold)
                        KpiLine("Enabled", state.campaignEngine.enabled)
                        KpiLine("Running", state.campaignEngine.running)
                        KpiLine("Interval sec", state.campaignEngine.intervalSec)
                        KpiLine("Batch size", state.campaignEngine.batchSize)
                        KpiLine("Send delay ms", state.campaignEngine.sendDelayMs)
                        TextButton(onClick = viewModel::tickCampaignEngine) {
                            Text("Ejecutar tick campaign")
                        }

                        HorizontalDivider()

                        Text("Remarketing engine", fontWeight = FontWeight.SemiBold)
                        KpiLine("Enabled", state.remarketingEngine.enabled)
                        KpiLine("Running", state.remarketingEngine.running)
                        KpiLine("Runner", state.remarketingEngine.runner)
                        KpiLine("Interval sec", state.remarketingEngine.intervalSec)
                        KpiLine("Batch size", state.remarketingEngine.batchSize)
                        KpiLine("New enrollments/flow", state.remarketingEngine.newEnrollmentsPerFlow)
                        KpiLine("Resume after min", state.remarketingEngine.resumeAfterMinutes)
                        KpiLine("Retry min", state.remarketingEngine.retryMinutes)
                        KpiLine("Service window h", state.remarketingEngine.serviceWindowHours)
                        TextButton(onClick = viewModel::tickRemarketingEngine) {
                            Text("Ejecutar tick remarketing")
                        }
                    }
                }
            }
        }
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
