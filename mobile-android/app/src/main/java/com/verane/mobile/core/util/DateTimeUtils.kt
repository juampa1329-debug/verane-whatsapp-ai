package com.verane.mobile.core.util

import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import java.util.Locale

object DateTimeUtils {
    private val output = DateTimeFormatter.ofPattern("dd MMM HH:mm", Locale.getDefault())

    fun formatForUi(raw: String?): String {
        val epoch = toEpochMillis(raw) ?: return ""
        return Instant.ofEpochMilli(epoch).atZone(ZoneId.systemDefault()).format(output)
    }

    fun toEpochMillis(raw: String?): Long? {
        val value = raw?.trim().orEmpty()
        if (value.isEmpty()) return null

        return try {
            Instant.parse(value).toEpochMilli()
        } catch (_: DateTimeParseException) {
            try {
                val ldt = LocalDateTime.parse(value)
                ldt.toInstant(ZoneOffset.UTC).toEpochMilli()
            } catch (_: DateTimeParseException) {
                null
            }
        }
    }
}
