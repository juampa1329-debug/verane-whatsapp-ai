package com.verane.mobile.core.data

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "verane_mobile_prefs")

data class AppConfig(
    val apiBase: String,
    val securityToken: String,
    val webAppBase: String,
    val backgroundSyncEnabled: Boolean,
    val firebaseToken: String,
    val securityRole: String,
    val actorName: String,
) {
    companion object {
        val Default = AppConfig(
            apiBase = "https://backend.perfumesverane.com",
            securityToken = "",
            webAppBase = "https://app.perfumesverane.com",
            backgroundSyncEnabled = true,
            firebaseToken = "",
            securityRole = "admin",
            actorName = "",
        )
    }
}

class AppPreferences(private val context: Context) {
    private object Keys {
        val apiBase = stringPreferencesKey("api_base")
        val securityToken = stringPreferencesKey("security_token")
        val webAppBase = stringPreferencesKey("web_app_base")
        val backgroundSyncEnabled = booleanPreferencesKey("background_sync_enabled")
        val firebaseToken = stringPreferencesKey("firebase_token")
        val securityRole = stringPreferencesKey("security_role")
        val actorName = stringPreferencesKey("actor_name")
        val lastUnreadTotal = intPreferencesKey("last_unread_total")
        val lastTopConversationTs = stringPreferencesKey("last_top_conversation_ts")
    }

    val configFlow: Flow<AppConfig> = context.dataStore.data.map { prefs ->
        AppConfig(
            apiBase = normalizeBase(prefs[Keys.apiBase] ?: AppConfig.Default.apiBase),
            securityToken = (prefs[Keys.securityToken] ?: AppConfig.Default.securityToken).trim(),
            webAppBase = normalizeBase(prefs[Keys.webAppBase] ?: AppConfig.Default.webAppBase),
            backgroundSyncEnabled = prefs[Keys.backgroundSyncEnabled] ?: AppConfig.Default.backgroundSyncEnabled,
            firebaseToken = prefs[Keys.firebaseToken] ?: AppConfig.Default.firebaseToken,
            securityRole = normalizeRole(prefs[Keys.securityRole] ?: AppConfig.Default.securityRole),
            actorName = (prefs[Keys.actorName] ?: AppConfig.Default.actorName).trim().take(120),
        )
    }

    val syncStateFlow: Flow<Pair<Int, String>> = context.dataStore.data.map { prefs ->
        Pair(
            prefs[Keys.lastUnreadTotal] ?: 0,
            prefs[Keys.lastTopConversationTs] ?: "",
        )
    }

    suspend fun saveConfig(
        apiBase: String,
        securityToken: String,
        webAppBase: String,
        backgroundSyncEnabled: Boolean,
        securityRole: String,
        actorName: String,
    ) {
        context.dataStore.edit { prefs ->
            prefs[Keys.apiBase] = normalizeBase(apiBase)
            prefs[Keys.securityToken] = securityToken.trim()
            prefs[Keys.webAppBase] = normalizeBase(webAppBase)
            prefs[Keys.backgroundSyncEnabled] = backgroundSyncEnabled
            prefs[Keys.securityRole] = normalizeRole(securityRole)
            prefs[Keys.actorName] = actorName.trim().take(120)
        }
    }

    suspend fun saveFirebaseToken(token: String) {
        context.dataStore.edit { prefs ->
            prefs[Keys.firebaseToken] = token.trim()
        }
    }

    suspend fun saveSyncState(unreadTotal: Int, topConversationTs: String) {
        context.dataStore.edit { prefs ->
            prefs[Keys.lastUnreadTotal] = unreadTotal
            prefs[Keys.lastTopConversationTs] = topConversationTs
        }
    }

    private fun normalizeBase(raw: String): String {
        val trimmed = raw.trim().removeSuffix("/")
        if (trimmed.isEmpty()) return ""
        if (trimmed.startsWith("http://", ignoreCase = true) ||
            trimmed.startsWith("https://", ignoreCase = true)
        ) {
            return trimmed
        }
        return "https://$trimmed"
    }

    private fun normalizeRole(raw: String): String {
        return when (raw.trim().lowercase()) {
            "admin", "supervisor", "agente" -> raw.trim().lowercase()
            else -> "agente"
        }
    }
}
