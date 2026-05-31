package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.*
import com.example.motiwish.data.network.TaskApi // 新增
import com.example.motiwish.data.network.TaskCompleteRequest // 新增
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.TaskRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.temporal.ChronoUnit

class TaskViewModel(
    private val taskRepository: TaskRepository,
    private val currencyRepository: CurrencyRepository,
    private val taskApi: TaskApi // 新增网络依赖
) : ViewModel() {
    private val _todayMetric = MutableStateFlow<DailyMetric?>(null)
    val todayMetric: StateFlow<DailyMetric?> = _todayMetric
    private val _periodicTasks = MutableStateFlow<List<PeriodicTask>>(emptyList())
    val periodicTasks: StateFlow<List<PeriodicTask>> = _periodicTasks
    private val _oneShotTasks = MutableStateFlow<List<OneShotTask>>(emptyList())
    val oneShotTasks: StateFlow<List<OneShotTask>> = _oneShotTasks
    private val _todaysPeriodicTasks = MutableStateFlow<List<Pair<PeriodicTask, Boolean>>>(emptyList())
    val todaysPeriodicTasks: StateFlow<List<Pair<PeriodicTask, Boolean>>> = _todaysPeriodicTasks
    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    init {
        loadTodayMetric()
        loadPeriodicTasks()
        loadOneShotTasks()
        loadTodaysPeriodicTasks()
    }

    private fun loadTodayMetric() {
        viewModelScope.launch {
            val today = LocalDate.now()
            var metric = taskRepository.getDailyMetricByDate(today)
            if (metric == null) {
                metric = DailyMetric(date = today, wakeUpTime = "", sleepTime = "", phoneUsageMinutes = 0, waterCups = 0)
                taskRepository.saveDailyMetric(metric)
            }
            _todayMetric.value = metric
        }
    }

    private fun loadPeriodicTasks() {
        taskRepository.getAllActivePeriodicTasks().onEach {
            _periodicTasks.value = it
            loadTodaysPeriodicTasks()
        }.launchIn(viewModelScope)
    }

    private fun loadOneShotTasks() {
        taskRepository.getAllOneShotTasks().onEach {
            _oneShotTasks.value = it
        }.launchIn(viewModelScope)
    }

    private fun loadTodaysPeriodicTasks() {
        viewModelScope.launch {
            val today = LocalDate.now()
            val tasks = _periodicTasks.value.filter { task ->
                when (task.type) {
                    "DAILY" -> true
                    "WEEKLY" -> task.dayOfWeek == today.dayOfWeek.value
                    "MONTHLY" -> task.dayOfMonth == today.dayOfMonth
                    else -> false
                }
            }
            val tasksWithCompletion = tasks.map { task ->
                task to taskRepository.isPeriodicTaskCompletedToday(task.id, today)
            }
            _todaysPeriodicTasks.value = tasksWithCompletion
        }
    }

    fun updateDailyMetric(wakeUpTime: String, sleepTime: String, phoneUsage: Int, waterCups: Int) {
        viewModelScope.launch {
            val metric = _todayMetric.value ?: return@launch
            metric.wakeUpTime = wakeUpTime
            metric.sleepTime = sleepTime
            metric.phoneUsageMinutes = phoneUsage
            metric.waterCups = waterCups
            taskRepository.saveDailyMetric(metric)
            _todayMetric.value = metric
        }
    }

    // 【修改点】：目前后端的 OpenAPI 文档中没有专门结算 DailyMetric 的端点，
    // 这里我们先暂时仅做本地评估，或者通过通知服务器完成特定任务（需要跟后端确认）
    fun evaluateDailyMetric() {
        viewModelScope.launch {
            val metric = _todayMetric.value ?: return@launch
            if (metric.evaluated) {
                _uiMessage.emit("今日日常任务已经评估过了")
                return@launch
            }

            // 提醒：在真正的联机状态下，这里的奖惩逻辑应交由服务器的 /ai/report-jobs/ 或专用端点处理
            // 这里仅做 UI 提示，不再调用已经不存在的 addPrimaryCurrency
            _uiMessage.emit("日常记录已保存，等待服务器统一结算。")
            metric.evaluated = true
            taskRepository.saveDailyMetric(metric)
            _todayMetric.value = metric
        }
    }

    // 【修改点】：调用网络接口完成任务
    fun completePeriodicTask(task: PeriodicTask) {
        viewModelScope.launch {
            val today = LocalDate.now()
            if (taskRepository.isPeriodicTaskCompletedToday(task.id, today)) {
                _uiMessage.emit("今日已完成此任务")
                return@launch
            }

            try {
                // 1. 发送给服务器进行真实结算
                val response = taskApi.completeTask(task.id, TaskCompleteRequest())

                if (response.success) {
                    // 2. 更新本地状态并刷新服务器钱包
                    taskRepository.completePeriodicTask(task.id, today, task.rewardAmount)
                    currencyRepository.refreshWalletFromServer()
                    _uiMessage.emit("完成周期任务！")
                    loadTodaysPeriodicTasks()
                } else {
                    _uiMessage.emit(response.message ?: "任务提交失败")
                }
            } catch (e: Exception) {
                _uiMessage.emit("网络连接失败，请稍后重试")
            }
        }
    }

    fun addPeriodicTask(name: String, type: String, dayValue: Int, reward: Int) {
        viewModelScope.launch {
            val task = PeriodicTask(name = name, type = type, dayOfWeek = if (type == "WEEKLY") dayValue else null, dayOfMonth = if (type == "MONTHLY") dayValue else null, rewardAmount = reward)
            taskRepository.addPeriodicTask(task)
            _uiMessage.emit("周期任务添加成功")
        }
    }

    fun deletePeriodicTask(task: PeriodicTask) {
        viewModelScope.launch {
            taskRepository.deletePeriodicTask(task)
            _uiMessage.emit("周期任务已删除")
        }
    }

    fun addOneShotTask(name: String, description: String, deadline: LocalDateTime) {
        viewModelScope.launch {
            val task = OneShotTask(name = name, description = description, deadline = deadline)
            taskRepository.addOneShotTask(task)
            _uiMessage.emit("一次性任务添加成功")
        }
    }

    fun updateOneShotProgress(taskId: Int, progress: Int) {
        viewModelScope.launch {
            val task = taskRepository.getOneShotTaskById(taskId) ?: return@launch
            task.progress = progress
            if (progress >= 100 && task.status == "ACTIVE") evaluateOneShotTask(taskId)
            else taskRepository.updateOneShotTask(task)
        }
    }

    // 【修改点】：调用网络接口完成一次性任务
    fun evaluateOneShotTask(taskId: Int) {
        viewModelScope.launch {
            val task = taskRepository.getOneShotTaskById(taskId) ?: return@launch
            if (task.evaluated) {
                _uiMessage.emit("任务已评估过")
                return@launch
            }

            val isCompleted = task.progress >= 100

            if (isCompleted) {
                try {
                    val response = taskApi.completeTask(task.id, TaskCompleteRequest())
                    if (response.success) {
                        task.status = "COMPLETED"
                        task.evaluated = true
                        taskRepository.updateOneShotTask(task)
                        currencyRepository.refreshWalletFromServer()
                        _uiMessage.emit("任务完成！")
                    } else {
                        _uiMessage.emit(response.message ?: "提交失败")
                    }
                } catch (e: Exception) {
                    _uiMessage.emit("网络连接失败，请稍后重试")
                }
            } else {
                val now = LocalDateTime.now()
                val isOverdue = now.isAfter(task.deadline)
                if (isOverdue) {
                    task.status = "FAILED"
                    task.evaluated = true
                    taskRepository.updateOneShotTask(task)
                    _uiMessage.emit("任务超时已失败，等待服务器结算。")
                }
            }
        }
    }

    fun deleteOneShotTask(task: OneShotTask) {
        viewModelScope.launch {
            taskRepository.deleteOneShotTask(task)
            _uiMessage.emit("一次性任务已删除")
        }
    }
}