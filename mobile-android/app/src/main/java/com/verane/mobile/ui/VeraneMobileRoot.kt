package com.verane.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Web
import androidx.compose.material3.Icon
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.verane.mobile.core.AppGraph
import com.verane.mobile.core.data.AppConfig
import com.verane.mobile.core.security.canAccessAi
import com.verane.mobile.core.security.canAccessSecurity
import com.verane.mobile.core.security.normalizeRole
import com.verane.mobile.core.util.SingleViewModelFactory
import com.verane.mobile.core.work.ConversationSyncWorker
import com.verane.mobile.feature.ai.AiAdminScreen
import com.verane.mobile.feature.ai.AiAdminViewModel
import com.verane.mobile.feature.customers.CustomersScreen
import com.verane.mobile.feature.customers.CustomersViewModel
import com.verane.mobile.feature.dashboard.DashboardScreen
import com.verane.mobile.feature.dashboard.DashboardViewModel
import com.verane.mobile.feature.inbox.InboxScreen
import com.verane.mobile.feature.inbox.InboxViewModel
import com.verane.mobile.feature.marketing.MarketingScreen
import com.verane.mobile.feature.marketing.MarketingViewModel
import com.verane.mobile.feature.settings.SettingsScreen
import com.verane.mobile.feature.settings.SettingsViewModel
import com.verane.mobile.feature.setup.SetupScreen
import com.verane.mobile.feature.setup.SetupViewModel
import com.verane.mobile.feature.security.SecurityScreen
import com.verane.mobile.feature.security.SecurityViewModel

private enum class HomeTab(val title: String) {
    Dashboard("Dashboard"),
    Inbox("Inbox"),
    Customers("Clientes"),
    Marketing("Marketing"),
    Settings("Ajustes"),
    Security("Seguridad"),
    Ai("AI"),
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
fun VeraneMobileRoot(graph: AppGraph) {
    val context = LocalContext.current
    val config by graph.preferences.configFlow.collectAsStateWithLifecycle(initialValue = AppConfig.Default)

    val setupViewModel: SetupViewModel = viewModel(
        factory = SingleViewModelFactory { SetupViewModel(graph.repository) },
    )

    if (config.apiBase.isBlank()) {
        SetupScreen(
            viewModel = setupViewModel,
            onSaved = { ConversationSyncWorker.schedule(context) },
        )
        return
    }

    LaunchedEffect(config.apiBase, config.backgroundSyncEnabled) {
        if (config.backgroundSyncEnabled && config.apiBase.isNotBlank()) {
            ConversationSyncWorker.schedule(context)
        } else {
            ConversationSyncWorker.cancel(context)
        }
    }

    val inboxViewModel: InboxViewModel = viewModel(
        key = "inbox_vm",
        factory = SingleViewModelFactory {
            InboxViewModel(
                repository = graph.repository,
                appContext = context.applicationContext,
            )
        },
    )
    val customersViewModel: CustomersViewModel = viewModel(
        key = "customers_vm",
        factory = SingleViewModelFactory { CustomersViewModel(graph.repository) },
    )
    val dashboardViewModel: DashboardViewModel = viewModel(
        key = "dashboard_vm",
        factory = SingleViewModelFactory { DashboardViewModel(graph.repository) },
    )
    val marketingViewModel: MarketingViewModel = viewModel(
        key = "marketing_vm",
        factory = SingleViewModelFactory { MarketingViewModel(graph.repository) },
    )
    val settingsViewModel: SettingsViewModel = viewModel(
        key = "settings_vm",
        factory = SingleViewModelFactory { SettingsViewModel(graph.repository) },
    )
    val securityViewModel: SecurityViewModel = viewModel(
        key = "security_vm",
        factory = SingleViewModelFactory { SecurityViewModel(graph.repository) },
    )
    val aiAdminViewModel: AiAdminViewModel = viewModel(
        key = "ai_admin_vm",
        factory = SingleViewModelFactory { AiAdminViewModel(graph.repository) },
    )

    var tab by remember { mutableStateOf(HomeTab.Dashboard) }
    val role = normalizeRole(config.securityRole)
    val canSecurity = canAccessSecurity(role)
    val canAi = canAccessAi(role)

    LaunchedEffect(canSecurity, canAi, tab) {
        if (tab == HomeTab.Security && !canSecurity) tab = HomeTab.Dashboard
        if (tab == HomeTab.Ai && !canAi) tab = HomeTab.Dashboard
    }

    Scaffold(
        containerColor = Color.Transparent,
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Verane Mobile - ${tab.title}",
                        style = MaterialTheme.typography.titleMedium,
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary,
                ),
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
                tonalElevation = 8.dp,
            ) {
                NavigationBarItem(
                    selected = tab == HomeTab.Dashboard,
                    onClick = { tab = HomeTab.Dashboard },
                    icon = { Icon(Icons.Default.Home, contentDescription = null) },
                    label = { Text("Dashboard") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = MaterialTheme.colorScheme.primary,
                        selectedTextColor = MaterialTheme.colorScheme.primary,
                        indicatorColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                    ),
                )
                NavigationBarItem(
                    selected = tab == HomeTab.Inbox,
                    onClick = { tab = HomeTab.Inbox },
                    icon = { Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = null) },
                    label = { Text("Inbox") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = MaterialTheme.colorScheme.primary,
                        selectedTextColor = MaterialTheme.colorScheme.primary,
                        indicatorColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                    ),
                )
                NavigationBarItem(
                    selected = tab == HomeTab.Customers,
                    onClick = { tab = HomeTab.Customers },
                    icon = { Icon(Icons.Default.Groups, contentDescription = null) },
                    label = { Text("Clientes") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = MaterialTheme.colorScheme.primary,
                        selectedTextColor = MaterialTheme.colorScheme.primary,
                        indicatorColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                    ),
                )
                NavigationBarItem(
                    selected = tab == HomeTab.Marketing,
                    onClick = { tab = HomeTab.Marketing },
                    icon = { Icon(Icons.Default.Web, contentDescription = null) },
                    label = { Text("Marketing") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = MaterialTheme.colorScheme.primary,
                        selectedTextColor = MaterialTheme.colorScheme.primary,
                        indicatorColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                    ),
                )
                NavigationBarItem(
                    selected = tab == HomeTab.Settings,
                    onClick = { tab = HomeTab.Settings },
                    icon = { Icon(Icons.Default.Settings, contentDescription = null) },
                    label = { Text("Ajustes") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = MaterialTheme.colorScheme.primary,
                        selectedTextColor = MaterialTheme.colorScheme.primary,
                        indicatorColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                    ),
                )
                if (canSecurity) {
                    NavigationBarItem(
                        selected = tab == HomeTab.Security,
                        onClick = { tab = HomeTab.Security },
                        icon = { Icon(Icons.Default.Security, contentDescription = null) },
                        label = { Text("Seguridad") },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                        ),
                    )
                }
                if (canAi) {
                    NavigationBarItem(
                        selected = tab == HomeTab.Ai,
                        onClick = { tab = HomeTab.Ai },
                        icon = { Icon(Icons.Default.Psychology, contentDescription = null) },
                        label = { Text("AI") },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                        ),
                    )
                }
            }
        },
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            MaterialTheme.colorScheme.background,
                            MaterialTheme.colorScheme.surfaceContainer,
                        ),
                    ),
                ),
        ) {
            when (tab) {
                HomeTab.Dashboard -> DashboardScreen(
                    viewModel = dashboardViewModel,
                    modifier = Modifier.padding(innerPadding),
                )

                HomeTab.Inbox -> InboxScreen(
                    viewModel = inboxViewModel,
                    modifier = Modifier.padding(innerPadding),
                    onOpenCustomerCrm = { phone ->
                        customersViewModel.selectCustomer(phone)
                        tab = HomeTab.Customers
                    },
                )

                HomeTab.Customers -> CustomersScreen(
                    viewModel = customersViewModel,
                    modifier = Modifier.padding(innerPadding),
                )

                HomeTab.Marketing -> MarketingScreen(
                    viewModel = marketingViewModel,
                    modifier = Modifier.padding(innerPadding),
                )

                HomeTab.Settings -> SettingsScreen(
                    viewModel = settingsViewModel,
                    modifier = Modifier.padding(innerPadding),
                )

                HomeTab.Security -> SecurityScreen(
                    viewModel = securityViewModel,
                    modifier = Modifier.padding(innerPadding),
                )

                HomeTab.Ai -> AiAdminScreen(
                    viewModel = aiAdminViewModel,
                    modifier = Modifier.padding(innerPadding),
                )
            }
        }
    }
}
