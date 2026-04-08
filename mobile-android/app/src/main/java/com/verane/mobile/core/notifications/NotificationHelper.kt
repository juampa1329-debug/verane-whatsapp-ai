package com.verane.mobile.core.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.verane.mobile.MainActivity
import com.verane.mobile.R

object NotificationHelper {
    const val CHANNEL_MESSAGES = "verane_messages"
    const val CHANNEL_SYSTEM = "verane_system"

    fun ensureChannels(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java) ?: return

        val messageChannel = NotificationChannel(
            CHANNEL_MESSAGES,
            "Mensajes",
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = "Mensajes nuevos en conversaciones"
        }
        val systemChannel = NotificationChannel(
            CHANNEL_SYSTEM,
            "Sistema",
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply {
            description = "Eventos de sincronizacion y estado"
        }

        manager.createNotificationChannels(listOf(messageChannel, systemChannel))
    }

    fun notifyIncomingMessage(
        context: Context,
        phone: String,
        preview: String,
    ) {
        ensureChannels(context)
        val text = if (preview.isBlank()) "Tienes un mensaje nuevo" else preview
        val notification = NotificationCompat.Builder(context, CHANNEL_MESSAGES)
            .setSmallIcon(android.R.drawable.ic_dialog_email)
            .setContentTitle("Nuevo mensaje: $phone")
            .setContentText(text)
            .setAutoCancel(true)
            .setContentIntent(mainIntent(context))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()

        NotificationManagerCompat.from(context).notify(phone.hashCode(), notification)
    }

    fun notifySyncUpdate(
        context: Context,
        title: String,
        body: String,
    ) {
        ensureChannels(context)
        val notification = NotificationCompat.Builder(context, CHANNEL_SYSTEM)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setContentIntent(mainIntent(context))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()

        NotificationManagerCompat.from(context).notify(1001, notification)
    }

    fun notifyPush(
        context: Context,
        title: String,
        body: String,
    ) {
        ensureChannels(context)
        val notification = NotificationCompat.Builder(context, CHANNEL_MESSAGES)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title.ifBlank { context.getString(R.string.app_name) })
            .setContentText(body.ifBlank { "Tienes una notificacion nueva" })
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(mainIntent(context))
            .build()
        NotificationManagerCompat.from(context).notify((System.currentTimeMillis() % Int.MAX_VALUE).toInt(), notification)
    }

    private fun mainIntent(context: Context): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        return PendingIntent.getActivity(
            context,
            100,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }
}
