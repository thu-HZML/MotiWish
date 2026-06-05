package com.example.motiwish.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.DailyMetric
import com.example.motiwish.data.model.OneShotTask
import com.example.motiwish.data.network.PricingSession
import com.example.motiwish.data.network.TaskOccurrence
import com.example.motiwish.data.network.TaskPayload
import com.example.motiwish.data.model.*
import com.example.motiwish.data.network.CreatePricingSessionRequest
import com.example.motiwish.data.network.FeedbackRequest
import com.example.motiwish.data.network.TaskApi // 新增
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.TaskRepository
import kotlinx.coroutines.Job
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

    // 定价任务草稿管理
    private val _taskDrafts = MutableStateFlow<List<TaskDraft>>(emptyList())
    val taskDrafts: StateFlow<List<TaskDraft>> = _taskDrafts

    // 新增：当前选中的待定价草稿
    private val _selectedDraftForPricing = MutableStateFlow<Pair<Int, PricingSession>?>(null)
    val selectedDraftForPricing: StateFlow<Pair<Int, PricingSession>?> = _selectedDraftForPricing

    // 生成定价草稿临时 ID
    private var nextDraftId = 1

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
                    penaltyAmount = occ.task.penalty_primary,
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
                progressTarget = occ.task.progress_target ?: 0,
                progress = occ.progress ?: 0,
                status = when (occ.status) {
                    "completed" -> "COMPLETED"
                    "missed", "cancelled" -> "FAILED"
                    else -> "ACTIVE"
                },
                reward = occ.task.reward_primary,
                penalty = occ.task.penalty_primary,
                evaluated = occ.status != "pending",
                estimatedFocusMinutes = occ.task.estimated_focus_minutes,   // 新增
                settlementTrack = occ.task.settlement_track ?: "regular",    // 新增
                actualReward = occ.settlement_details?.reward_primary,       // 实际获得奖励
                actualPenalty = occ.settlement_details?.penalty_primary      // 实际获得惩罚
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
            val currentTask = _oneShotTasks.value.find { it.id == taskId } ?: return@launch
            val progress = currentTask.progress
            val success = taskRepository.updateOneShotProgress(taskId, progress)
            if (success) {
                _uiMessage.emit("进度已保存")
                // 如果是 regular 任务且进度 >= 100 且尚未完成，自动调用结算
                if (currentTask.settlementTrack == "regular" && progress >= 100 && currentTask.status != "COMPLETED") {
                    autoCompleteRegularTask(taskId, progress)
                } else {
                    loadTodayOccurrences()
                }
            } else {
                _uiMessage.emit("保存进度失败")
                loadTodayOccurrences()
            }
        }
    }

    // 新增：自动完成 regular 一次性任务
    private suspend fun autoCompleteRegularTask(taskId: Int, progress: Int) {
        try {
            val occurrence = taskRepository.completeOneShotTask(taskId, progress)
            val reward = if (occurrence.status == "completed") occurrence.task.reward_primary else 0
            if (reward > 0) {
                _uiMessage.emit("任务完成！获得 $reward 货币")
            } else {
                _uiMessage.emit("任务已完成，未获得奖励")
            }
            loadTodayOccurrences()
        } catch (e: Exception) {
            _uiMessage.emit("自动完成失败: ${e.message}")
            loadTodayOccurrences()
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
            val oldMetric = _todayMetric.value ?: return@launch
            val updatedMetric = oldMetric.copy(
                wakeUpTime = wakeUpTime,
                sleepTime = sleepTime,
                phoneUsageMinutes = phoneUsage,
                waterCups = waterCups
            )
            taskRepository.saveDailyMetric(updatedMetric)
            _todayMetric.value = updatedMetric
        }
    }

    // 【修改点】：目前后端的 OpenAPI 文档中没有专门结算 DailyMetric 的端点，
    // 这里我们先暂时仅做本地评估，或者通过通知服务器完成特定任务（需要跟后端确认）
    fun evaluateDailyMetric() {
        viewModelScope.launch {
            val oldMetric = _todayMetric.value ?: return@launch
            if (oldMetric.evaluated) {
                _uiMessage.emit("今日已评估")
                return@launch
            }
            try {
                val reward = taskRepository.evaluateDailyMetric(oldMetric)
                val updatedMetric = oldMetric.copy(evaluated = true, reward = reward)
                _todayMetric.value = updatedMetric
                _uiMessage.emit("获得 $reward 货币")
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

    // 异步开启定价对话
    fun createTaskDraftAsync(
        taskType: String,
        title: String,
        description: String? = null,
        recurrence: String? = null,
        weekdays: List<Int>? = null,
        monthDays: List<Int>? = null,
        dueAt: LocalDateTime? = null,
        settlementTrack: String = "regular",
        estimatedFocusMinutes: Int? = null
    ) {
        val draftId = nextDraftId++
        // 立即添加本地草稿，状态为 "pricing"
        val draft = TaskDraft(
            id = draftId,
            sessionId = null,
            title = title,
            description = description,
            taskType = taskType,
            recurrence = recurrence,
            weekdays = weekdays,
            monthDays = monthDays,
            dueAt = dueAt,
            settlementTrack = settlementTrack,
            estimatedFocusMinutes = estimatedFocusMinutes,
            status = "pricing",
            quotePayload = null,
            createdAt = System.currentTimeMillis()
        )
        _taskDrafts.value = _taskDrafts.value + draft

        // 异步执行网络请求（不阻塞 UI）
        viewModelScope.launch {
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
                        taskType == "one_time" && settlementTrack == "exploration" -> estimatedFocusMinutes ?: 1
                        taskType == "one_time" -> 100
                        else -> null
                    },
                    tags = listOf("user_created")
                )
                val response = taskApi.createPricingSession(CreatePricingSessionRequest(payload))
                if (response.success) {
                    val session = response.data
                    // 更新草稿：填入 sessionId 和 quotePayload，状态改为 "quoted"
                    _taskDrafts.value = _taskDrafts.value.map {
                        if (it.id == draftId) {
                            it.copy(
                                sessionId = session.id,
                                status = "quoted",
                                quotePayload = session.quote_payload
                            )
                        } else it
                    }
                    _uiMessage.emit("任务定价完成")
                } else {
                    // 定价失败，移除草稿
                    _taskDrafts.value = _taskDrafts.value.filter { it.id != draftId }
                    _uiMessage.emit("定价失败: ${response.message}")
                }
            } catch (e: Exception) {
                _taskDrafts.value = _taskDrafts.value.filter { it.id != draftId }
                _uiMessage.emit("网络错误: ${e.message}")
            }
        }
    }

    // 展示定价对话框（仅当任务状态为 quoted）
    fun showPricingDialog(draftId: Int) {
        Log.d("PricingDialog", "showPricingDialog called with draftId=$draftId")
        val draft = _taskDrafts.value.find { it.id == draftId }
        Log.d("PricingDialog", "Found draft: $draft")
        if (draft?.status == "quoted" && draft.quotePayload != null && draft.sessionId != null) {
            Log.d("PricingDialog", "Conditions met, building tempSession")
            // 构建临时 TaskPayload，仅用于填充数据类
            val tempTaskPayload = TaskPayload(
                title = draft.title,
                description = draft.description,
                task_type = draft.taskType,
                recurrence = draft.recurrence,
                settlement_track = draft.settlementTrack,
                difficulty_level = "medium",
                estimated_focus_minutes = draft.estimatedFocusMinutes,
                weekdays = draft.weekdays,
                month_days = draft.monthDays,
                due_at = draft.dueAt?.atZone(ZoneId.systemDefault())?.format(DateTimeFormatter.ISO_INSTANT),
                progress_target = when {
                    draft.taskType == "one_time" && draft.settlementTrack == "exploration" -> draft.estimatedFocusMinutes ?: 1
                    draft.taskType == "one_time" -> 100
                    else -> null
                },
                tags = listOf("user_created")
            )
            val tempSession = PricingSession(
                id = draft.sessionId,
                status = "waiting_feedback",
                task_payload = tempTaskPayload,
                quote_payload = draft.quotePayload,
                feedback_history = null,
                created_task = null
            )
            _selectedDraftForPricing.value = Pair(draftId, tempSession)
        } else {
            Log.w("PricingDialog", "Conditions not met: status=${draft?.status}, quotePayload=${draft?.quotePayload}, sessionId=${draft?.sessionId}")
        }
    }

    // 清除定价对话
    fun dismissPricingDialog() {
        _selectedDraftForPricing.value = null
    }

    // 接受定价并创建正式任务
    fun acceptPricingAndCreate(draftId: Int) {
        viewModelScope.launch {
            val draft = _taskDrafts.value.find { it.id == draftId }
            if (draft == null || draft.sessionId == null) {
                _uiMessage.emit("草稿不存在，请重试")
                dismissPricingDialog()
                return@launch
            }
            // 关闭对话框（可选立即关闭）
            dismissPricingDialog()
            try {
                val updatedSession = taskRepository.submitFeedback(draft.sessionId, "accept")
                if (updatedSession.created_task != null) {
                    _taskDrafts.value = _taskDrafts.value.filter { it.id != draftId }
                    loadTodayOccurrences()
                    _uiMessage.emit("任务创建成功")
                } else {
                    _uiMessage.emit("任务创建失败")
                }
            } catch (e: Exception) {
                _uiMessage.emit("接受定价失败: ${e.message}")
            } finally {
                // 确保对话框已关闭（如果上面没有调用）
                dismissPricingDialog()
            }
        }
    }

    // 用户反馈：拒绝定价（异步）
    fun revisePricing(draftId: Int, direction: String, feedbackText: String) {
        // 1. 立即关闭对话框
        dismissPricingDialog()

        // 2. 找到对应的草稿
        val draft = _taskDrafts.value.find { it.id == draftId }
        if (draft == null) {
            return
        }

        // 3. 立即更新状态为 "repricing"
        _taskDrafts.value = _taskDrafts.value.map {
            if (it.id == draftId) it.copy(status = "repricing") else it
        }

        // 4. 异步提交反馈（不阻塞 UI）
        viewModelScope.launch {
            try {
                val updatedSession = taskRepository.submitFeedback(draft.sessionId!!, "revise", direction, feedbackText)
                // 5. 成功后更新草稿状态为 "quoted" 并保存新报价
                _taskDrafts.value = _taskDrafts.value.map {
                    if (it.id == draftId) {
                        it.copy(
                            status = "quoted",
                            quotePayload = updatedSession.quote_payload
                        )
                    } else it
                }
                _uiMessage.emit("重新定价完成，请点击查看")
            } catch (e: Exception) {
                // 失败时回滚到 quoted 状态（保留原报价）或标记为 failed
                _taskDrafts.value = _taskDrafts.value.map {
                    if (it.id == draftId) it.copy(status = "quoted") else it
                }
                _uiMessage.emit("重新定价失败: ${e.message}")
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

    // 手动完成一次性任务（用户点击按钮触发）
    fun manuallyCompleteOneShotTask(taskId: Int) {
        viewModelScope.launch {
            val task = _oneShotTasks.value.find { it.id == taskId }
            if (task == null) {
                _uiMessage.emit("任务不存在")
                return@launch
            }
            val progress = task.progress  // 当前进度
            try {
                val occurrence = taskRepository.completeOneShotTask(taskId, progress)
                val reward = if (occurrence.status == "completed") occurrence.task.reward_primary else 0
                if (reward > 0) {
                    _uiMessage.emit("手动结算完成，获得 $reward 货币")
                } else {
                    _uiMessage.emit("结算完成，未获得奖励")
                }
                loadTodayOccurrences()
            } catch (e: Exception) {
                _uiMessage.emit("手动结算失败: ${e.message}")
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
                //taskRepository.syncAllTasks()
                loadTodayMetric()
                loadTodayOccurrences()
            } catch (e: Exception) {
                _uiMessage.emit("同步失败：${e.message}")
            }
        }
    }
}

// 用于 UI 展示的今日周期任务数据
data class TodayPeriodicTask(
    val id: Int,
    val name: String,
    val rewardAmount: Int,
    val penaltyAmount: Int,
    val completed: Boolean,
    val pricingStatus: String,  // AI定价状态："pending", "quoted", "applied"
    val description: String? = null
)