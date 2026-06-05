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
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.example.motiwish.data.model.OneShotTask
import com.example.motiwish.data.network.PricingSession

import com.example.motiwish.viewmodel.UserViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

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

    /*
    var isFirstLoad by remember { mutableStateOf(true) }

    LaunchedEffect(isFirstLoad) {
        if (isFirstLoad) {
            if (TokenManager.getToken() != null) {
                viewModel.syncTasksFromRemote()
            }
            isFirstLoad = false
        }
    }
    */
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
                            Text("今日已评估，获得: ${todayMetric?.reward ?: 0} 货币")
                        } else {
                            OutlinedTextField(
                                value = todayMetric?.wakeUpTime ?: "",
                                onValueChange = {
                                    viewModel.updateDailyMetric(
                                        it,
                                        todayMetric?.sleepTime ?: "",
                                        todayMetric?.phoneUsageMinutes ?: 0,
                                        todayMetric?.waterCups ?: 0
                                    )
                                },
                                label = { Text("起床时间 (HH:MM)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = todayMetric?.sleepTime ?: "",
                                onValueChange = {
                                    viewModel.updateDailyMetric(
                                        todayMetric?.wakeUpTime ?: "",
                                        it,
                                        todayMetric?.phoneUsageMinutes ?: 0,
                                        todayMetric?.waterCups ?: 0
                                    )
                                },
                                label = { Text("睡觉时间 (HH:MM)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = (todayMetric?.phoneUsageMinutes ?: 0).toString(),
                                onValueChange = {
                                    val intValue = it.toIntOrNull() ?: 0
                                    viewModel.updateDailyMetric(
                                        todayMetric?.wakeUpTime ?: "",
                                        todayMetric?.sleepTime ?: "",
                                        intValue,
                                        todayMetric?.waterCups ?: 0
                                    )
                                },
                                label = { Text("手机使用时长 (分钟)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = (todayMetric?.waterCups ?: 0).toString(),
                                onValueChange = {
                                    val intValue = it.toIntOrNull() ?: 0
                                    viewModel.updateDailyMetric(
                                        todayMetric?.wakeUpTime ?: "",
                                        todayMetric?.sleepTime ?: "",
                                        todayMetric?.phoneUsageMinutes ?: 0,
                                        intValue
                                    )
                                },
                                label = { Text("喝水杯数") },
                                modifier = Modifier.fillMaxWidth()
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

            // ---------- 定价中任务卡片 ----------
            if (taskDrafts.isNotEmpty()) {
                item {
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
                            taskDrafts.forEach { draft ->
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
                                                CircularProgressIndicator(
                                                    modifier = Modifier.size(16.dp),
                                                    strokeWidth = 2.dp
                                                )
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
                                                CircularProgressIndicator(
                                                    modifier = Modifier.size(16.dp),
                                                    strokeWidth = 2.dp
                                                )
                                                Spacer(modifier = Modifier.width(8.dp))
                                                Text("AI 重新定价中...", style = MaterialTheme.typography.bodySmall)
                                            }
                                        }
                                        else -> {
                                            // 可处理其他状态（如 repricing）
                                            Text(draft.status, style = MaterialTheme.typography.bodySmall)
                                        }
                                    }
                                }
                                if (draft != taskDrafts.last()) {
                                    Divider(modifier = Modifier.padding(vertical = 4.dp))
                                }
                            }
                        }
                    }
                }
            }

            // ---------- 周期任务卡片 ----------
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Text(
                            text = "今日周期任务",
                            style = MaterialTheme.typography.titleLarge,
                            color = MaterialTheme.colorScheme.primary
                        )

                        if (sortedPeriodicTasks.isEmpty()) {
                            Text("今日没有周期任务")
                        } else {
                            var showDeleteDialog by remember { mutableStateOf(false) }
                            var taskToDelete by remember { mutableStateOf<TodayPeriodicTask?>(null) }

                            sortedPeriodicTasks.forEach { task ->
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(task.name, style = MaterialTheme.typography.bodyLarge)
                                        task.description?.let {
                                            Text(it, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                                        }
                                        if (task.pricingStatus == "pending") {
                                            Text("AI定价中", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                                        } else {
                                            Text("奖励: ${task.rewardAmount}", style = MaterialTheme.typography.bodySmall)
                                        }
                                    }
                                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        if (task.completed) {
                                            Icon(Icons.Default.CheckCircle, contentDescription = "已完成", tint = Color.Green)
                                        } else {
                                            if (task.pricingStatus == "pending") {
                                                Button(
                                                    enabled = false,
                                                    onClick = { },
                                                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary.copy(alpha = 0.5f))
                                                ) {
                                                    Text("定价中")
                                                }
                                            } else {
                                                Button(
                                                    onClick = { viewModel.completePeriodicTask(task) },
                                                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                                                ) {
                                                    Text("完成")
                                                }
                                            }
                                        }
                                        IconButton(
                                            onClick = {
                                                taskToDelete = task
                                                showDeleteDialog = true
                                            }
                                        ) {
                                            Icon(Icons.Default.Delete, contentDescription = "删除")
                                        }
                                    }
                                }
                                Divider()
                            }

                            if (showDeleteDialog && taskToDelete != null) {
                                AlertDialog(
                                    onDismissRequest = { showDeleteDialog = false },
                                    title = { Text("确认删除") },
                                    text = { Text("确定要删除任务 \"${taskToDelete?.name}\" 吗？") },
                                    confirmButton = {
                                        TextButton(
                                            onClick = {
                                                taskToDelete?.let { viewModel.deletePeriodicTask(it) }
                                                showDeleteDialog = false
                                                taskToDelete = null
                                            }
                                        ) {
                                            Text("删除")
                                        }
                                    },
                                    dismissButton = {
                                        TextButton(onClick = {
                                            showDeleteDialog = false
                                            taskToDelete = null
                                        }) {
                                            Text("取消")
                                        }
                                    }
                                )
                            }
                        }
                    }
                }
            }

            // ---------- 一次性任务卡片 ----------
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = "一次性任务",
                                style = MaterialTheme.typography.titleLarge,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }

                        if (sortedOneShotTasks.isEmpty()) {
                            Text("暂无一次性任务")
                        } else {
                            val showDeleteDialogState = remember { mutableStateOf(false) }
                            val taskToDeleteState = remember { mutableStateOf<OneShotTask?>(null) }

                            sortedOneShotTasks.forEach { task ->
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                                ) {
                                    Column(modifier = Modifier.padding(12.dp)) {
                                        Text(task.name, style = MaterialTheme.typography.titleMedium)
                                        Text(task.description, style = MaterialTheme.typography.bodySmall)
                                        Text(
                                            "截止: ${task.deadline.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"))}",
                                            style = MaterialTheme.typography.bodySmall
                                        )

                                        if (task.status == "ACTIVE" && !task.evaluated) {
                                            if (task.settlementTrack == "exploration") {
                                                // 探索任务
                                                Row(
                                                    modifier = Modifier.fillMaxWidth(),
                                                    horizontalArrangement = Arrangement.SpaceBetween
                                                ) {
                                                    Column {
                                                        Text("预估专注: ${task.estimatedFocusMinutes ?: 0} 分钟")
                                                        Text("已专注: ${task.progress} 分钟")
                                                    }
                                                    Button(
                                                        onClick = {
                                                            navController.navigate("focusTimer/${task.id}/${task.progress}/${task.estimatedFocusMinutes ?: 0}")
                                                        }
                                                    ) {
                                                        Text(if (task.progress > 0) "继续探索" else "开始探索")
                                                    }
                                                }
                                                // 手动结算按钮
                                                Button(
                                                    onClick = { viewModel.manuallyCompleteOneShotTask(task.id) },
                                                    modifier = Modifier.fillMaxWidth(),
                                                    enabled = task.progress > 0  // 至少有一点进度才能结算
                                                ) {
                                                    Text("手动评估并结算")
                                                }
                                            } else {
                                                // Regular 任务
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
                                                    enabled = task.progress < 100  // 达到100后禁用滑块
                                                )
                                                Text("进度: ${task.progress}%")

                                                // 手动结算按钮（始终可用，用于提前放弃/结算）
                                                Button(
                                                    onClick = { viewModel.manuallyCompleteOneShotTask(task.id) },
                                                    modifier = Modifier.fillMaxWidth(),
                                                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                                                ) {
                                                    Text(if (task.progress >= 100) "领取奖励" else "手动结算（放弃任务）")
                                                }
                                            }
                                        } else {
                                            Text(
                                                "状态: ${when (task.status) {
                                                    "COMPLETED" -> "已完成"
                                                    "FAILED" -> "失败"
                                                    else -> "进行中"
                                                }}",
                                                color = if (task.status == "COMPLETED") Color.Green else Color.Red
                                            )
                                            Text(
                                                "奖惩: ${task.actualReward ?: task.reward} / ${task.actualPenalty ?: task.penalty}",
                                                color = if (task.status == "COMPLETED") Color.Green else Color.Red
                                            )
                                        }

                                        IconButton(
                                            onClick = {
                                                taskToDeleteState.value = task
                                                showDeleteDialogState.value = true
                                            },
                                            modifier = Modifier.align(Alignment.End)
                                        ) {
                                            Icon(Icons.Default.Delete, contentDescription = "删除")
                                        }
                                    }
                                }
                            }

                            if (showDeleteDialogState.value && taskToDeleteState.value != null) {
                                AlertDialog(
                                    onDismissRequest = { showDeleteDialogState.value = false },
                                    title = { Text("确认删除") },
                                    text = { Text("确定要删除任务 \"${taskToDeleteState.value?.name}\" 吗？") },
                                    confirmButton = {
                                        TextButton(
                                            onClick = {
                                                taskToDeleteState.value?.let { viewModel.deleteOneShotTask(it) }
                                                showDeleteDialogState.value = false
                                                taskToDeleteState.value = null
                                            }
                                        ) {
                                            Text("删除")
                                        }
                                    },
                                    dismissButton = {
                                        TextButton(onClick = {
                                            showDeleteDialogState.value = false
                                            taskToDeleteState.value = null
                                        }) {
                                            Text("取消")
                                        }
                                    }
                                )
                            }
                        }
                    }
                }
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