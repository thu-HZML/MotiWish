package com.example.motiwish.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.navigation.NavController
import com.example.motiwish.viewmodel.TaskViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.ceil

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FocusTimerScreen(
    navController: NavController,
    taskId: Int,
    initialFocusedMinutes: Int,
    estimatedMinutes: Int,
    viewModel: TaskViewModel
) {
    // 全屏隐藏系统栏
    val view = LocalView.current
    DisposableEffect(Unit) {
        val insetsController = ViewCompat.getWindowInsetsController(view)
        insetsController?.let { controller ->
            // 隐藏状态栏和导航栏
            controller.hide(WindowInsetsCompat.Type.statusBars() or WindowInsetsCompat.Type.navigationBars())
            // 设置为滑动边缘时临时显示
            controller.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
        onDispose {
            // 恢复显示系统栏
            insetsController?.show(WindowInsetsCompat.Type.statusBars() or WindowInsetsCompat.Type.navigationBars())
        }
    }

    // 计时逻辑
    val initialSeconds = initialFocusedMinutes * 60
    var elapsedSeconds by remember { mutableStateOf(initialSeconds) }
    var isRunning by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(isRunning) {
        while (isRunning) {
            delay(1000L)
            elapsedSeconds++
        }
    }

    fun formatTime(seconds: Int): String {
        val mins = seconds / 60
        val secs = seconds % 60
        return String.format("%02d:%02d", mins, secs)
    }

    // 不使用 Scaffold 的 bottomBar，且让它占满全屏
    Scaffold(
        topBar = { TopAppBar(title = { Text("专注探索") }) },
        modifier = Modifier.fillMaxSize()
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("预估专注时长: $estimatedMinutes 分钟", fontSize = 18.sp)
            Text(
                text = formatTime(elapsedSeconds),
                fontSize = 48.sp,
                fontFamily = monospaceFontFamily()
            )
            Row {
                Button(
                    onClick = { isRunning = !isRunning },
                    enabled = elapsedSeconds / 60 < estimatedMinutes
                ) {
                    Text(if (isRunning) "暂停" else "开始")
                }
                Spacer(modifier = Modifier.width(8.dp))
                Button(
                    onClick = {
                        val totalMinutes = ceil(elapsedSeconds / 60.0).toInt()
                        viewModel.updateExplorationProgress(taskId, totalMinutes)
                        navController.popBackStack()
                    }
                ) {
                    Text("完成")
                }
            }
        }
    }
}

@Composable
fun monospaceFontFamily() = androidx.compose.ui.text.font.FontFamily.Monospace