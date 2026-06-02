package com.example.motiwish.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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
    // 将初始分钟转换为秒
    val initialSeconds = initialFocusedMinutes * 60
    var elapsedSeconds by remember { mutableStateOf(initialSeconds) }
    var isRunning by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    // 计时器：每秒增加 1 秒
    LaunchedEffect(isRunning) {
        while (isRunning) {
            delay(1000L)
            elapsedSeconds++
        }
    }

    // 格式化 mm:ss
    fun formatTime(seconds: Int): String {
        val mins = seconds / 60
        val secs = seconds % 60
        return String.format("%02d:%02d", mins, secs)
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("专注探索") }) }
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
                        // 停止计时，计算总分钟数（向上取整）
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