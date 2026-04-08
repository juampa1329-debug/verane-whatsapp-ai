package com.verane.mobile

import android.app.Application
import android.provider.Settings
import com.google.firebase.FirebaseApp
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.google.firebase.messaging.FirebaseMessaging
import com.verane.mobile.core.AppGraph
import com.verane.mobile.core.data.AppConfig
import com.verane.mobile.core.notifications.NotificationHelper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class VeraneApp : Application() {
    lateinit var appGraph: AppGraph
        private set
    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var firebaseReady: Boolean = false

    override fun onCreate() {
        super.onCreate()
        appGraph = AppGraph(this)
        NotificationHelper.ensureChannels(this)

        firebaseReady = ensureFirebaseReady()
        if (!firebaseReady) {
            return
        }

        setupCrashlytics()
        observeConfigForMonitoringAndPush()

        runCatching {
            FirebaseMessaging.getInstance().token
                .addOnSuccessListener { token ->
                    appScope.launch { saveAndRegisterToken(token) }
                }
                .addOnFailureListener { e ->
                    recordNonFatal(e)
                }
        }.onFailure { e ->
            recordNonFatal(e)
        }
    }

    private fun ensureFirebaseReady(): Boolean {
        return runCatching {
            FirebaseApp.initializeApp(this)
            FirebaseApp.getApps(this).isNotEmpty()
        }.getOrDefault(false)
    }

    private fun withCrashlytics(block: (FirebaseCrashlytics) -> Unit) {
        if (!firebaseReady) return
        runCatching { FirebaseCrashlytics.getInstance() }
            .onSuccess(block)
    }

    private fun recordNonFatal(error: Throwable) {
        withCrashlytics { it.recordException(error) }
    }

    private fun setupCrashlytics() {
        withCrashlytics { crashlytics ->
            crashlytics.setCrashlyticsCollectionEnabled(!BuildConfig.DEBUG)
            crashlytics.setCustomKey("app_version", BuildConfig.VERSION_NAME)
            crashlytics.setCustomKey("build_type", BuildConfig.BUILD_TYPE)
        }
    }

    private fun observeConfigForMonitoringAndPush() {
        appScope.launch {
            appGraph.repository.configFlow.collectLatest { cfg ->
                withCrashlytics { crashlytics ->
                    crashlytics.setCustomKey("security_role", cfg.securityRole)
                    crashlytics.setCustomKey("api_base", cfg.apiBase)
                    if (cfg.actorName.isNotBlank()) {
                        crashlytics.setUserId(cfg.actorName)
                    }
                }

                if (cfg.firebaseToken.isNotBlank()) {
                    registerTokenInBackend(cfg.firebaseToken, cfg)
                }
            }
        }
    }

    private suspend fun saveAndRegisterToken(token: String) {
        val clean = token.trim()
        if (clean.isBlank()) return
        runCatching {
            appGraph.repository.saveFirebaseToken(clean)
        }.onFailure { e ->
            recordNonFatal(e)
        }

        val cfg = runCatching { appGraph.repository.currentConfig() }.getOrDefault(AppConfig.Default)
        registerTokenInBackend(clean, cfg)
    }

    private suspend fun registerTokenInBackend(token: String, cfg: AppConfig) {
        if (cfg.apiBase.isBlank()) return
        runCatching {
            appGraph.repository.registerMobilePushToken(
                token = token,
                platform = "android",
                appVersion = BuildConfig.VERSION_NAME,
                deviceId = androidDeviceId(),
                role = cfg.securityRole,
                actor = cfg.actorName,
                notificationsEnabled = true,
            )
        }.onFailure { e ->
            recordNonFatal(e)
        }
    }

    private fun androidDeviceId(): String {
        return runCatching {
            Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID).orEmpty()
        }.getOrDefault("")
    }
}
