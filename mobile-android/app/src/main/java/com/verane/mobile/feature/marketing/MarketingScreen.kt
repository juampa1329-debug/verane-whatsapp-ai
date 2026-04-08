package com.verane.mobile.feature.marketing

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
import androidx.compose.material3.Checkbox
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

private val channels = listOf("whatsapp", "facebook", "instagram", "tiktok", "all")
private val templateStatusFilters = listOf("all", "draft", "active", "paused", "archived")
private val campaignStatusFilters = listOf("all", "draft", "scheduled", "processing", "sent", "paused")
private val yesNoAll = listOf("all", "yes", "no")

@Composable
fun MarketingScreen(
    viewModel: MarketingViewModel,
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
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            channels.forEach { channel ->
                AssistChip(
                    onClick = { viewModel.setChannel(channel) },
                    label = {
                        val marker = if (channel == state.channel) "*" else ""
                        Text("$marker$channel")
                    },
                )
            }
            IconButton(onClick = viewModel::refreshAll) {
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

        if (state.processing) {
            Text("Procesando...", style = MaterialTheme.typography.bodySmall)
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
                FiltersCard(state = state, viewModel = viewModel)
            }

            item {
                CampaignComposerCard(state = state, viewModel = viewModel)
            }

            item {
                TemplateEditorCard(state = state, viewModel = viewModel)
            }

            item {
                Text("Templates", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            }
            items(state.templates, key = { it.id }) { template ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Checkbox(
                            checked = state.selectedTemplateIds.contains(template.id),
                            onCheckedChange = { viewModel.toggleTemplateSelection(template.id) },
                        )
                        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(template.name, fontWeight = FontWeight.SemiBold)
                            Text(
                                "${template.channel} | ${template.status} | ${template.category}",
                                style = MaterialTheme.typography.bodySmall,
                            )
                            Text(
                                template.body,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            TextButton(onClick = { viewModel.beginTemplateEdit(template) }) {
                                Text("Editar")
                            }
                            TextButton(onClick = { viewModel.deleteTemplate(template.id) }) {
                                Text("Eliminar")
                            }
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
                        Text("Engines", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        KpiLine("Campaign running", state.campaignEngine.running)
                        KpiLine("Campaign batch", state.campaignEngine.batchSize)
                        TextButton(onClick = viewModel::tickCampaignEngine) {
                            Text("Tick campaign engine")
                        }
                        HorizontalDivider()
                        KpiLine("Remarketing running", state.remarketingEngine.running)
                        KpiLine("Remarketing batch", state.remarketingEngine.batchSize)
                        TextButton(onClick = viewModel::tickRemarketingEngine) {
                            Text("Tick remarketing engine")
                        }
                    }
                }
            }

            item {
                Text("Campanas", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            }
            items(state.campaigns, key = { it.id }) { campaign ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Text(campaign.name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        KpiLine("Estado", campaign.status)
                        KpiLine("Canal", campaign.channel)
                        KpiLine("Segmento", campaign.segmentName ?: "-")
                        KpiLine("Template", campaign.templateName ?: "-")
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            TextButton(onClick = { viewModel.launchCampaign(campaign.id) }) {
                                Text("Lanzar")
                            }
                            TextButton(onClick = { viewModel.deleteCampaign(campaign.id) }) {
                                Text("Eliminar")
                            }
                        }
                    }
                }
            }
            item {
                TriggerEditorCard(state = state, viewModel = viewModel)
            }

            item {
                Text("Triggers", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            }
            items(state.triggers, key = { it.id }) { trigger ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Checkbox(
                            checked = state.selectedTriggerIds.contains(trigger.id),
                            onCheckedChange = { viewModel.toggleTriggerSelection(trigger.id) },
                        )
                        Column(modifier = Modifier.weight(1f)) {
                            Text(trigger.name, fontWeight = FontWeight.SemiBold)
                            Text("${trigger.eventType} | ${trigger.triggerType}", style = MaterialTheme.typography.bodySmall)
                            Text("Exec: ${trigger.executionsCount} | Priority: ${trigger.priority}", style = MaterialTheme.typography.bodySmall)
                        }
                        Switch(
                            checked = trigger.isActive,
                            onCheckedChange = { viewModel.toggleTrigger(trigger) },
                        )
                        Column(horizontalAlignment = Alignment.End) {
                            TextButton(onClick = { viewModel.beginTriggerEdit(trigger) }) {
                                Text("Editar")
                            }
                            TextButton(onClick = { viewModel.deleteTrigger(trigger.id) }) {
                                Text("Eliminar")
                            }
                        }
                    }
                }
            }

            item {
                FlowEditorCard(state = state, viewModel = viewModel)
            }

            item {
                Text("Remarketing flows", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            }
            items(state.flows, key = { it.id }) { flow ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Checkbox(
                            checked = state.selectedFlowIds.contains(flow.id),
                            onCheckedChange = { viewModel.toggleFlowSelection(flow.id) },
                        )
                        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(flow.name, fontWeight = FontWeight.SemiBold)
                            KpiLine("Activo", flow.isActive)
                            KpiLine("Steps", flow.stepsCount)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            TextButton(onClick = { viewModel.selectFlow(flow.id) }) {
                                Text("Detalle")
                            }
                            TextButton(onClick = { viewModel.dispatchFlow(flow.id) }) {
                                Text("Dispatch")
                            }
                            TextButton(onClick = { viewModel.beginFlowEdit(flow) }) {
                                Text("Editar")
                            }
                            TextButton(onClick = { viewModel.deleteFlow(flow.id) }) {
                                Text("Eliminar")
                            }
                        }
                    }
                }
            }

            if (state.selectedFlowId != null) {
                item {
                    SelectedFlowCard(state = state, viewModel = viewModel)
                }
            }
        }
    }
}

@Composable
private fun FiltersCard(
    state: MarketingUiState,
    viewModel: MarketingViewModel,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Filtros", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)

            Text("Templates por estado", fontWeight = FontWeight.SemiBold)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                templateStatusFilters.forEach { status ->
                    AssistChip(
                        onClick = { viewModel.setTemplateStatusFilter(status) },
                        label = {
                            val marker = if (state.templateStatusFilter == status) "*" else ""
                            Text("$marker$status")
                        },
                    )
                }
            }

            OutlinedTextField(
                value = state.templateSearch,
                onValueChange = viewModel::setTemplateSearch,
                label = { Text("Buscar template") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            TextButton(onClick = viewModel::applyTemplateSearch) {
                Text("Aplicar busqueda")
            }

            Text("Campanas por estado", fontWeight = FontWeight.SemiBold)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                campaignStatusFilters.forEach { status ->
                    AssistChip(
                        onClick = { viewModel.setCampaignStatusFilter(status) },
                        label = {
                            val marker = if (state.campaignStatusFilter == status) "*" else ""
                            Text("$marker$status")
                        },
                    )
                }
            }

            Text("Triggers activos", fontWeight = FontWeight.SemiBold)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                yesNoAll.forEach { value ->
                    AssistChip(
                        onClick = { viewModel.setTriggerActiveFilter(value) },
                        label = {
                            val marker = if (state.triggerActiveFilter == value) "*" else ""
                            Text("$marker$value")
                        },
                    )
                }
            }

            Text("Flows activos", fontWeight = FontWeight.SemiBold)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                yesNoAll.forEach { value ->
                    AssistChip(
                        onClick = { viewModel.setFlowActiveFilter(value) },
                        label = {
                            val marker = if (state.flowActiveFilter == value) "*" else ""
                            Text("$marker$value")
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun CampaignComposerCard(
    state: MarketingUiState,
    viewModel: MarketingViewModel,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Quick campaign", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)

            OutlinedTextField(
                value = state.campaignName,
                onValueChange = viewModel::updateCampaignName,
                label = { Text("Nombre") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.campaignObjective,
                onValueChange = viewModel::updateCampaignObjective,
                label = { Text("Objetivo") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Text("Segmento", fontWeight = FontWeight.SemiBold)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                state.segments.take(30).forEach { segment ->
                    AssistChip(
                        onClick = { viewModel.selectSegment(segment.id) },
                        label = {
                            val marker = if (state.selectedSegmentId == segment.id) "*" else ""
                            Text("$marker${segment.name}")
                        },
                    )
                }
            }

            Text("Template", fontWeight = FontWeight.SemiBold)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                state.templates.take(30).forEach { template ->
                    AssistChip(
                        onClick = { viewModel.selectCampaignTemplate(template.id) },
                        label = {
                            val marker = if (state.selectedCampaignTemplateId == template.id) "*" else ""
                            Text("$marker${template.name}")
                        },
                    )
                }
            }

            TextButton(onClick = viewModel::createCampaignQuick, modifier = Modifier.fillMaxWidth()) {
                Text("Crear campana")
            }
        }
    }
}

@Composable
private fun TemplateEditorCard(
    state: MarketingUiState,
    viewModel: MarketingViewModel,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            val modeLabel = if (state.templateEditorId == null) "Nuevo template" else "Editar template #${state.templateEditorId}"
            Text(modeLabel, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)

            OutlinedTextField(
                value = state.templateName,
                onValueChange = viewModel::updateTemplateName,
                label = { Text("Nombre") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.templateCategory,
                onValueChange = viewModel::updateTemplateCategory,
                label = { Text("Categoria") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.templateRenderMode,
                onValueChange = viewModel::updateTemplateRenderMode,
                label = { Text("Render mode") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.templateStatus,
                onValueChange = viewModel::updateTemplateStatus,
                label = { Text("Status") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.templateBody,
                onValueChange = viewModel::updateTemplateBody,
                label = { Text("Body") },
                modifier = Modifier.fillMaxWidth(),
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                TextButton(onClick = viewModel::saveTemplateEditor) {
                    Text("Guardar")
                }
                TextButton(onClick = viewModel::clearTemplateEditor) {
                    Text("Limpiar")
                }
            }

            HorizontalDivider()
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                AssistChip(onClick = viewModel::selectAllTemplatesOnPage, label = { Text("Seleccionar pagina") })
                AssistChip(onClick = viewModel::clearTemplateSelection, label = { Text("Limpiar seleccion") })
                AssistChip(onClick = viewModel::bulkDeleteTemplates, label = { Text("Eliminar seleccion") })
                AssistChip(onClick = { viewModel.bulkSetTemplateStatus("active") }, label = { Text("Set active") })
                AssistChip(onClick = { viewModel.bulkSetTemplateStatus("paused") }, label = { Text("Set paused") })
            }
        }
    }
}

@Composable
private fun TriggerEditorCard(
    state: MarketingUiState,
    viewModel: MarketingViewModel,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            val modeLabel = if (state.triggerEditorId == null) "Nuevo trigger" else "Editar trigger #${state.triggerEditorId}"
            Text(modeLabel, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)

            OutlinedTextField(
                value = state.triggerName,
                onValueChange = viewModel::updateTriggerName,
                label = { Text("Nombre") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.triggerEventType,
                onValueChange = viewModel::updateTriggerEventType,
                label = { Text("Event type") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.triggerType,
                onValueChange = viewModel::updateTriggerType,
                label = { Text("Trigger type") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.triggerFlowEvent,
                onValueChange = viewModel::updateTriggerFlowEvent,
                label = { Text("Flow event") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.triggerCooldownMinutes,
                onValueChange = viewModel::updateTriggerCooldown,
                label = { Text("Cooldown (min)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.triggerPriority,
                onValueChange = viewModel::updateTriggerPriority,
                label = { Text("Priority") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Activo", fontWeight = FontWeight.SemiBold)
                Switch(checked = state.triggerActive, onCheckedChange = viewModel::updateTriggerActive)
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                TextButton(onClick = viewModel::saveTriggerEditor) {
                    Text("Guardar")
                }
                TextButton(onClick = viewModel::clearTriggerEditor) {
                    Text("Limpiar")
                }
            }

            HorizontalDivider()
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                AssistChip(onClick = viewModel::selectAllTriggersOnPage, label = { Text("Seleccionar pagina") })
                AssistChip(onClick = viewModel::clearTriggerSelection, label = { Text("Limpiar seleccion") })
                AssistChip(onClick = viewModel::bulkDeleteTriggers, label = { Text("Eliminar seleccion") })
                AssistChip(onClick = { viewModel.bulkSetTriggersActive(true) }, label = { Text("Set active") })
                AssistChip(onClick = { viewModel.bulkSetTriggersActive(false) }, label = { Text("Set inactive") })
            }
        }
    }
}

@Composable
private fun FlowEditorCard(
    state: MarketingUiState,
    viewModel: MarketingViewModel,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            val modeLabel = if (state.flowEditorId == null) "Nuevo flow" else "Editar flow #${state.flowEditorId}"
            Text(modeLabel, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)

            OutlinedTextField(
                value = state.flowName,
                onValueChange = viewModel::updateFlowName,
                label = { Text("Nombre flow") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Activo", fontWeight = FontWeight.SemiBold)
                Switch(checked = state.flowActive, onCheckedChange = viewModel::updateFlowActive)
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                TextButton(onClick = viewModel::saveFlowEditor) {
                    Text("Guardar")
                }
                TextButton(onClick = viewModel::clearFlowEditor) {
                    Text("Limpiar")
                }
            }

            HorizontalDivider()
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                AssistChip(onClick = viewModel::selectAllFlowsOnPage, label = { Text("Seleccionar pagina") })
                AssistChip(onClick = viewModel::clearFlowSelection, label = { Text("Limpiar seleccion") })
                AssistChip(onClick = viewModel::bulkDeleteFlows, label = { Text("Eliminar seleccion") })
                AssistChip(onClick = { viewModel.bulkSetFlowsActive(true) }, label = { Text("Set active") })
                AssistChip(onClick = { viewModel.bulkSetFlowsActive(false) }, label = { Text("Set inactive") })
            }
        }
    }
}

@Composable
private fun SelectedFlowCard(
    state: MarketingUiState,
    viewModel: MarketingViewModel,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                "Flow seleccionado #${state.selectedFlowId}",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = { state.selectedFlowId?.let(viewModel::dispatchFlow) }) {
                    Text("Dispatch flow")
                }
                TextButton(onClick = { viewModel.selectFlow(null) }) {
                    Text("Cerrar detalle")
                }
            }

            HorizontalDivider()
            val stepMode = if (state.stepEditorId == null) "Nuevo step" else "Editar step #${state.stepEditorId}"
            Text(stepMode, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = state.stepOrder,
                onValueChange = viewModel::updateStepOrder,
                label = { Text("Orden") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.stepStageName,
                onValueChange = viewModel::updateStepStageName,
                label = { Text("Stage name") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.stepWaitMinutes,
                onValueChange = viewModel::updateStepWaitMinutes,
                label = { Text("Wait minutes") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Text("Template del step", fontWeight = FontWeight.SemiBold)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                AssistChip(
                    onClick = { viewModel.selectStepTemplate(null) },
                    label = {
                        val marker = if (state.stepTemplateId == null) "*" else ""
                        Text("${marker}Sin template")
                    },
                )
                state.templates.take(20).forEach { template ->
                    AssistChip(
                        onClick = { viewModel.selectStepTemplate(template.id) },
                        label = {
                            val marker = if (state.stepTemplateId == template.id) "*" else ""
                            Text("$marker${template.name}")
                        },
                    )
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = viewModel::saveStepEditor) {
                    Text("Guardar step")
                }
                TextButton(onClick = viewModel::clearStepEditor) {
                    Text("Limpiar step")
                }
            }

            HorizontalDivider()
            Text("Steps", fontWeight = FontWeight.SemiBold)
            state.selectedFlowSteps.forEach { step ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("#${step.stepOrder} ${step.stageName.ifBlank { "Sin nombre" }}")
                        Text(
                            "Wait ${step.waitMinutes} min | Template: ${step.templateName ?: "-"}",
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        TextButton(onClick = { viewModel.beginStepEdit(step) }) {
                            Text("Editar")
                        }
                        TextButton(onClick = { viewModel.dispatchStep(step.id) }) {
                            Text("Dispatch")
                        }
                        TextButton(onClick = { viewModel.deleteStep(step.id) }) {
                            Text("Eliminar")
                        }
                    }
                }
            }

            HorizontalDivider()
            Text("Enrollments (${state.selectedFlowEnrollments.size})", fontWeight = FontWeight.SemiBold)
            state.selectedFlowEnrollments.take(30).forEach { enrollment ->
                Text(
                    "${enrollment.phone} | ${enrollment.state} | step ${enrollment.currentStepOrder}",
                    style = MaterialTheme.typography.bodySmall,
                )
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
