package com.verane.mobile.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = VeranePrimary,
    onPrimary = Color.White,
    secondary = VeraneAccent,
    onSecondary = Color(0xFF072E1A),
    tertiary = VeraneTeal,
    onTertiary = Color.White,
    background = VeraneBgBottom,
    onBackground = Color(0xFF102521),
    surface = VeraneCard,
    onSurface = Color(0xFF132A26),
    surfaceContainer = Color(0xFFF2F8F5),
    surfaceContainerHigh = Color(0xFFEAF3EF),
    outline = VeraneOutline,
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF18C49A),
    onPrimary = Color(0xFF07251E),
    secondary = Color(0xFF57E389),
    onSecondary = Color(0xFF0C2A1A),
    tertiary = Color(0xFF4CD4BF),
    onTertiary = Color(0xFF08241F),
    background = Color(0xFF071311),
    onBackground = Color(0xFFD5E6DF),
    surface = Color(0xFF0D1B19),
    onSurface = Color(0xFFD5E6DF),
    surfaceContainer = Color(0xFF0F2320),
    surfaceContainerHigh = Color(0xFF16312D),
    outline = Color(0xFF45635A),
)

@Composable
fun VeraneTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colors = if (darkTheme) DarkColors else LightColors
    MaterialTheme(
        colorScheme = colors,
        typography = Typography,
        content = content,
    )
}
