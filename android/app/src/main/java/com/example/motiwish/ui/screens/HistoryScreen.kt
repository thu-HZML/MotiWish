package com.example.motiwish.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.motiwish.viewmodel.HistoryViewModel
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(viewModel: HistoryViewModel) {
    // 当前显示的年份月份
    var currentYearMonth by remember { mutableStateOf(YearMonth.now()) }
    // 选中的日期（用于显示详情对话框）
    var selectedDate by remember { mutableStateOf<LocalDate?>(null) }

    // 从 ViewModel 获取当月所有任务（按日期分组）
    val tasksByDate by viewModel.getTasksByMonth(currentYearMonth)
        .collectAsStateWithLifecycle(initialValue = emptyMap())

    // 获取用于日历网格的日期列表（包含前后月占位）
    val calendarDates = remember(currentYearMonth) {
        buildCalendarDates(currentYearMonth)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("任务日历") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary
                ),
                actions = {
                    // 月份切换按钮
                    IconButton(onClick = { currentYearMonth = currentYearMonth.minusMonths(1) }) {
                        Icon(Icons.Default.ChevronLeft, contentDescription = "上个月")
                    }
                    Text(
                        text = currentYearMonth.format(DateTimeFormatter.ofPattern("yyyy年 MMM")),
                        modifier = Modifier.padding(horizontal = 8.dp),
                        fontSize = 18.sp
                    )
                    IconButton(onClick = { currentYearMonth = currentYearMonth.plusMonths(1) }) {
                        Icon(Icons.Default.ChevronRight, contentDescription = "下个月")
                    }
                    IconButton(onClick = { currentYearMonth = YearMonth.now() }) {
                        Icon(Icons.Default.Today, contentDescription = "今天")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // 星期标题行
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                val daysOfWeek = listOf("一", "二", "三", "四", "五", "六", "日")
                daysOfWeek.forEach { day ->
                    Text(
                        text = day,
                        modifier = Modifier.weight(1f),
                        textAlign = TextAlign.Center,
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (day == "日") MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface
                    )
                }
            }

            Divider()

            // 日历网格 (使用 LazyVerticalGrid 或 Column+Row)
            // 简单起见，使用 Column 逐行添加
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(8.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                // 将日期列表按周分组（每7天一行）
                val weeks = calendarDates.chunked(7)
                items(weeks) { weekDates ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        weekDates.forEach { date ->
                            val isCurrentMonth = YearMonth.from(date) == currentYearMonth
                            val tasksOnDay = tasksByDate[date] ?: emptyList()
                            CalendarDayCell(
                                date = date,
                                isCurrentMonth = isCurrentMonth,
                                taskCount = tasksOnDay.size,
                                isToday = date == LocalDate.now(),
                                onClick = { selectedDate = date }
                            )
                        }
                        // 补齐空位（最后一行可能不足7个）
                        repeat(7 - weekDates.size) {
                            Spacer(modifier = Modifier.weight(1f))
                        }
                    }
                }
            }
        }
    }

    // 日期详情弹窗
    selectedDate?.let { date ->
        AlertDialog(
            onDismissRequest = { selectedDate = null },
            title = { Text("${date.format(DateTimeFormatter.ofPattern("yyyy-MM-dd EEEE", Locale.getDefault()))}") },
            text = {
                val tasks = tasksByDate[date] ?: emptyList()
                if (tasks.isEmpty()) {
                    Text("当天没有任务记录")
                } else {
                    Column {
                        tasks.forEach { task ->
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 4.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = when (task.status) {
                                        "已完成" -> MaterialTheme.colorScheme.surfaceVariant
                                        "失败" -> MaterialTheme.colorScheme.errorContainer
                                        else -> MaterialTheme.colorScheme.surface
                                    }
                                )
                            ) {
                                Column(modifier = Modifier.padding(8.dp)) {
                                    Text(task.title, style = MaterialTheme.typography.titleSmall)
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text("类型: ${task.type}", style = MaterialTheme.typography.bodySmall)
                                        Text("状态: ${task.status}", style = MaterialTheme.typography.bodySmall)
                                        Text("货币: ${task.reward}", style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { selectedDate = null }) {
                    Text("关闭")
                }
            }
        )
    }
}

@Composable
fun RowScope.CalendarDayCell(
    date: LocalDate,
    isCurrentMonth: Boolean,
    taskCount: Int,
    isToday: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .weight(1f)       // 现在 weight 可用，因为处于 RowScope 中
            .aspectRatio(1f)
            .padding(2.dp)
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = when {
                isToday -> MaterialTheme.colorScheme.primaryContainer
                isCurrentMonth -> MaterialTheme.colorScheme.surface
                else -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
            }
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(4.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = date.dayOfMonth.toString(),
                style = MaterialTheme.typography.bodyMedium,
                color = if (isCurrentMonth) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (taskCount > 0) {
                Spacer(modifier = Modifier.height(2.dp))
                Badge(
                    containerColor = MaterialTheme.colorScheme.secondary,
                    modifier = Modifier.padding(horizontal = 4.dp)
                ) {
                    Text(text = "$taskCount", fontSize = 10.sp)
                }
            }
        }
    }
}

/**
 * 构建指定月份的日历网格日期列表（包含前后月补齐的日期，共42天或35天）
 */
private fun buildCalendarDates(yearMonth: YearMonth): List<LocalDate> {
    val firstDayOfMonth = yearMonth.atDay(1)
    // 获取当月第一天是星期几（周一=1，周日=7，需要转换成周一为第一天）
    val firstDayOfWeek = firstDayOfMonth.dayOfWeek.value // 周一=1，周日=7
    val daysToPrevMonth = firstDayOfWeek - 1 // 需要补齐的上个月天数
    val startDate = firstDayOfMonth.minusDays(daysToPrevMonth.toLong())

    // 总共显示6周即42天，保证完整
    return (0 until 42).map { startDate.plusDays(it.toLong()) }
}