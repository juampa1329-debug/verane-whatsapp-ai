
package com.verane.mobile.feature.marketing

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.verane.mobile.core.network.CampaignDto
import com.verane.mobile.core.network.CampaignEngineStatusResponse
import com.verane.mobile.core.network.RemarketingEnrollmentDto
import com.verane.mobile.core.network.RemarketingEngineStatusResponse
import com.verane.mobile.core.network.RemarketingFlowDto
import com.verane.mobile.core.network.RemarketingStepDto
import com.verane.mobile.core.network.SegmentDto
import com.verane.mobile.core.network.TemplateDto
import com.verane.mobile.core.network.TriggerDto
import com.verane.mobile.core.repository.VeraneRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class MarketingUiState(
    val loading: Boolean = true,
    val processing: Boolean = false,
    val channel: String = "whatsapp",
    val error: String = "",
    val success: String = "",
    val templateStatusFilter: String = "all",
    val templateSearch: String = "",
    val campaignStatusFilter: String = "all",
    val triggerActiveFilter: String = "all",
    val flowActiveFilter: String = "all",
    val templates: List<TemplateDto> = emptyList(),
    val segments: List<SegmentDto> = emptyList(),
    val campaigns: List<CampaignDto> = emptyList(),
    val triggers: List<TriggerDto> = emptyList(),
    val flows: List<RemarketingFlowDto> = emptyList(),
    val campaignEngine: CampaignEngineStatusResponse = CampaignEngineStatusResponse(),
    val remarketingEngine: RemarketingEngineStatusResponse = RemarketingEngineStatusResponse(),
    val campaignName: String = "",
    val campaignObjective: String = "",
    val selectedSegmentId: Int? = null,
    val selectedCampaignTemplateId: Int? = null,
    val templateEditorId: Int? = null,
    val templateName: String = "",
    val templateCategory: String = "general",
    val templateBody: String = "",
    val templateRenderMode: String = "chat",
    val templateStatus: String = "draft",
    val triggerEditorId: Int? = null,
    val triggerName: String = "",
    val triggerEventType: String = "message_in",
    val triggerType: String = "message_flow",
    val triggerFlowEvent: String = "received",
    val triggerCooldownMinutes: String = "60",
    val triggerPriority: String = "100",
    val triggerActive: Boolean = true,
    val flowEditorId: Int? = null,
    val flowName: String = "",
    val flowActive: Boolean = false,
    val selectedTemplateIds: Set<Int> = emptySet(),
    val selectedTriggerIds: Set<Int> = emptySet(),
    val selectedFlowIds: Set<Int> = emptySet(),
    val selectedFlowId: Int? = null,
    val selectedFlowSteps: List<RemarketingStepDto> = emptyList(),
    val selectedFlowEnrollments: List<RemarketingEnrollmentDto> = emptyList(),
    val stepEditorId: Int? = null,
    val stepOrder: String = "1",
    val stepStageName: String = "",
    val stepWaitMinutes: String = "1440",
    val stepTemplateId: Int? = null,
)

class MarketingViewModel(
    private val repository: VeraneRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(MarketingUiState())
    val uiState: StateFlow<MarketingUiState> = _uiState.asStateFlow()

    init {
        refreshAll()
    }

    fun setChannel(channel: String) {
        _uiState.update {
            it.copy(
                channel = channel,
                selectedFlowId = null,
                selectedFlowSteps = emptyList(),
                selectedFlowEnrollments = emptyList(),
                error = "",
                success = "",
            )
        }
        refreshAll()
    }

    fun setTemplateStatusFilter(value: String) {
        _uiState.update { it.copy(templateStatusFilter = value) }
        refreshAll()
    }

    fun setTemplateSearch(value: String) {
        _uiState.update { it.copy(templateSearch = value) }
    }

    fun applyTemplateSearch() {
        refreshAll()
    }

    fun setCampaignStatusFilter(value: String) {
        _uiState.update { it.copy(campaignStatusFilter = value) }
        refreshAll()
    }

    fun setTriggerActiveFilter(value: String) {
        _uiState.update { it.copy(triggerActiveFilter = value) }
        refreshAll()
    }

    fun setFlowActiveFilter(value: String) {
        _uiState.update { it.copy(flowActiveFilter = value) }
        refreshAll()
    }

    fun updateCampaignName(value: String) = _uiState.update { it.copy(campaignName = value, error = "", success = "") }
    fun updateCampaignObjective(value: String) = _uiState.update { it.copy(campaignObjective = value, error = "", success = "") }
    fun selectSegment(id: Int?) = _uiState.update { it.copy(selectedSegmentId = id, error = "", success = "") }
    fun selectCampaignTemplate(id: Int?) = _uiState.update { it.copy(selectedCampaignTemplateId = id, error = "", success = "") }

    fun updateTemplateName(value: String) = _uiState.update { it.copy(templateName = value, error = "", success = "") }
    fun updateTemplateCategory(value: String) = _uiState.update { it.copy(templateCategory = value, error = "", success = "") }
    fun updateTemplateBody(value: String) = _uiState.update { it.copy(templateBody = value, error = "", success = "") }
    fun updateTemplateRenderMode(value: String) = _uiState.update { it.copy(templateRenderMode = value, error = "", success = "") }
    fun updateTemplateStatus(value: String) = _uiState.update { it.copy(templateStatus = value, error = "", success = "") }

    fun updateTriggerName(value: String) = _uiState.update { it.copy(triggerName = value, error = "", success = "") }
    fun updateTriggerEventType(value: String) = _uiState.update { it.copy(triggerEventType = value, error = "", success = "") }
    fun updateTriggerType(value: String) = _uiState.update { it.copy(triggerType = value, error = "", success = "") }
    fun updateTriggerFlowEvent(value: String) = _uiState.update { it.copy(triggerFlowEvent = value, error = "", success = "") }
    fun updateTriggerCooldown(value: String) = _uiState.update { it.copy(triggerCooldownMinutes = value, error = "", success = "") }
    fun updateTriggerPriority(value: String) = _uiState.update { it.copy(triggerPriority = value, error = "", success = "") }
    fun updateTriggerActive(value: Boolean) = _uiState.update { it.copy(triggerActive = value, error = "", success = "") }

    fun updateFlowName(value: String) = _uiState.update { it.copy(flowName = value, error = "", success = "") }
    fun updateFlowActive(value: Boolean) = _uiState.update { it.copy(flowActive = value, error = "", success = "") }

    fun updateStepOrder(value: String) = _uiState.update { it.copy(stepOrder = value, error = "", success = "") }
    fun updateStepStageName(value: String) = _uiState.update { it.copy(stepStageName = value, error = "", success = "") }
    fun updateStepWaitMinutes(value: String) = _uiState.update { it.copy(stepWaitMinutes = value, error = "", success = "") }
    fun selectStepTemplate(templateId: Int?) = _uiState.update { it.copy(stepTemplateId = templateId, error = "", success = "") }

    fun refreshAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = "", success = "") }
            runCatching {
                val state = _uiState.value
                val ch = state.channel

                val templates = repository.listTemplates(
                    channel = ch,
                    status = state.templateStatusFilter,
                    search = state.templateSearch.trim(),
                )
                val segments = repository.listSegments(active = "all")
                val campaigns = repository.listCampaigns(status = state.campaignStatusFilter, channel = ch)
                val triggers = repository.listTriggers(active = state.triggerActiveFilter, channel = ch)
                val allFlows = repository.listRemarketingFlows(channel = ch)
                val flows = when (state.flowActiveFilter) {
                    "yes" -> allFlows.filter { it.isActive }
                    "no" -> allFlows.filter { !it.isActive }
                    else -> allFlows
                }
                val campaignEngine = repository.campaignEngineStatus()
                val remarketingEngine = repository.remarketingEngineStatus()

                val selectedFlowId = state.selectedFlowId?.takeIf { sid -> flows.any { it.id == sid } }
                val selectedFlowSteps = if (selectedFlowId != null) {
                    repository.listRemarketingFlowSteps(selectedFlowId)
                } else {
                    emptyList()
                }
                val selectedFlowEnrollments = if (selectedFlowId != null) {
                    repository.listRemarketingEnrollments(flowId = selectedFlowId, state = "all", limit = 120)
                } else {
                    emptyList()
                }

                val templateIds = templates.map { it.id }.toSet()
                val triggerIds = triggers.map { it.id }.toSet()
                val flowIds = flows.map { it.id }.toSet()

                _uiState.update { current ->
                    current.copy(
                        loading = false,
                        templates = templates,
                        segments = segments,
                        campaigns = campaigns,
                        triggers = triggers,
                        flows = flows,
                        campaignEngine = campaignEngine,
                        remarketingEngine = remarketingEngine,
                        selectedSegmentId = current.selectedSegmentId?.takeIf { sid -> segments.any { it.id == sid } }
                            ?: segments.firstOrNull()?.id,
                        selectedCampaignTemplateId = current.selectedCampaignTemplateId?.takeIf { tid -> templates.any { it.id == tid } }
                            ?: templates.firstOrNull()?.id,
                        selectedTemplateIds = current.selectedTemplateIds.intersect(templateIds),
                        selectedTriggerIds = current.selectedTriggerIds.intersect(triggerIds),
                        selectedFlowIds = current.selectedFlowIds.intersect(flowIds),
                        selectedFlowId = selectedFlowId,
                        selectedFlowSteps = selectedFlowSteps,
                        selectedFlowEnrollments = selectedFlowEnrollments,
                        stepTemplateId = current.stepTemplateId?.takeIf { tid -> templates.any { it.id == tid } },
                    )
                }
            }.onFailure { e ->
                _uiState.update { it.copy(loading = false, error = e.message ?: "No se pudo cargar Marketing") }
            }
        }
    }
    fun createCampaignQuick() {
        val state = _uiState.value
        val name = state.campaignName.trim()
        if (name.isBlank()) {
            _uiState.update { it.copy(error = "Nombre de campana requerido") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                repository.createCampaign(
                    name = name,
                    objective = state.campaignObjective.trim(),
                    segmentId = state.selectedSegmentId,
                    templateId = state.selectedCampaignTemplateId,
                    channel = state.channel,
                    status = "draft",
                )
            }.onSuccess {
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = "Campana creada",
                        campaignName = "",
                        campaignObjective = "",
                    )
                }
                refreshAll()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo crear campana") }
            }
        }
    }

    fun launchCampaign(campaignId: Int) {
        runMutation("No se pudo lanzar campana", "Campana lanzada") {
            repository.launchCampaign(campaignId = campaignId, maxRecipients = 300)
        }
    }

    fun deleteCampaign(campaignId: Int) {
        runMutation("No se pudo eliminar campana", "Campana eliminada") {
            repository.deleteCampaign(campaignId)
        }
    }

    fun tickCampaignEngine() {
        runMutation("No se pudo ejecutar campaign engine", "Campaign engine ejecutado") {
            repository.campaignEngineTick(batchSize = 20, sendDelayMs = 0)
        }
    }

    fun tickRemarketingEngine() {
        runMutation("No se pudo ejecutar remarketing engine", "Remarketing engine ejecutado") {
            repository.remarketingEngineTick(limit = 600, flowId = 0, channel = _uiState.value.channel)
        }
    }

    fun beginTemplateEdit(template: TemplateDto) {
        _uiState.update {
            it.copy(
                templateEditorId = template.id,
                templateName = template.name,
                templateCategory = template.category.ifBlank { "general" },
                templateBody = template.body,
                templateRenderMode = template.renderMode.ifBlank { "chat" },
                templateStatus = template.status.ifBlank { "draft" },
                error = "",
                success = "",
            )
        }
    }

    fun clearTemplateEditor() {
        _uiState.update {
            it.copy(
                templateEditorId = null,
                templateName = "",
                templateCategory = "general",
                templateBody = "",
                templateRenderMode = "chat",
                templateStatus = "draft",
                error = "",
                success = "",
            )
        }
    }

    fun saveTemplateEditor() {
        val state = _uiState.value
        val name = state.templateName.trim()
        if (name.isBlank()) {
            _uiState.update { it.copy(error = "Nombre de template requerido") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                if (state.templateEditorId == null) {
                    repository.createTemplate(
                        name = name,
                        category = state.templateCategory.trim().ifBlank { "general" },
                        channel = state.channel,
                        body = state.templateBody,
                        renderMode = state.templateRenderMode,
                        status = state.templateStatus,
                    )
                } else {
                    repository.updateTemplate(
                        templateId = state.templateEditorId,
                        name = name,
                        category = state.templateCategory.trim().ifBlank { "general" },
                        channel = state.channel,
                        body = state.templateBody,
                        renderMode = state.templateRenderMode,
                        status = state.templateStatus,
                    )
                }
            }.onSuccess {
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = if (state.templateEditorId == null) "Template creado" else "Template actualizado",
                    )
                }
                clearTemplateEditor()
                refreshAll()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo guardar template") }
            }
        }
    }

    fun deleteTemplate(templateId: Int) {
        runMutation("No se pudo eliminar template", "Template eliminado") {
            repository.deleteTemplate(templateId)
        }
    }

    fun toggleTemplateSelection(templateId: Int) {
        _uiState.update { state ->
            val next = state.selectedTemplateIds.toMutableSet()
            if (!next.add(templateId)) next.remove(templateId)
            state.copy(selectedTemplateIds = next)
        }
    }

    fun selectAllTemplatesOnPage() {
        _uiState.update { state -> state.copy(selectedTemplateIds = state.templates.map { it.id }.toSet()) }
    }

    fun clearTemplateSelection() {
        _uiState.update { it.copy(selectedTemplateIds = emptySet()) }
    }

    fun bulkDeleteTemplates() {
        bulkAction(
            ids = _uiState.value.selectedTemplateIds,
            emptyMessage = "Selecciona templates para eliminar",
            successPrefix = "Templates eliminados",
            action = { id -> repository.deleteTemplate(id) },
            onDone = { _uiState.update { state -> state.copy(selectedTemplateIds = emptySet()) } },
        )
    }

    fun bulkSetTemplateStatus(status: String) {
        bulkAction(
            ids = _uiState.value.selectedTemplateIds,
            emptyMessage = "Selecciona templates para actualizar",
            successPrefix = "Templates actualizados",
            action = { id -> repository.updateTemplate(templateId = id, status = status) },
        )
    }

    fun beginTriggerEdit(trigger: TriggerDto) {
        _uiState.update {
            it.copy(
                triggerEditorId = trigger.id,
                triggerName = trigger.name,
                triggerEventType = trigger.eventType.ifBlank { "message_in" },
                triggerType = trigger.triggerType.ifBlank { "message_flow" },
                triggerFlowEvent = trigger.flowEvent.ifBlank { "received" },
                triggerCooldownMinutes = trigger.cooldownMinutes.toString(),
                triggerPriority = trigger.priority.toString(),
                triggerActive = trigger.isActive,
                error = "",
                success = "",
            )
        }
    }

    fun clearTriggerEditor() {
        _uiState.update {
            it.copy(
                triggerEditorId = null,
                triggerName = "",
                triggerEventType = "message_in",
                triggerType = "message_flow",
                triggerFlowEvent = "received",
                triggerCooldownMinutes = "60",
                triggerPriority = "100",
                triggerActive = true,
                error = "",
                success = "",
            )
        }
    }

    fun saveTriggerEditor() {
        val state = _uiState.value
        val name = state.triggerName.trim()
        val cooldown = state.triggerCooldownMinutes.trim().toIntOrNull()
        val priority = state.triggerPriority.trim().toIntOrNull()

        if (name.isBlank()) {
            _uiState.update { it.copy(error = "Nombre de trigger requerido") }
            return
        }
        if (cooldown == null || cooldown < 0) {
            _uiState.update { it.copy(error = "Cooldown invalido") }
            return
        }
        if (priority == null) {
            _uiState.update { it.copy(error = "Prioridad invalida") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                if (state.triggerEditorId == null) {
                    repository.createTrigger(
                        name = name,
                        channel = state.channel,
                        eventType = state.triggerEventType.trim().ifBlank { "message_in" },
                        triggerType = state.triggerType.trim().ifBlank { "message_flow" },
                        flowEvent = state.triggerFlowEvent.trim().ifBlank { "received" },
                        cooldownMinutes = cooldown,
                        priority = priority,
                        isActive = state.triggerActive,
                    )
                } else {
                    repository.updateTrigger(
                        triggerId = state.triggerEditorId,
                        name = name,
                        channel = state.channel,
                        eventType = state.triggerEventType.trim().ifBlank { "message_in" },
                        triggerType = state.triggerType.trim().ifBlank { "message_flow" },
                        flowEvent = state.triggerFlowEvent.trim().ifBlank { "received" },
                        cooldownMinutes = cooldown,
                        priority = priority,
                        isActive = state.triggerActive,
                    )
                }
            }.onSuccess {
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = if (state.triggerEditorId == null) "Trigger creado" else "Trigger actualizado",
                    )
                }
                clearTriggerEditor()
                refreshAll()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo guardar trigger") }
            }
        }
    }

    fun toggleTrigger(trigger: TriggerDto) {
        runMutation("No se pudo actualizar trigger", "Trigger actualizado") {
            repository.toggleTrigger(triggerId = trigger.id, active = !trigger.isActive)
        }
    }

    fun deleteTrigger(triggerId: Int) {
        runMutation("No se pudo eliminar trigger", "Trigger eliminado") {
            repository.deleteTrigger(triggerId)
        }
    }

    fun toggleTriggerSelection(triggerId: Int) {
        _uiState.update { state ->
            val next = state.selectedTriggerIds.toMutableSet()
            if (!next.add(triggerId)) next.remove(triggerId)
            state.copy(selectedTriggerIds = next)
        }
    }

    fun selectAllTriggersOnPage() {
        _uiState.update { state -> state.copy(selectedTriggerIds = state.triggers.map { it.id }.toSet()) }
    }

    fun clearTriggerSelection() {
        _uiState.update { it.copy(selectedTriggerIds = emptySet()) }
    }

    fun bulkDeleteTriggers() {
        bulkAction(
            ids = _uiState.value.selectedTriggerIds,
            emptyMessage = "Selecciona triggers para eliminar",
            successPrefix = "Triggers eliminados",
            action = { id -> repository.deleteTrigger(id) },
            onDone = { _uiState.update { state -> state.copy(selectedTriggerIds = emptySet()) } },
        )
    }

    fun bulkSetTriggersActive(active: Boolean) {
        bulkAction(
            ids = _uiState.value.selectedTriggerIds,
            emptyMessage = "Selecciona triggers para actualizar",
            successPrefix = "Triggers actualizados",
            action = { id -> repository.updateTrigger(triggerId = id, isActive = active) },
        )
    }

    fun beginFlowEdit(flow: RemarketingFlowDto) {
        _uiState.update {
            it.copy(
                flowEditorId = flow.id,
                flowName = flow.name,
                flowActive = flow.isActive,
                error = "",
                success = "",
            )
        }
    }

    fun clearFlowEditor() {
        _uiState.update {
            it.copy(
                flowEditorId = null,
                flowName = "",
                flowActive = false,
                error = "",
                success = "",
            )
        }
    }

    fun saveFlowEditor() {
        val state = _uiState.value
        val name = state.flowName.trim()
        if (name.isBlank()) {
            _uiState.update { it.copy(error = "Nombre de flow requerido") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                if (state.flowEditorId == null) {
                    repository.createRemarketingFlow(
                        name = name,
                        channel = state.channel,
                        isActive = state.flowActive,
                    )
                } else {
                    repository.updateRemarketingFlow(
                        flowId = state.flowEditorId,
                        name = name,
                        channel = state.channel,
                        isActive = state.flowActive,
                    )
                }
            }.onSuccess {
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = if (state.flowEditorId == null) "Flow creado" else "Flow actualizado",
                    )
                }
                clearFlowEditor()
                refreshAll()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo guardar flow") }
            }
        }
    }

    fun deleteFlow(flowId: Int) {
        runMutation("No se pudo eliminar flow", "Flow eliminado") {
            repository.deleteRemarketingFlow(flowId)
        }
    }

    fun toggleFlowSelection(flowId: Int) {
        _uiState.update { state ->
            val next = state.selectedFlowIds.toMutableSet()
            if (!next.add(flowId)) next.remove(flowId)
            state.copy(selectedFlowIds = next)
        }
    }

    fun selectAllFlowsOnPage() {
        _uiState.update { state -> state.copy(selectedFlowIds = state.flows.map { it.id }.toSet()) }
    }

    fun clearFlowSelection() {
        _uiState.update { it.copy(selectedFlowIds = emptySet()) }
    }

    fun bulkDeleteFlows() {
        bulkAction(
            ids = _uiState.value.selectedFlowIds,
            emptyMessage = "Selecciona flows para eliminar",
            successPrefix = "Flows eliminados",
            action = { id -> repository.deleteRemarketingFlow(id) },
            onDone = { _uiState.update { state -> state.copy(selectedFlowIds = emptySet()) } },
        )
    }

    fun bulkSetFlowsActive(active: Boolean) {
        bulkAction(
            ids = _uiState.value.selectedFlowIds,
            emptyMessage = "Selecciona flows para actualizar",
            successPrefix = "Flows actualizados",
            action = { id -> repository.updateRemarketingFlow(flowId = id, isActive = active) },
        )
    }

    fun selectFlow(flowId: Int?) {
        _uiState.update {
            it.copy(
                selectedFlowId = flowId,
                selectedFlowSteps = emptyList(),
                selectedFlowEnrollments = emptyList(),
                stepEditorId = null,
                stepOrder = "1",
                stepStageName = "",
                stepWaitMinutes = "1440",
                stepTemplateId = null,
                error = "",
                success = "",
            )
        }
        if (flowId != null) {
            refreshAll()
        }
    }

    fun dispatchFlow(flowId: Int) {
        runMutation("No se pudo ejecutar dispatch del flow", "Flow despachado") {
            repository.dispatchRemarketingFlow(flowId = flowId, limit = 600, includeHold = false)
        }
    }

    fun beginStepEdit(step: RemarketingStepDto) {
        _uiState.update {
            it.copy(
                stepEditorId = step.id,
                stepOrder = step.stepOrder.toString(),
                stepStageName = step.stageName,
                stepWaitMinutes = step.waitMinutes.toString(),
                stepTemplateId = step.templateId,
                error = "",
                success = "",
            )
        }
    }

    fun clearStepEditor() {
        _uiState.update {
            it.copy(
                stepEditorId = null,
                stepOrder = "1",
                stepStageName = "",
                stepWaitMinutes = "1440",
                stepTemplateId = null,
                error = "",
                success = "",
            )
        }
    }

    fun saveStepEditor() {
        val state = _uiState.value
        val flowId = state.selectedFlowId
        val stepOrder = state.stepOrder.trim().toIntOrNull()
        val waitMinutes = state.stepWaitMinutes.trim().toIntOrNull()
        val stageName = state.stepStageName.trim()

        if (flowId == null) {
            _uiState.update { it.copy(error = "Selecciona un flow antes de guardar un step") }
            return
        }
        if (stepOrder == null || stepOrder <= 0) {
            _uiState.update { it.copy(error = "Orden de step invalido") }
            return
        }
        if (waitMinutes == null || waitMinutes < 0) {
            _uiState.update { it.copy(error = "Wait minutes invalido") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                if (state.stepEditorId == null) {
                    repository.createRemarketingStep(
                        flowId = flowId,
                        stepOrder = stepOrder,
                        stageName = stageName,
                        waitMinutes = waitMinutes,
                        templateId = state.stepTemplateId,
                    )
                } else {
                    repository.updateRemarketingStep(
                        stepId = state.stepEditorId,
                        stepOrder = stepOrder,
                        stageName = stageName,
                        waitMinutes = waitMinutes,
                        templateId = state.stepTemplateId,
                    )
                }
            }.onSuccess {
                _uiState.update {
                    it.copy(
                        processing = false,
                        success = if (state.stepEditorId == null) "Step creado" else "Step actualizado",
                    )
                }
                clearStepEditor()
                refreshAll()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: "No se pudo guardar step") }
            }
        }
    }

    fun deleteStep(stepId: Int) {
        runMutation("No se pudo eliminar step", "Step eliminado") {
            repository.deleteRemarketingStep(stepId)
        }
    }

    fun dispatchStep(stepId: Int) {
        runMutation("No se pudo ejecutar dispatch del step", "Step despachado") {
            repository.dispatchRemarketingStep(stepId = stepId, limit = 600, includeHold = false)
        }
    }

    private fun runMutation(
        errorMessage: String,
        successMessage: String,
        action: suspend () -> Unit,
    ) {
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            runCatching {
                action()
            }.onSuccess {
                _uiState.update { it.copy(processing = false, success = successMessage) }
                refreshAll()
            }.onFailure { e ->
                _uiState.update { it.copy(processing = false, error = e.message ?: errorMessage) }
            }
        }
    }

    private fun bulkAction(
        ids: Set<Int>,
        emptyMessage: String,
        successPrefix: String,
        action: suspend (Int) -> Unit,
        onDone: () -> Unit = {},
    ) {
        if (ids.isEmpty()) {
            _uiState.update { it.copy(error = emptyMessage, success = "") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, error = "", success = "") }
            var okCount = 0
            val errors = mutableListOf<String>()
            ids.forEach { id ->
                runCatching { action(id) }
                    .onSuccess { okCount += 1 }
                    .onFailure { e ->
                        if (errors.size < 3) {
                            errors += "id $id: ${e.message ?: "error"}"
                        }
                    }
            }

            val failed = ids.size - okCount
            val successMsg = if (okCount > 0) "$successPrefix: $okCount" else ""
            val errorMsg = if (failed > 0) {
                val detail = if (errors.isNotEmpty()) " (${errors.joinToString(" | ")})" else ""
                "Fallaron $failed operaciones$detail"
            } else {
                ""
            }

            _uiState.update {
                it.copy(
                    processing = false,
                    success = successMsg,
                    error = errorMsg,
                )
            }
            onDone()
            refreshAll()
        }
    }
}
