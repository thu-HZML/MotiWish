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
import androidx.navigation.NavController
import com.example.motiwish.data.model.PeriodicTask
import com.example.motiwish.viewmodel.TaskViewModel
import androidx.compose.ui.graphics.Color
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.Instant
import java.time.ZoneId

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TaskScreen(viewModel: TaskViewModel, navController: NavController) {
    val todayMetric by viewModel.todayMetric.collectAsState()
    val todaysPeriodicTasks by viewModel.todaysPeriodicTasks.collectAsState()
    val oneShotTasks by viewModel.oneShotTasks.collectAsState()
    val sortedPeriodicTasks = todaysPeriodicTasks.sortedBy { it.second } // false（未完成）在前，true（已完成）在后
    val sortedOneShotTasks = oneShotTasks.sortedWith(compareBy {
        when (it.status) {
            "ACTIVE" -> 0  // 进行中（未完成）排最前
            else -> 1      // COMPLETED 或 FAILED 排后面
        }
    })
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    // 监听返回结果
    LaunchedEffect(Unit) {
        val savedStateHandle = navController.currentBackStackEntry?.savedStateHandle
        savedStateHandle?.getLiveData<Boolean>("periodic_task_added")?.observeForever { added ->
            if (added == true) {
                scope.launch {
                    snackbarHostState.showSnackbar(
                        message = "周期任务添加成功",
                        duration = SnackbarDuration.Long
                    )
                }
                savedStateHandle.remove<Boolean>("periodic_task_added")
            }
        }
        // 相同方式处理一次性任务添加成功（如果也需要）
        savedStateHandle?.getLiveData<Boolean>("one_shot_task_added")?.observeForever { added ->
            if (added == true) {
                scope.launch {
                    snackbarHostState.showSnackbar(
                        message = "一次性任务添加成功",
                        duration = SnackbarDuration.Long
                    )
                }
                savedStateHandle.remove<Boolean>("one_shot_task_added")
            }
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { navController.navigate("addPeriodicTask") },
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
            // Daily Tasks Section
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
                                onValueChange = { viewModel.updateDailyMetric(it, todayMetric?.sleepTime ?: "", todayMetric?.phoneUsageMinutes ?: 0, todayMetric?.waterCups ?: 0) },
                                label = { Text("起床时间 (HH:MM)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = todayMetric?.sleepTime ?: "",
                                onValueChange = { viewModel.updateDailyMetric(todayMetric?.wakeUpTime ?: "", it, todayMetric?.phoneUsageMinutes ?: 0, todayMetric?.waterCups ?: 0) },
                                label = { Text("睡觉时间 (HH:MM)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = (todayMetric?.phoneUsageMinutes ?: 0).toString(),
                                onValueChange = {
                                    val intValue = it.toIntOrNull() ?: 0
                                    viewModel.updateDailyMetric(todayMetric?.wakeUpTime ?: "", todayMetric?.sleepTime ?: "", intValue, todayMetric?.waterCups ?: 0)
                                },
                                label = { Text("手机使用时长 (分钟)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = (todayMetric?.waterCups ?: 0).toString(),
                                onValueChange = {
                                    val intValue = it.toIntOrNull() ?: 0
                                    viewModel.updateDailyMetric(todayMetric?.wakeUpTime ?: "", todayMetric?.sleepTime ?: "", todayMetric?.phoneUsageMinutes ?: 0, intValue)
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

            // Periodic Tasks Section
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
                            sortedPeriodicTasks.forEach { (task, completed) ->
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(task.name, style = MaterialTheme.typography.bodyLarge)
                                        Text("奖励: ${task.rewardAmount}", style = MaterialTheme.typography.bodySmall)
                                    }
                                    if (completed) {
                                        Icon(Icons.Default.CheckCircle, contentDescription = "已完成", tint = Color.Green)
                                    } else {
                                        Button(
                                            onClick = { viewModel.completePeriodicTask(task) },
                                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                                        ) {
                                            Text("完成")
                                        }
                                    }
                                }
                                Divider()
                            }
                        }
                    }
                }
            }

            // One Shot Tasks Section
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
                            Button(onClick = { navController.navigate("addOneShotTask") }) {
                                Text("添加任务")
                            }
                        }

                        if (sortedOneShotTasks.isEmpty()) {
                            Text("暂无一次性任务")
                        } else {
                            sortedOneShotTasks.forEach { task ->
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                                ) {
                                    Column(modifier = Modifier.padding(12.dp)) {
                                        Text(task.name, style = MaterialTheme.typography.titleMedium)
                                        Text(task.description, style = MaterialTheme.typography.bodySmall)
                                        Text("截止: ${task.deadline.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"))}", style = MaterialTheme.typography.bodySmall)

                                        if (task.status == "ACTIVE" && !task.evaluated) {
                                            Slider(
                                                value = task.progress.toFloat(),
                                                onValueChange = { viewModel.updateOneShotProgress(task.id, it.toInt()) },
                                                valueRange = 0f..100f,
                                                modifier = Modifier.fillMaxWidth()
                                            )
                                            Text("进度: ${task.progress}%")
                                            Button(
                                                onClick = { viewModel.evaluateOneShotTask(task.id) },
                                                modifier = Modifier.fillMaxWidth()
                                            ) {
                                                Text("手动评估")
                                            }
                                        } else {
                                            Text(
                                                "状态: ${if (task.status == "COMPLETED") "已完成" else if (task.status == "FAILED") "失败" else "进行中"}",
                                                color = if (task.status == "COMPLETED") Color.Green else Color.Red
                                            )
                                            Text("奖惩: ${task.reward - task.penalty}")
                                        }

                                        IconButton(
                                            onClick = { viewModel.deleteOneShotTask(task) },
                                            modifier = Modifier.align(Alignment.End)
                                        ) {
                                            Icon(Icons.Default.Delete, contentDescription = "删除")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddPeriodicTaskScreen(viewModel: TaskViewModel, navController: NavController) {
    var name by remember { mutableStateOf("") }
    var type by remember { mutableStateOf("DAILY") }
    var dayValue by remember { mutableStateOf(1) }
    var reward by remember { mutableStateOf(10) }
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("添加周期任务") },
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
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("任务名称") },
                modifier = Modifier.fillMaxWidth()
            )

            Row {
                Text("任务类型: ", modifier = Modifier.align(Alignment.CenterVertically))
                Spacer(modifier = Modifier.width(8.dp))
                listOf("DAILY" to "每日", "WEEKLY" to "每周", "MONTHLY" to "每月").forEach { (value, label) ->
                    FilterChip(
                        selected = type == value,
                        onClick = { type = value },
                        label = { Text(label) },
                        modifier = Modifier.padding(end = 8.dp)
                    )
                }
            }

            when (type) {
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
            }

            OutlinedTextField(
                value = reward.toString(),
                onValueChange = { reward = it.toIntOrNull() ?: 10 },
                label = { Text("奖励金额") },
                modifier = Modifier.fillMaxWidth()
            )

            Button(
                /*
                onClick = {
                    if (name.isNotBlank()) {
                        viewModel.addPeriodicTask(name, type, dayValue, reward)
                        scope.launch {
                            snackbarHostState.showSnackbar("添加成功")
                            navController.popBackStack()
                        }
                    }
                },*/
                onClick = {
                    if (name.isNotBlank()) {
                        viewModel.addPeriodicTask(name, type, dayValue, reward)
                        // 设置返回结果
                        navController.previousBackStackEntry?.savedStateHandle?.set("periodic_task_added", true)
                        navController.popBackStack()  // 立即返回
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text("添加")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddOneShotTaskScreen(viewModel: TaskViewModel, navController: NavController) {
    var name by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }

    // 1. 创建 DatePickerState
    val datePickerState = rememberDatePickerState(
        initialSelectedDateMillis = LocalDate.now().plusDays(7)
            .atStartOfDay(ZoneId.systemDefault())
            .toInstant()
            .toEpochMilli()
    )

    // 2. 创建 TimePickerState
    val timePickerState = rememberTimePickerState(
        initialHour = 23,
        initialMinute = 59,
        is24Hour = true
    )

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    // 3. 辅助函数，从state中获取选中的 LocalDateTime
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
                title = { Text("添加一次性任务") },
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
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("任务名称") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text("任务描述") },
                modifier = Modifier.fillMaxWidth()
            )

            Text("截止日期")
            DatePicker(
                state = datePickerState,  // 传入 state
                modifier = Modifier.fillMaxWidth()
            )

            Text("截止时间")
            TimePicker(
                state = timePickerState,  // 传入 state
                modifier = Modifier.fillMaxWidth()
            )

            Button(
                onClick = {
                    if (name.isNotBlank()) {
                        val deadline = getSelectedDateTime()
                        if (deadline != null) {
                            viewModel.addOneShotTask(name, description, deadline)
                            scope.launch {
                                snackbarHostState.showSnackbar("添加成功")
                                navController.popBackStack()
                            }
                        } else {
                            scope.launch {
                                snackbarHostState.showSnackbar("请选择有效的日期")
                            }
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text("添加")
            }
        }
    }
}