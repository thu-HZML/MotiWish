package com.example.motiwish.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.example.motiwish.R
import kotlinx.coroutines.delay

@Composable
fun SplashScreen(navController: NavController) {
    // 延时 2 秒后跳转到主页
    LaunchedEffect(Unit) {
        delay(2000L)
        navController.navigate("tasks") {
            // 跳转后将过渡页从栈中销毁，防止按返回键退回
            popUpTo("splash") { inclusive = true }
        }
    }

    // 绘制纯色背景和中间的图标
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.primary), // 背景颜色
        contentAlignment = Alignment.Center
    ) {
        Image(
            painter = painterResource(id = R.drawable.ic_launcher_foreground),
            contentDescription = "App Logo",
            modifier = Modifier.size(150.dp)
        )
    }
}