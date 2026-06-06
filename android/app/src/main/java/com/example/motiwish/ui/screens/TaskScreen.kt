package com.example.motiwish.ui.screens

import android.util.Log
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.window.Dialog
import androidx.compose.material3.TimePicker
import androidx.compose.material3.rememberTimePickerState
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.TextButton
import androidx.navigation.NavController
import com.example.motiwish.viewmodel.TaskViewModel
import com.example.motiwish.viewmodel.TodayPeriodicTask
import androidx.compose.ui.graphics.Color
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.Instant
import java.time.ZoneId
import kotlinx.coroutines.delay

import com.example.motiwish.data.network.TokenManager
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.example.motiwish.data.model.OneShotTask
import com.example.motiwish.data.network.PricingSession

import com.example.motiwish.viewmodel.UserViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.motiwish.data.model.DailyMetric
import com.example.motiwish.data.model.TaskDraft

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TaskScreen(
    viewModel: TaskViewModel,
    userViewModel: UserViewModel,
    navController: NavController
){
    val showOnboarding by userViewModel.showOnboarding.collectAsStateWithLifecycle()

    val showDynamicPrompt by userViewModel.showDynamicPrompt.collectAsStateWithLifecycle()

    LaunchedEffect(showOnboarding) {
        if (showOnboarding) {
            navController.navigate("onboarding") {
                launchSingleTop = true
            }
        }
    }
    val todayMetric by viewModel.todayMetric.collectAsState()
    val todaysPeriodicTasks by viewModel.todaysPeriodicTasks.collectAsState()
    val oneShotTasks by viewModel.oneShotTasks.collectAsState()
    val taskDrafts by viewModel.taskDrafts.collectAsState()     // 定价中的任务（还未创建）

    // 排序：未完成的排前面
    val sortedPeriodicTasks = todaysPeriodicTasks.sortedBy { it.completed }
    val sortedOneShotTasks = oneShotTasks.sortedWith(compareBy {
        when (it.status) {
            "ACTIVE" -> 0
            else -> 1
        }
    })

    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        userViewModel.checkProfilePromptStatus()
    }

    // 生命周期监听：页面每次可见时刷新数据
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                viewModel.syncTasksFromRemote()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    LaunchedEffect(Unit) {
        viewModel.uiMessage.collect { message ->
            snackbarHostState.showSnackbar(message)
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { navController.navigate("addTask") },
                containerColor = MaterialTheme.colorScheme.primary
            ) {
                Icon(Icons.Default.Add, contentDescription = "添加周期任务")
            }
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // ---------- 日常指标卡片 ----------
            item {
                DailyMetricCard(
                    todayMetric = todayMetric,
                    viewModel = viewModel
                )
            }

            // ---------- 定价中任务卡片 ----------
            if (taskDrafts.isNotEmpty()) {
                item {
                    PricingDraftsCard(
                        drafts = taskDrafts,
                        viewModel = viewModel
                    )
                }
            }

            // ---------- 周期任务标题 ----------
            item {
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                Text(
                    text = "今日任务",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(top = 8.dp, bottom = 8.dp, start = 16.dp)
                )
            }

            // ---------- 周期任务列表（每个任务一个 item）----------
            items(sortedPeriodicTasks) { task ->
                PeriodicTaskCard(
                    task = task,
                    viewModel = viewModel,
                    snackbarHostState = snackbarHostState,
                    onEdit = { taskToEdit ->
                        // 这里实现编辑逻辑，例如跳转到编辑页面
                        //scope.launch {
                            //snackbarHostState.showSnackbar("编辑功能开发中：${taskToEdit.name}")
                        //}
                    }
                )
            }

            // ---------- 一次性任务标题 ----------
            item {
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                Text(
                    text = "一次性任务",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(top = 8.dp, bottom = 8.dp, start = 16.dp)
                )
            }

            // ---------- 一次性任务列表（每个任务一个 item）----------
            items(sortedOneShotTasks) { task ->
                OneShotTaskCard(
                    task = task,
                    viewModel = viewModel,
                    navController = navController,
                    snackbarHostState = snackbarHostState,
                    onEdit = { taskToEdit ->
                        //scope.launch {
                            //snackbarHostState.showSnackbar("编辑功能开发中：${taskToEdit.name}")
                        //}
                    }
                )
            }
        }

        // 显示定价对话
        val pricingDialogState by viewModel.selectedDraftForPricing.collectAsState()
        pricingDialogState?.let { (draftId, session) ->
            PricingDialog(
                session = session,
                onAccept = { viewModel.acceptPricingAndCreate(draftId) },
                onRevise = { direction, text -> viewModel.revisePricing(draftId, direction, text) },
                onDismiss = { viewModel.dismissPricingDialog() }
            )
        }
    }

    // 当 showDynamicPrompt 为 true 时，呼出底部半屏弹窗
    if (showDynamicPrompt) {
        DynamicProfileSheet(
            viewModel = userViewModel,
            onDismiss = {
                // 因为我们在 ViewModel 里已经处理了关闭状态 (_showDynamicPrompt.value = false)
                // 以及跳过 (skip) / 提交 (submit) 的逻辑，所以这里留空即可。
            }
        )
    }
}

// 添加任务页面（已合并）
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddTaskScreen(viewModel: TaskViewModel, navController: NavController) {
    // 通用字段
    var taskName by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var taskType by remember { mutableStateOf("DAILY") } // "DAILY", "WEEKLY", "MONTHLY", "ONE_TIME"

    // 周期任务字段
    var dayValue by remember { mutableStateOf(1) } // 周几或每月几号

    // 一次性任务字段
    var isExploration by remember { mutableStateOf(false) }
    var estimatedMinutes by remember { mutableStateOf("") }
    val datePickerState = rememberDatePickerState(
        initialSelectedDateMillis = LocalDate.now().plusDays(7)
            .atStartOfDay(ZoneId.systemDefault())
            .toInstant()
            .toEpochMilli()
    )
    val timePickerState = rememberTimePickerState(
        initialHour = 23,
        initialMinute = 59,
        is24Hour = true
    )

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    // 定价会话观察
    val pricingSession by viewModel.pricingSession.collectAsState()
    val isPricingLoading by viewModel.isPricingLoading.collectAsState()

    // 监听成功消息，自动返回
    LaunchedEffect(Unit) {
        viewModel.uiMessage.collect { message ->
            if (message == "任务添加成功") {
                delay(300)
                navController.popBackStack()
            }
        }
    }

    // 显示定价对话框
    if (pricingSession != null) {
        PricingDialog(
            session = pricingSession!!,
            onAccept = { viewModel.acceptPricingAndCreate(pricingSession!!.id) },
            onRevise = { direction, text -> viewModel.revisePricing(pricingSession!!.id, direction, text) },
            onDismiss = { viewModel.dismissPricingDialog() }
        )
    }

    fun getSelectedDateTime(): LocalDateTime? {
        val selectedDateMillis = datePickerState.selectedDateMillis
        val selectedDate = selectedDateMillis?.let {
            Instant.ofEpochMilli(it).atZone(ZoneId.systemDefault()).toLocalDate()
        }
        val selectedTime = LocalTime.of(timePickerState.hour, timePickerState.minute)
        return selectedDate?.atTime(selectedTime)
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("添加任务") },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 任务名称
            OutlinedTextField(
                value = taskName,
                onValueChange = { taskName = it },
                label = { Text("任务名称") },
                modifier = Modifier.fillMaxWidth()
            )
            // 描述
            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text("任务描述") },
                modifier = Modifier.fillMaxWidth()
            )
            // 任务类型选择
            Text("任务类型")
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                listOf("DAILY" to "每日", "WEEKLY" to "每周", "MONTHLY" to "每月", "ONE_TIME" to "一次性").forEach { (type, label) ->
                    FilterChip(
                        selected = taskType == type,
                        onClick = { taskType = type },
                        label = { Text(label) }
                    )
                }
            }

            // 根据类型显示不同表单
            when (taskType) {
                "WEEKLY" -> {
                    Text("选择星期几")
                    Row {
                        (1..7).forEach { day ->
                            FilterChip(
                                selected = dayValue == day,
                                onClick = { dayValue = day },
                                label = { Text(day.toString()) },
                                modifier = Modifier.padding(end = 4.dp)
                            )
                        }
                    }
                }
                "MONTHLY" -> {
                    OutlinedTextField(
                        value = dayValue.toString(),
                        onValueChange = { dayValue = it.toIntOrNull() ?: 1 },
                        label = { Text("每月几号 (1-31)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                "ONE_TIME" -> {
                    // 探索任务开关
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("设定为探索任务", modifier = Modifier.weight(1f))
                        Switch(checked = isExploration, onCheckedChange = { isExploration = it })
                    }
                    if (isExploration) {
                        OutlinedTextField(
                            value = estimatedMinutes,
                            onValueChange = { estimatedMinutes = it },
                            label = { Text("预估专注时长 (分钟)") },
                            modifier = Modifier.fillMaxWidth(),
                            isError = estimatedMinutes.isNotBlank() && estimatedMinutes.toIntOrNull() == null
                        )
                    }
                    Text("截止日期")
                    DatePicker(state = datePickerState, modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp))
                    Text("截止时间")
                    TimePicker(state = timePickerState, modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp))
                }
                // DAILY 不需要额外字段
            }

            Button(
                onClick = {
                    if (taskName.isBlank()) {
                        scope.launch { snackbarHostState.showSnackbar("请填写任务名称") }
                        return@Button
                    }
                    if (taskType == "ONE_TIME") {
                        val deadline = getSelectedDateTime()
                        if (deadline == null) {
                            scope.launch { snackbarHostState.showSnackbar("请选择有效的截止日期和时间") }
                            return@Button
                        }
                        val estimated = if (isExploration) estimatedMinutes.toIntOrNull() else null
                        if (isExploration && (estimated == null || estimated <= 0)) {
                            scope.launch { snackbarHostState.showSnackbar("请填写有效的专注时长") }
                            return@Button
                        }
                        viewModel.createTaskDraftAsync(
                            taskType = "one_time",
                            title = taskName,
                            description = description,
                            dueAt = deadline,
                            settlementTrack = if (isExploration) "exploration" else "regular",
                            estimatedFocusMinutes = estimated   // 仅探索任务传入
                        )
                        navController.popBackStack()     // 立即返回主页
                    } else {
                        // 周期任务
                        val recurrence = when (taskType) {
                            "DAILY" -> "daily"
                            "WEEKLY" -> "weekly"
                            "MONTHLY" -> "monthly"
                            else -> "none"
                        }
                        val weekdays = if (taskType == "WEEKLY") listOf(dayValue - 1) else null
                        val monthDays = if (taskType == "MONTHLY") listOf(dayValue) else null
                        viewModel.createTaskDraftAsync(
                            taskType = "recurring",
                            title = taskName,
                            description = description,
                            recurrence = recurrence,
                            weekdays = weekdays,
                            monthDays = monthDays
                        )
                        navController.popBackStack()     // 立即返回主页
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                if (isPricingLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp))
                } else {
                    Text("创建任务")
                }
            }
        }
    }
}

// 定价中任务卡片
@Composable
fun PricingDraftsCard(
    drafts: List<TaskDraft>,
    viewModel: TaskViewModel
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "定价中的任务",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.primary
            )
            drafts.forEach { draft ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = draft.title,
                        style = MaterialTheme.typography.bodyLarge,
                        modifier = Modifier.weight(1f)
                    )
                    when (draft.status) {
                        "pricing" -> {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("AI 定价中...", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                        "quoted" -> {
                            Button(
                                onClick = { viewModel.showPricingDialog(draft.id) },
                                modifier = Modifier.wrapContentWidth()
                            ) {
                                Text("已定价，点击查看")
                            }
                        }
                        "repricing" -> {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("AI 重新定价中...", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                        else -> {
                            Text(draft.status, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
                if (draft != drafts.last()) {
                    Divider(modifier = Modifier.padding(vertical = 4.dp))
                }
            }
        }
    }
}

@Composable
fun PricingDialog(
    session: PricingSession,
    onAccept: () -> Unit,
    onRevise: (direction: String, text: String) -> Unit,
    onDismiss: () -> Unit
) {
    var feedbackText by remember { mutableStateOf("") }
    var selectedDirection by remember { mutableStateOf("too_high") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("AI 定价建议") },
        text = {
            Column {
                Text("奖励: ${session.quote_payload.reward_primary}")
                Text("惩罚: ${session.quote_payload.penalty_primary}")
                Text("理由: ${session.quote_payload.reasoning}")
                if (session.quote_payload.risk_notes.isNotEmpty()) {
                    Text("风险: ${session.quote_payload.risk_notes.joinToString()}")
                }
                Spacer(modifier = Modifier.height(8.dp))
                // 反馈选项（仅当 status == "waiting_feedback" 时显示）
                if (session.status == "waiting_feedback") {
                    Row {
                        listOf("too_high" to "偏高", "too_low" to "偏低", "detail" to "详细说明").forEach { (dir, label) ->
                            FilterChip(
                                selected = selectedDirection == dir,
                                onClick = { selectedDirection = dir },
                                label = { Text(label) }
                            )
                        }
                    }
                    OutlinedTextField(
                        value = feedbackText,
                        onValueChange = { feedbackText = it },
                        label = { Text("反馈内容 (可选)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Row {
                        Button(onClick = {
                            onRevise(selectedDirection, feedbackText)  // 这个 onRevise 应调用 revisePricing
                        }) {
                            Text("调整定价")
                        }
                        Button(onClick = onAccept) {
                            Text("接受并创建任务")
                        }
                    }
                } else {
                    // 可能处于重新定价加载状态
                    CircularProgressIndicator()
                }
            }
        },
        confirmButton = {},
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DailyMetricCard(
    todayMetric: DailyMetric?,
    viewModel: TaskViewModel
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "今日日常指标",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.primary
            )

            if (todayMetric?.evaluated == true) {
                Text("今日已评估，获得: ${todayMetric.reward} 货币")
            } else {
                // 解析起床时间（从 "HH:MM" 字符串）
                val wakeParts = (todayMetric?.wakeUpTime ?: "00:00").split(":").mapNotNull { it.toIntOrNull() }
                val wakeHour = wakeParts.getOrElse(0) { 0 }.coerceIn(0, 23)
                val wakeMinute = wakeParts.getOrElse(1) { 0 }.coerceIn(0, 59)

                // 起床时间 - 小时 & 分钟并排
                Text("起床时间", style = MaterialTheme.typography.bodyMedium)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = if (wakeHour == 0 && wakeMinute == 0) "" else wakeHour.toString(),
                        onValueChange = { newValue ->
                            val newHour = if (newValue.isEmpty()) 0 else (newValue.toIntOrNull()?.coerceIn(0, 23) ?: 0)
                            val newTime = String.format("%02d:%02d", newHour, wakeMinute)
                            viewModel.updateDailyMetric(
                                newTime,
                                todayMetric?.sleepTime ?: "",
                                todayMetric?.phoneUsageMinutes ?: 0,
                                todayMetric?.waterCups ?: 0
                            )
                        },
                        label = { Text("小时") },
                        modifier = Modifier.weight(1f),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                    )
                    OutlinedTextField(
                        value = if (wakeHour == 0 && wakeMinute == 0) "" else wakeMinute.toString(),
                        onValueChange = { newValue ->
                            val newMinute = if (newValue.isEmpty()) 0 else (newValue.toIntOrNull()?.coerceIn(0, 59) ?: 0)
                            val newTime = String.format("%02d:%02d", wakeHour, newMinute)
                            viewModel.updateDailyMetric(
                                newTime,
                                todayMetric?.sleepTime ?: "",
                                todayMetric?.phoneUsageMinutes ?: 0,
                                todayMetric?.waterCups ?: 0
                            )
                        },
                        label = { Text("分钟") },
                        modifier = Modifier.weight(1f),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                    )
                }

                // 睡觉时间
                val sleepParts = (todayMetric?.sleepTime ?: "00:00").split(":").mapNotNull { it.toIntOrNull() }
                val sleepHour = sleepParts.getOrElse(0) { 0 }.coerceIn(0, 23)
                val sleepMinute = sleepParts.getOrElse(1) { 0 }.coerceIn(0, 59)

                Text("睡觉时间", style = MaterialTheme.typography.bodyMedium)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = if (sleepHour == 0 && sleepMinute == 0) "" else sleepHour.toString(),
                        onValueChange = { newValue ->
                            val newHour = if (newValue.isEmpty()) 0 else (newValue.toIntOrNull()?.coerceIn(0, 23) ?: 0)
                            val newTime = String.format("%02d:%02d", newHour, sleepMinute)
                            viewModel.updateDailyMetric(
                                todayMetric?.wakeUpTime ?: "",
                                newTime,
                                todayMetric?.phoneUsageMinutes ?: 0,
                                todayMetric?.waterCups ?: 0
                            )
                        },
                        label = { Text("小时") },
                        modifier = Modifier.weight(1f),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                    )
                    OutlinedTextField(
                        value = if (sleepHour == 0 && sleepMinute == 0) "" else sleepMinute.toString(),
                        onValueChange = { newValue ->
                            val newMinute = if (newValue.isEmpty()) 0 else (newValue.toIntOrNull()?.coerceIn(0, 59) ?: 0)
                            val newTime = String.format("%02d:%02d", sleepHour, newMinute)
                            viewModel.updateDailyMetric(
                                todayMetric?.wakeUpTime ?: "",
                                newTime,
                                todayMetric?.phoneUsageMinutes ?: 0,
                                todayMetric?.waterCups ?: 0
                            )
                        },
                        label = { Text("分钟") },
                        modifier = Modifier.weight(1f),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                    )
                }

                // 手机使用时长：小时 + 分钟（数字输入）
                Text("手机使用时长", style = MaterialTheme.typography.bodyMedium)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    val totalMinutes = todayMetric?.phoneUsageMinutes ?: 0
                    val hours = totalMinutes / 60
                    val minutes = totalMinutes % 60

                    // 手机使用时长的“小时”输入框
                    val hoursText = if (hours == 0) "" else hours.toString()
                    OutlinedTextField(
                        value = hoursText,
                        onValueChange = { newValue ->
                            val newHours = if (newValue.isEmpty()) 0 else (newValue.toIntOrNull()?.coerceIn(0, 23) ?: 0)
                            val newTotal = newHours * 60 + minutes
                            viewModel.updateDailyMetric(
                                todayMetric?.wakeUpTime ?: "",
                                todayMetric?.sleepTime ?: "",
                                newTotal,
                                todayMetric?.waterCups ?: 0
                            )
                        },
                        label = { Text("小时") },
                        modifier = Modifier.weight(1f),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                    )

                    // 手机使用时长的“分钟”输入框
                    val minutesText = if (minutes == 0) "" else minutes.toString()
                    OutlinedTextField(
                        value = minutesText,
                        onValueChange = { newValue ->
                            val newMinutes = if (newValue.isEmpty()) 0 else (newValue.toIntOrNull()?.coerceIn(0, 59) ?: 0)
                            val newTotal = hours * 60 + newMinutes
                            viewModel.updateDailyMetric(
                                todayMetric?.wakeUpTime ?: "",
                                todayMetric?.sleepTime ?: "",
                                newTotal,
                                todayMetric?.waterCups ?: 0
                            )
                        },
                        label = { Text("分钟") },
                        modifier = Modifier.weight(1f),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                    )
                }

                // 喝水杯数
                OutlinedTextField(
                    value = (todayMetric?.waterCups ?: 0).toString(),
                    onValueChange = { newValue ->
                        val cups = if (newValue.isEmpty()) 0 else (newValue.toIntOrNull() ?: 0)
                        viewModel.updateDailyMetric(
                            todayMetric?.wakeUpTime ?: "",
                            todayMetric?.sleepTime ?: "",
                            todayMetric?.phoneUsageMinutes ?: 0,
                            cups
                        )
                    },
                    label = { Text("喝水杯数") },
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                )

                Button(
                    onClick = { viewModel.evaluateDailyMetric() },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Text("评估今日日常")
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TimePickerDialog(
    initialTime: String,  // 格式 "HH:MM"
    onConfirm: (String) -> Unit,
    onDismiss: () -> Unit
) {
    // 解析初始小时和分钟
    val parts = initialTime.split(":").mapNotNull { it.toIntOrNull() }
    val initialHour = parts.getOrElse(0) { 0 }.coerceIn(0, 23)
    val initialMinute = parts.getOrElse(1) { 0 }.coerceIn(0, 59)

    val timePickerState = rememberTimePickerState(
        initialHour = initialHour,
        initialMinute = initialMinute,
        is24Hour = true
    )

    Dialog(onDismissRequest = onDismiss) {
        Card(
            shape = MaterialTheme.shapes.medium,
            modifier = Modifier.fillMaxWidth(),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                TimePicker(state = timePickerState)
                Spacer(modifier = Modifier.height(16.dp))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("取消")
                    }
                    TextButton(
                        onClick = {
                            val hour = timePickerState.hour
                            val minute = timePickerState.minute
                            val timeStr = String.format("%02d:%02d", hour, minute)
                            onConfirm(timeStr)
                        }
                    ) {
                        Text("确定")
                    }
                }
            }
        }
    }
}

// 周期任务卡片
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PeriodicTaskCard(
    task: TodayPeriodicTask,
    viewModel: TaskViewModel,
    snackbarHostState: SnackbarHostState,
    onEdit: (TodayPeriodicTask) -> Unit
) {
    var showBottomSheet by remember { mutableStateOf(false) }
    var showDeleteConfirm by remember { mutableStateOf(false) }
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { showBottomSheet = true },
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(task.name, style = MaterialTheme.typography.titleMedium)
                task.description?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                }
                if (task.pricingStatus == "pending") {
                    Text("AI定价中", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                } else {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text("奖励: ${task.rewardAmount}", style = MaterialTheme.typography.bodySmall)
                        if (!task.completed) {
                            Text(
                                "惩罚: ${task.penaltyAmount}",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                    }
                }
            }

            if (task.completed) {
                Button(
                    onClick = { /* 已完成，无操作 */ },
                    enabled = false,  // 禁用点击
                    modifier = Modifier.width(100.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant,
                        contentColor = Color.Gray
                    )
                ) {
                    Text("已完成")
                }
            } else {
                Button(
                    onClick = { viewModel.completePeriodicTask(task) },
                    modifier = Modifier.width(100.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                ) {
                    Text("完成")
                }
            }
        }
    }

    // 底部操作菜单
    if (showBottomSheet) {
        ModalBottomSheet(
            onDismissRequest = { showBottomSheet = false },
            sheetState = sheetState
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                TextButton(
                    onClick = {
                        showBottomSheet = false
                        viewModel.deletePeriodicTask(task)   // 直接删除
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("删除", modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }
}

// 一次性任务卡片
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OneShotTaskCard(
    task: OneShotTask,
    viewModel: TaskViewModel,
    navController: NavController,
    snackbarHostState: SnackbarHostState,
    onEdit: (OneShotTask) -> Unit
) {
    var showBottomSheet by remember { mutableStateOf(false) }
    var showDeleteConfirm by remember { mutableStateOf(false) }
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { showBottomSheet = true },
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(task.name, style = MaterialTheme.typography.titleMedium)
            Text(task.description, style = MaterialTheme.typography.bodySmall)
            Text(
                "截止: ${task.deadline.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"))}",
                style = MaterialTheme.typography.bodySmall
            )
            // 显示奖励和惩罚（预估）
            if (task.status == "ACTIVE" && !task.evaluated) {
                Text("奖励: ${task.reward}  /  惩罚: ${task.penalty}", style = MaterialTheme.typography.bodySmall)
            }

            when {
                task.status == "ACTIVE" && !task.evaluated -> {
                    if (task.settlementTrack == "exploration") {
                        Text("专注进度: ${task.progress} / ${task.estimatedFocusMinutes ?: 0} 分钟")
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Button(
                                onClick = {
                                    navController.navigate("focusTimer/${task.id}/${task.progress}/${task.estimatedFocusMinutes ?: 0}")
                                },
                                modifier = Modifier.weight(1f)
                            ) {
                                Text(if (task.progress > 0) "继续探索" else "开始探索")
                            }
                            Button(
                                onClick = { viewModel.manuallyCompleteOneShotTask(task.id) },
                                modifier = Modifier.weight(1f),
                                enabled = task.progress > 0
                            ) {
                                Text("手动评估并结算")
                            }
                        }
                    } else {
                        Text("完成进度: ${task.progress}%")
                        Slider(
                            value = task.progress.toFloat(),
                            onValueChange = { newProgress ->
                                viewModel.updateLocalProgressOnly(task.id, newProgress.toInt())
                            },
                            onValueChangeFinished = {
                                viewModel.persistProgress(task.id)
                            },
                            valueRange = 0f..100f,
                            modifier = Modifier.fillMaxWidth(),
                            enabled = task.progress < 100
                        )
                        Button(
                            onClick = { viewModel.manuallyCompleteOneShotTask(task.id) },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                        ) {
                            Text(if (task.progress >= 100) "领取奖励" else "手动结算（放弃任务）")
                        }
                    }
                }
                else -> {
                    Text(
                        "状态: ${when (task.status) {
                            "COMPLETED" -> "已完成"
                            "FAILED" -> "失败"
                            else -> "进行中"
                        }}"
                    )
                    Text(
                        "奖惩: ${task.actualReward ?: task.reward} / ${task.actualPenalty ?: task.penalty}",
                        color = if (task.status == "COMPLETED") MaterialTheme.colorScheme.primary else Color.Red
                    )
                }
            }
        }
    }

    // 底部操作菜单
    if (showBottomSheet) {
        ModalBottomSheet(
            onDismissRequest = { showBottomSheet = false },
            sheetState = sheetState
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                TextButton(
                    onClick = {
                        showBottomSheet = false
                        viewModel.deleteOneShotTask(task)   // 直接删除
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("删除", modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }
}