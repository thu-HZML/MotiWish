package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.*
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
    private val currencyRepository: CurrencyRepository
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

    fun evaluateDailyMetric() {
        viewModelScope.launch {
            val metric = _todayMetric.value ?: return@launch
            if (metric.evaluated) {
                _uiMessage.emit("今日日常任务已经评估过了")
                return@launch
            }
            var reward = 0
            val wakeTime = LocalTime.parse(metric.wakeUpTime)
            if (wakeTime.isBefore(LocalTime.of(8, 0))) reward += 10
            val sleepTime = LocalTime.parse(metric.sleepTime)
            if (sleepTime.isBefore(LocalTime.of(23, 0))) reward += 10
            if (metric.phoneUsageMinutes <= 300) reward += 15
            else if (metric.phoneUsageMinutes > 500) reward -= 5
            if (metric.waterCups >= 8) reward += 15
            else if (metric.waterCups < 4) reward -= 5
            metric.reward = reward
            metric.evaluated = true
            taskRepository.saveDailyMetric(metric)
            if (reward > 0) {
                currencyRepository.addPrimaryCurrency(reward, "日常任务奖励")
                _uiMessage.emit("获得 $reward 一级货币！")
            } else if (reward < 0) {
                currencyRepository.deductPrimaryCurrency(-reward, "日常任务惩罚")
                _uiMessage.emit("被扣除 ${-reward} 一级货币")
            } else {
                _uiMessage.emit("日常任务完成，无奖惩")
            }
            _todayMetric.value = metric
        }
    }

    fun completePeriodicTask(task: PeriodicTask) {
        viewModelScope.launch {
            val today = LocalDate.now()
            if (taskRepository.isPeriodicTaskCompletedToday(task.id, today)) {
                _uiMessage.emit("今日已完成此任务")
                return@launch
            }
            taskRepository.completePeriodicTask(task.id, today, task.rewardAmount)
            currencyRepository.addPrimaryCurrency(task.rewardAmount, "周期任务奖励")
            _uiMessage.emit("完成周期任务，获得 ${task.rewardAmount} 一级货币")
            loadTodaysPeriodicTasks()
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

    fun evaluateOneShotTask(taskId: Int) {
        viewModelScope.launch {
            val task = taskRepository.getOneShotTaskById(taskId) ?: return@launch
            if (task.evaluated) {
                _uiMessage.emit("任务已评估过")
                return@launch
            }
            val now = LocalDateTime.now()
            val isCompleted = task.progress >= 100
            val isOverdue = now.isAfter(task.deadline)
            var reward = 0
            var penalty = 0
            if (isCompleted) {
                task.status = "COMPLETED"
                val hoursEarly = if (!isOverdue) ChronoUnit.HOURS.between(now, task.deadline).coerceAtLeast(0) else 0
                reward = (50 + hoursEarly / 2).toInt().coerceAtMost(200)
                currencyRepository.addPrimaryCurrency(reward, "一次性任务奖励")
                _uiMessage.emit("任务完成！获得 $reward 一级货币")
            } else if (isOverdue && task.progress < 100) {
                task.status = "FAILED"
                penalty = 30
                currencyRepository.deductPrimaryCurrency(penalty, "一次性任务失败惩罚")
                _uiMessage.emit("任务超时未完成，扣除 $penalty 一级货币")
            }
            task.reward = reward
            task.penalty = penalty
            task.evaluated = true
            taskRepository.updateOneShotTask(task)
        }
    }

    fun deleteOneShotTask(task: OneShotTask) {
        viewModelScope.launch {
            taskRepository.deleteOneShotTask(task)
            _uiMessage.emit("一次性任务已删除")
        }
    }
}