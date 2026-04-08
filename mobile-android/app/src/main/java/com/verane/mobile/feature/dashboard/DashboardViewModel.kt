package com.verane.mobile.feature.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.verane.mobile.core.network.CampaignEngineStatusResponse
import com.verane.mobile.core.network.DashboardCampaignMetrics
import com.verane.mobile.core.network.DashboardFunnelStep
import com.verane.mobile.core.network.DashboardOverviewKpis
import com.verane.mobile.core.network.RemarketingEngineStatusResponse
import com.verane.mobile.core.repository.VeraneRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DashboardUiState(
    val loading: Boolean = true,
    val range: String = "7d",
    val error: String = "",
    val success: String = "",
    val kpis: DashboardOverviewKpis = DashboardOverviewKpis(),
    val funnel: List<DashboardFunnelStep> = emptyList(),
    val campaignMetrics: DashboardCampaignMetrics = DashboardCampaignMetrics(),
    val remarketingFlowsTotal: Int = 0,
    val remarketingFlowsActive: Int = 0,
    val remarketingStepsTotal: Int = 0,
    val campaignEngine: CampaignEngineStatusResponse = CampaignEngineStatusResponse(),
    val remarketingEngine: RemarketingEngineStatusResponse = RemarketingEngineStatusResponse(),
)

class DashboardViewModel(
    private val repository: VeraneRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun setRange(value: String) {
        _uiState.update { it.copy(range = value) }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = "", success = "") }
            runCatching {
                val currentRange = _uiState.value.range
                val overview = repository.dashboardOverview(range = currentRange)
                val funnel = repository.dashboardFunnel()
                val campaigns = repository.dashboardCampaigns(range = if (currentRange == "7d") "30d" else currentRange)
                val remarketing = repository.dashboardRemarketing()
                val campaignEngine = repository.campaignEngineStatus()
                val remarketingEngine = repository.remarketingEngineStatus()

                _uiState.update {
                    it.copy(
                        loading = false,
                        kpis = overview.kpis,
                        funnel = funnel.steps,
                        campaignMetrics = campaigns.metrics,
                        remarketingFlowsTotal = remarketing.flowsTotal,
                        remarketingFlowsActive = remarketing.activeFlows,
                        remarketingStepsTotal = remarketing.stepsTotal,
                        campaignEngine = campaignEngine,
                        remarketingEngine = remarketingEngine,
                        error = "",
                    )
                }
            }.onFailure { e ->
                _uiState.update {
                    it.copy(
                        loading = false,
                        error = e.message ?: "No se pudo cargar dashboard",
                    )
                }
            }
        }
    }

    fun tickCampaignEngine() {
        viewModelScope.launch {
            _uiState.update { it.copy(success = "", error = "") }
            runCatching {
                repository.campaignEngineTick(batchSize = 20, sendDelayMs = 0)
            }.onSuccess {
                _uiState.update { it.copy(success = "Campaign engine ejecutado") }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(error = e.message ?: "No se pudo ejecutar campaign engine") }
            }
        }
    }

    fun tickRemarketingEngine() {
        viewModelScope.launch {
            _uiState.update { it.copy(success = "", error = "") }
            runCatching {
                repository.remarketingEngineTick(limit = 600, flowId = 0, channel = "all")
            }.onSuccess {
                _uiState.update { it.copy(success = "Remarketing engine ejecutado") }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(error = e.message ?: "No se pudo ejecutar remarketing engine") }
            }
        }
    }
}
