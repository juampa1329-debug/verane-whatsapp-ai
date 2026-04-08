package com.verane.mobile.core.security

object SecurityRoles {
    const val ADMIN = "admin"
    const val SUPERVISOR = "supervisor"
    const val AGENT = "agente"

    val all = listOf(ADMIN, SUPERVISOR, AGENT)
}

fun normalizeRole(raw: String): String {
    return when (raw.trim().lowercase()) {
        SecurityRoles.ADMIN -> SecurityRoles.ADMIN
        SecurityRoles.SUPERVISOR -> SecurityRoles.SUPERVISOR
        SecurityRoles.AGENT -> SecurityRoles.AGENT
        else -> SecurityRoles.AGENT
    }
}

fun canAccessSecurity(role: String): Boolean {
    val r = normalizeRole(role)
    return r == SecurityRoles.ADMIN || r == SecurityRoles.SUPERVISOR
}

fun canManageSecurity(role: String): Boolean {
    return normalizeRole(role) == SecurityRoles.ADMIN
}

fun canAccessAi(role: String): Boolean {
    val r = normalizeRole(role)
    return r == SecurityRoles.ADMIN || r == SecurityRoles.SUPERVISOR
}
