package com.example.motiwish.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.DailyMetric
import com.example.motiwish.data.model.OneShotTask
import com.example.motiwish.data.model.PeriodicTask
import com.example.motiwish.data.network.PricingSession
import com.example.motiwish.data.network.TaskOccurrence
import com.example.motiwish.data.network.TaskPayload
import com.example.motiwish.data.model.*
import com.example.motiwish.data.network.TaskApi // 新增
import com.example.motiwish.data.network.TaskCompleteRequest // 新增
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.TaskRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private const val TAG = "TaskViewModel"

class TaskViewModel(
    private val taskRepository: TaskRepository,
    private val currencyRepository: CurrencyRepository,
    private val taskApi: TaskApi // 新增网络依赖
) : ViewModel() {

    // 日常指标
    private val _todayMetric = MutableStateFlow<DailyMetric?>(null)
    val todayMetric: StateFlow<DailyMetric?> = _todayMetric

    // 一次性任务（完全由云端 occurrences 构建）
    private val _oneShotTasks = MutableStateFlow<List<OneShotTask>>(emptyList())
    val oneShotTasks: StateFlow<List<OneShotTask>> = _oneShotTasks

    // 今日周期任务（云端数据驱动）
    private val _todaysPeriodicTasks = MutableStateFlow<List<TodayPeriodicTask>>(emptyList())
    val todaysPeriodicTasks: StateFlow<List<TodayPeriodicTask>> = _todaysPeriodicTasks

    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    // AI定价相关
    private val _pricingSession = MutableStateFlow<PricingSession?>(null)
    val pricingSession: StateFlow<PricingSession?> = _pricingSession

    private val _isPricingLoading = MutableStateFlow(false)
    val isPricingLoading: StateFlow<Boolean> = _isPricingLoading

    private val _pricingError = MutableSharedFlow<String>()
    val pricingError: SharedFlow<String> = _pricingError.asSharedFlow()

    init {
        loadTodayMetric()
        loadTodayOccurrences()     // 从云端加载今日所有任务实例
    }

    // 从云端加载今日任务实例，并更新 UI 状态
    private fun loadTodayOccurrences() {
        viewModelScope.launch {
            val occurrences = taskRepository.getTodayTaskOccurrences()
            updateTodaysPeriodicTasksFromOccurrences(occurrences)
            updateOneShotTasksFromOccurrences(occurrences)
            // 日常指标也可以在这里从 occurrences 中解析（可选）
        }
    }

    // 根据云端实例更新周期任务列表
    private fun updateTodaysPeriodicTasksFromOccurrences(occurrences: List<TaskOccurrence>) {
        val tasks = occurrences
            .filter { it.task.task_type == "recurring" }
            .map { occ ->
                TodayPeriodicTask(
                    id = occ.task.id,
                    name = occ.task.title,
                    rewardAmount = occ.task.reward_primary,
                    completed = occ.status == "completed",
                    pricingStatus = occ.task.pricing_status ?: "applied",
                    description = occ.task.description
                )
            }
        _todaysPeriodicTasks.value = tasks
    }

    // 根据云端实例更新一次性任务列表
    private fun updateOneShotTasksFromOccurrences(occurrences: List<TaskOccurrence>) {
        val oneShotOccurrences = occurrences.filter { it.task.task_type == "one_time" }
        val tasks = oneShotOccurrences.map { occ ->
            OneShotTask(
                id = occ.task.id,
                name = occ.task.title,
                description = occ.task.description ?: "",
                deadline = try {
                    occ.task.due_at?.let {
                        LocalDateTime.parse(it, DateTimeFormatter.ISO_DATE_TIME)
                    } ?: LocalDateTime.parse("${occ.occurrence_date}T00:00:00")
                } catch (e: Exception) {
                    LocalDateTime.now().plusDays(7)
                },
                progress = occ.task.progress_target ?: 0,
                status = when (occ.status) {
                    "completed" -> "COMPLETED"
                    "missed", "cancelled" -> "FAILED"
                    else -> "ACTIVE"
                },
                reward = if (occ.status == "completed") occ.task.reward_primary else 0,
                penalty = if (occ.status in listOf("missed", "cancelled")) occ.task.penalty_primary else 0,
                evaluated = occ.status != "pending",
                estimatedFocusMinutes = occ.task.estimated_focus_minutes,   // 新增
                settlementTrack = occ.task.settlement_track ?: "regular"    // 新增
            )
        }
        _oneShotTasks.value = tasks
    }

    // 进度更新辅助函数
    // 仅更新本地进度（不保存到云端）
    fun updateLocalProgressOnly(taskId: Int, newProgress: Int) {
        val currentTasks = _oneShotTasks.value
        val updatedTasks = currentTasks.map { task ->
            if (task.id == taskId) {
                task.copy(progress = newProgress)
            } else task
        }
        _oneShotTasks.value = updatedTasks
        val afterUpdate = _oneShotTasks.value.find { it.id == taskId }
    }

    // 在滑块松开时调用，保存进度到云端
    fun persistProgress(taskId: Int) {
        viewModelScope.launch {
            // 获取当前本地进度
            val currentTask = _oneShotTasks.value.find { it.id == taskId }
            val progress = currentTask?.progress ?: return@launch
            val success = taskRepository.updateOneShotProgress(taskId, progress)
            if (success) {
                _uiMessage.emit("进度已保存")
                // 从云端刷新一次以确保完全同步
                loadTodayOccurrences()
            } else {
                _uiMessage.emit("保存进度失败")
                // 失败时回滚：重新从云端拉取正确数据
                loadTodayOccurrences()
            }
        }
    }

    // 日常指标：从本地数据库加载（离线缓存）
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
                _uiMessage.emit("今日已评估")
                return@launch
            }
            try {
                val reward = taskRepository.evaluateDailyMetric(metric)
                _todayMetric.value = metric
                if (reward > 0) {
                    currencyRepository.addPrimaryCurrency(reward, "日常任务奖励")
                    _uiMessage.emit("获得 $reward 货币")
                } else if (reward < 0) {
                    currencyRepository.deductPrimaryCurrency(-reward, "日常任务惩罚")
                    _uiMessage.emit("扣除 ${-reward} 货币")
                }
            } catch (e: Exception) {
                _uiMessage.emit("评估失败: ${e.message}")
            }
        }
    }

    // 完成周期任务（使用 TodayPeriodicTask）
    fun completePeriodicTask(task: TodayPeriodicTask) {
        viewModelScope.launch {
            if (task.completed) {
                _uiMessage.emit("今日已完成此任务")
                return@launch
            }
            try {
                val occurrence = taskRepository.completeTaskOccurrence(task.id, LocalDate.now())
                // 根据返回的 occurrence 判断是否获得奖励（status == "completed" 时）
                val reward = if (occurrence.status == "completed") occurrence.task.reward_primary else 0
                if (reward > 0) {
                    currencyRepository.addPrimaryCurrency(reward, "周期任务奖励")
                    _uiMessage.emit("完成周期任务，获得 $reward 一级货币")
                } else {
                    // 可能惩罚或没有奖励
                    _uiMessage.emit("任务已完成，无奖励")
                }
                loadTodayOccurrences()   // 刷新任务状态
            } catch (e: Exception) {
                _uiMessage.emit("完成失败: ${e.message}")
            }
        }
    }

    // 添加周期任务（调用云端 API）
    fun addPeriodicTask(name: String, type: String, dayValue: Int, reward: Int) {
        viewModelScope.launch {
            try {
                // 临时构造一个 PeriodicTask 对象用于传递参数，Repository 内部会转为云端请求
                val task = PeriodicTask(
                    name = name,
                    type = type,
                    dayOfWeek = if (type == "WEEKLY") dayValue else null,
                    dayOfMonth = if (type == "MONTHLY") dayValue else null,
                    rewardAmount = reward
                )
                taskRepository.addPeriodicTask(task)
                _uiMessage.emit("周期任务添加成功")
                loadTodayOccurrences()   // 刷新列表
            } catch (e: Exception) {
                _uiMessage.emit("添加失败: ${e.message}")
            }
        }
    }

    // 删除周期任务（根据 TodayPeriodicTask）
    fun deletePeriodicTask(task: TodayPeriodicTask) {
        viewModelScope.launch {
            try {
                taskRepository.deletePeriodicTaskById(task.id)
                _uiMessage.emit("周期任务已删除")
                loadTodayOccurrences()
            } catch (e: Exception) {
                _uiMessage.emit("删除失败: ${e.message}")
            }
        }
    }

    // 开启定价对话
    fun startTaskPricing(
        taskType: String, // "recurring" or "one_time"
        title: String,
        description: String? = null,
        recurrence: String? = null,       // for recurring
        weekdays: List<Int>? = null,      // for recurring weekly
        monthDays: List<Int>? = null,     // for recurring monthly
        dueAt: LocalDateTime? = null,     // for one_time
        settlementTrack: String = "regular",
        estimatedFocusMinutes: Int? = null
    ) {
        Log.d("TaskViewModel", "startTaskPricing called")
        viewModelScope.launch {
            _isPricingLoading.value = true
            try {
                val payload = TaskPayload(
                    title = title,
                    description = description,
                    task_type = taskType,
                    recurrence = recurrence,
                    settlement_track = settlementTrack,
                    difficulty_level = "medium",
                    estimated_focus_minutes = estimatedFocusMinutes,
                    weekdays = weekdays,
                    month_days = monthDays,
                    due_at = dueAt?.atZone(ZoneId.systemDefault())?.format(DateTimeFormatter.ISO_INSTANT),
                    progress_target = when {
                        taskType == "one_time" && settlementTrack == "exploration" -> 1   // 探索任务初始专注0分钟
                        else -> 100   // 普通一次性任务进度目标100%
                    },
                    tags = listOf("user_created")
                )
                val session = taskRepository.createPricingSession(payload)
                _pricingSession.value = session
            } catch (e: Exception) {
                _pricingError.emit("创建定价会话失败: ${e.message}")
            } finally {
                _isPricingLoading.value = false
            }
        }
    }

    // 清除定价对话
    fun dismissPricingDialog() {
        _pricingSession.value = null
    }

    // 处理定价反馈：接收定价
    fun acceptPricing(sessionId: Int) {
        viewModelScope.launch {
            _isPricingLoading.value = true
            try {
                val updatedSession = taskRepository.submitFeedback(sessionId, "accept")
                if (updatedSession.created_task != null) {
                    loadTodayOccurrences()
                    _uiMessage.emit("任务添加成功")   // 统一消息
                    _pricingSession.value = null    // 清除对话页面
                } else {
                    _pricingError.emit("任务创建失败")
                }
            } catch (e: Exception) {
                _pricingError.emit("接受定价失败: ${e.message}")
            } finally {
                _isPricingLoading.value = false
            }
        }
    }

    // 处理定价反馈：拒绝定价
    fun revisePricing(sessionId: Int, direction: String, feedbackText: String) {
        viewModelScope.launch {
            _isPricingLoading.value = true
            try {
                val updatedSession = taskRepository.submitFeedback(sessionId, "revise", direction, feedbackText)
                _pricingSession.value = updatedSession  // 更新报价信息
            } catch (e: Exception) {
                _pricingError.emit("反馈失败: ${e.message}")
            } finally {
                _isPricingLoading.value = false
            }
        }
    }

    // 添加一次性任务
    fun addOneShotTask(
        name: String,
        description: String,
        deadline: LocalDateTime,
        settlementTrack: String = "regular",
        estimatedFocusMinutes: Int? = null
    ) {
        viewModelScope.launch {
            try {
                val task = OneShotTask(
                    name = name,
                    description = description,
                    deadline = deadline,
                    settlementTrack = settlementTrack,
                    estimatedFocusMinutes = estimatedFocusMinutes
                )
                taskRepository.addOneShotTask(task)
                _uiMessage.emit("一次性任务添加成功")
                loadTodayOccurrences()
            } catch (e: Exception) {
                _uiMessage.emit("添加失败: ${e.message}")
            }
        }
    }

    // 更新一次性任务进度
    fun updateOneShotProgress(taskId: Int, progress: Int) {
        viewModelScope.launch {
            val success = taskRepository.updateOneShotProgress(taskId, progress)
            if (success) {
                loadTodayOccurrences()
            } else {
                _uiMessage.emit("更新进度失败")
            }
        }
    }

    // 更新专注时长进度
    fun updateExplorationProgress(taskId: Int, focusedMinutes: Int) {
        viewModelScope.launch {
            try {
                taskRepository.updateExplorationProgress(taskId, focusedMinutes)
                _uiMessage.emit("专注时长已保存")
                loadTodayOccurrences() // 刷新任务列表
            } catch (e: Exception) {
                _uiMessage.emit("保存失败: ${e.message}")
            }
        }
    }

    // 评估一次性任务
    fun evaluateOneShotTask(taskId: Int) {
        viewModelScope.launch {
            val success = taskRepository.evaluateOneShotTask(taskId)
            if (success) {
                _uiMessage.emit("任务评估成功")
                loadTodayOccurrences()
            } else {
                _uiMessage.emit("评估失败，请稍后重试")
            }
        }
    }

    // 删除一次性任务
    fun deleteOneShotTask(task: OneShotTask) {
        viewModelScope.launch {
            try {
                taskRepository.deleteOneShotTask(task)
                _uiMessage.emit("一次性任务已删除")
                loadTodayOccurrences()
            } catch (e: Exception) {
                _uiMessage.emit("删除失败: ${e.message}")
            }
        }
    }

    // 手动同步所有数据（登录后或下拉刷新）
    fun syncTasksFromRemote() {
        viewModelScope.launch {
            try {
                taskRepository.syncAllTasks()
                loadTodayMetric()
                loadTodayOccurrences()
            } catch (e: Exception) {
                _uiMessage.emit("同步失败：${e.message}")
            }
        }
    }

    fun refreshFromNetwork() {
        viewModelScope.launch {
            taskRepository.syncAllTasks()
            loadTodayOccurrences()
            _uiMessage.emit("数据已同步")
        }
    }
}

// 用于 UI 展示的今日周期任务数据
data class TodayPeriodicTask(
    val id: Int,
    val name: String,
    val rewardAmount: Int,
    val completed: Boolean,
    val pricingStatus: String,  // AI定价状态："pending", "quoted", "applied"
    val description: String? = null
)