package com.verane.mobile.push

import android.provider.Settings
import com.google.firebase.FirebaseApp
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.verane.mobile.BuildConfig
import com.verane.mobile.core.data.AppConfig
import com.verane.mobile.core.data.AppPreferences
import com.verane.mobile.core.notifications.NotificationHelper
import com.verane.mobile.core.repository.VeraneRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class VeraneFirebaseMessagingService : FirebaseMessagingService() {
    private fun withCrashlytics(block: (FirebaseCrashlytics) -> Unit) {
        runCatching {
            if (FirebaseApp.getApps(this).isEmpty()) return
            FirebaseCrashlytics.getInstance()
        }.onSuccess(block)
    }

    private fun recordNonFatal(error: Throwable) {
        withCrashlytics { it.recordException(error) }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        val title = message.notification?.title
            ?: message.data["title"]
            ?: "Verane Mobile"
        val body = message.notification?.body
            ?: message.data["body"]
            ?: "Nueva notificacion"
        val eventType = (message.data["event_type"] ?: "").trim().lowercase()
        val phone = (message.data["phone"] ?: "").trim()

        withCrashlytics {
            it.log(
                "fcm_message event=$eventType phone=$phone data_keys=${message.data.keys.joinToString(",")}",
            )
        }

        when (eventType) {
            "message_in" -> NotificationHelper.notifyIncomingMessage(
                context = this,
                phone = phone.ifBlank { "contacto" },
                preview = body,
            )

            "takeover_changed", "security_alert" -> NotificationHelper.notifySyncUpdate(
                context = this,
                title = title,
                body = body,
            )

            else -> NotificationHelper.notifyPush(this, title = title, body = body)
        }
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        CoroutineScope(Dispatchers.IO).launch {
            val prefs = AppPreferences(applicationContext)
            val repository = VeraneRepository(prefs)
            val clean = token.trim()
            if (clean.isBlank()) return@launch

            runCatching { prefs.saveFirebaseToken(clean) }
                .onFailure { recordNonFatal(it) }

            val cfg = runCatching { repository.currentConfig() }.getOrDefault(AppConfig.Default)
            if (cfg.apiBase.isBlank()) return@launch

            runCatching {
                repository.registerMobilePushToken(
                    token = clean,
                    platform = "android",
                    appVersion = BuildConfig.VERSION_NAME,
                    deviceId = Settings.Secure.getString(
                        applicationContext.contentResolver,
                        Settings.Secure.ANDROID_ID,
                    ).orEmpty(),
                    role = cfg.securityRole,
                    actor = cfg.actorName,
                    notificationsEnabled = true,
                )
            }.onFailure { recordNonFatal(it) }
        }
    }
}
