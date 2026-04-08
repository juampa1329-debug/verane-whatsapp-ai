package com.verane.mobile.core.work

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.verane.mobile.core.data.AppConfig
import com.verane.mobile.core.data.AppPreferences
import com.verane.mobile.core.notifications.NotificationHelper
import com.verane.mobile.core.repository.VeraneRepository
import com.verane.mobile.core.util.DateTimeUtils
import kotlinx.coroutines.flow.first
import java.util.concurrent.TimeUnit

class ConversationSyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    private val prefs = AppPreferences(appContext)
    private val repository = VeraneRepository(prefs)

    override suspend fun doWork(): Result {
        return try {
            val cfg = prefs.configFlow.first()
            if (!isSyncEnabled(cfg)) return Result.success()

            val conversations = repository.listConversations(search = "", channel = "all")
            val unreadTotal = conversations.sumOf { it.unreadCount.coerceAtLeast(0) }
            val topTs = conversations.firstOrNull()?.updatedAt.orEmpty()
            val (prevUnread, prevTopTs) = repository.loadSyncState()

            if (unreadTotal > prevUnread) {
                NotificationHelper.notifySyncUpdate(
                    context = applicationContext,
                    title = "Actividad nueva",
                    body = "Tienes $unreadTotal mensajes sin leer",
                )
            } else if (topTs.isNotBlank() && topTs != prevTopTs && prevTopTs.isNotBlank()) {
                val humanTs = DateTimeUtils.formatForUi(topTs)
                NotificationHelper.notifySyncUpdate(
                    context = applicationContext,
                    title = "Conversaciones actualizadas",
                    body = "Ultima actividad $humanTs",
                )
            }

            repository.saveSyncState(unreadTotal = unreadTotal, topConversationTs = topTs)
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    private fun isSyncEnabled(cfg: AppConfig): Boolean {
        return cfg.backgroundSyncEnabled && cfg.apiBase.isNotBlank()
    }

    companion object {
        private const val WORK_NAME = "conversation_sync_periodic"

        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<ConversationSyncWorker>(15, TimeUnit.MINUTES)
                .setInitialDelay(15, TimeUnit.MINUTES)
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request,
            )
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
