package com.example.motiwish.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColorScheme = lightColorScheme(
    primary = Color(0xFF2196F3),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFBBDEFB),
    secondary = Color(0xFF03A9F4),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFB3E5FC),
    background = Color(0xFFF5F9FF),
    surface = Color.White,
    onSurface = Color(0xFF1A1A1A),
    error = Color(0xFFB00020)
)

@Composable
fun MySelfManagementAppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        typography = Typography(),
        content = content
    )
}