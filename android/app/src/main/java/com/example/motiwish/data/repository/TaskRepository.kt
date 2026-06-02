// TaskRepository.kt
package com.example.motiwish.data.repository

import android.util.Log
import com.example.motiwish.data.database.TaskDao
import com.example.motiwish.data.model.*
import com.example.motiwish.data.network.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

class TaskRepository(
    private val taskDao: TaskDao,
    private val taskApi: TaskApi          // 新增网络 API
) {

    // ---------- 同步：从云端拉取所有任务，更新本地数据库 ----------
    suspend fun syncAllTasks() {
        try {
            var currentPage = 1
            var hasMore = true
            val allRemoteTasks = mutableListOf<RemoteTask>()

            while (hasMore) {
                val response = taskApi.getTasks(currentPage)
                Log.d("TaskRepository", "Page $currentPage response: success=, results size=${response.results?.size}")
                val items = response.results ?: emptyList()
                if (items.isNotEmpty()) {
                    val tasks = items.flatMap { it.data }
                    allRemoteTasks.addAll(tasks)
                    Log.d("TaskRepository", "Added ${tasks.size} tasks, total now ${allRemoteTasks.size}")
                }
                hasMore = response.next != null
                currentPage++
            }

            Log.d("TaskRepository", "Fetched ${allRemoteTasks.size} remote tasks")
            convertAndSaveRemoteTasks(allRemoteTasks)
        } catch (e: Exception) {
            Log.e("TaskRepository", "syncAllTasks error", e)
        }
    }

    // 将云端任务转换为本地实体
    private suspend fun convertAndSaveRemoteTasks(remoteTasks: List<RemoteTask>) {
        for (remote in remoteTasks) {
            when (remote.task_type) {
                "daily", "weekly", "monthly" -> {
                    val type = remote.task_type.uppercase()
                    val dayOfWeek = if (type == "WEEKLY" && !remote.weekdays.isNullOrEmpty()) {
                        // 假设后端 weekdays 中 1=周一，与 LocalDate 的 dayOfWeek.value (1=周一) 一致
                        remote.weekdays[0]
                    } else null
                    val dayOfMonth = if (type == "MONTHLY" && !remote.month_days.isNullOrEmpty()) {
                        remote.month_days[0]
                    } else null

                    val periodic = PeriodicTask(
                        id = remote.id,
                        name = remote.title,
                        type = type,
                        dayOfWeek = dayOfWeek,
                        dayOfMonth = dayOfMonth,
                        rewardAmount = remote.reward_primary,
                        active = remote.status == "active"
                    )
                    taskDao.insertPeriodicTask(periodic)
                }
                "one_time" -> {
                    val deadline = remote.due_at?.let {
                        LocalDateTime.parse(it, DateTimeFormatter.ISO_DATE_TIME)
                    } ?: LocalDateTime.now().plusDays(7)

                    val status = when (remote.status) {
                        "active" -> "ACTIVE"
                        "completed" -> "COMPLETED"
                        "failed" -> "FAILED"
                        else -> "ACTIVE"
                    }

                    val oneShot = OneShotTask(
                        id = remote.id,
                        name = remote.title,
                        description = remote.description ?: "",
                        deadline = deadline,
                        progress = remote.progress_target ?: 0,
                        status = status,
                        reward = if (status == "COMPLETED") remote.reward_primary else 0,
                        penalty = if (status == "FAILED") remote.penalty_primary else 0,
                        evaluated = status != "ACTIVE"
                    )
                    taskDao.insertOneShotTask(oneShot)
                }
                "metric" -> {
                    // 处理日常指标任务（起床时间、喝水等）
                    if (remote.metric_key != null) {
                        updateDailyMetricFromRemote(remote)
                    }
                }
                // 其他类型忽略
            }
        }
    }

    private suspend fun updateDailyMetricFromRemote(remote: RemoteTask) {
        val today = LocalDate.now()
        var metric = taskDao.getDailyMetricByDate(today)
        if (metric == null) {
            metric = DailyMetric(date = today)
        }
        when (remote.metric_key) {
            "wake_up_time" -> metric.wakeUpTime = remote.target_value?.toString() ?: ""
            "sleep_time" -> metric.sleepTime = remote.target_value?.toString() ?: ""
            "phone_usage_minutes" -> metric.phoneUsageMinutes = remote.target_value ?: 0
            "water_cups" -> metric.waterCups = remote.target_value ?: 0
        }
        if (remote.status == "completed") {
            metric.evaluated = true
            metric.reward = remote.reward_primary
        }
        if (metric.id == 0) taskDao.insertDailyMetric(metric)
        else taskDao.updateDailyMetric(metric)
    }

    // ---------- 日常指标 ----------
    suspend fun getDailyMetricByDate(date: LocalDate): DailyMetric? {
        // 先尝试从本地读取，同时后台同步一次（可选）
        return taskDao.getDailyMetricByDate(date)
    }

    suspend fun saveDailyMetric(metric: DailyMetric) {
        // 注意：日常指标通常不需要单独上传，因为评估时会整体发送
        if (metric.id == 0) taskDao.insertDailyMetric(metric)
        else taskDao.updateDailyMetric(metric)
    }

    fun getAllDailyMetrics(): Flow<List<DailyMetric>> = taskDao.getAllDailyMetrics()

    // 评估日常指标（调用 API）
    suspend fun evaluateDailyMetric(metric: DailyMetric): Int {
        val request = EvaluateDailyMetricRequest(
            wake_up_time = metric.wakeUpTime,
            sleep_time = metric.sleepTime,
            phone_usage_minutes = metric.phoneUsageMinutes,
            water_cups = metric.waterCups
        )
        val response = taskApi.evaluateDailyMetric(request)
        if (response.success) {
            metric.evaluated = true
            metric.reward = response.reward
            saveDailyMetric(metric)
            return response.reward
        } else {
            throw Exception(response.message)
        }
    }

    // ---------- 周期任务 ----------
    fun getAllActivePeriodicTasks(): Flow<List<PeriodicTask>> = taskDao.getAllActivePeriodicTasks()

    suspend fun addPeriodicTask(task: PeriodicTask): PeriodicTask {
        // 映射周期任务的 task_type 和 recurrence
        val taskType = "recurring"
        val recurrence = when (task.type) {
            "DAILY" -> "daily"
            "WEEKLY" -> "weekly"
            "MONTHLY" -> "monthly"
            else -> "none"
        }
        val weekdays = if (task.type == "WEEKLY" && task.dayOfWeek != null) {
            // 后端 weekdays 使用 0=周一，需要将 dayOfWeek（1=周一）转换
            listOf(task.dayOfWeek - 1)
        } else null
        val monthDays = if (task.type == "MONTHLY" && task.dayOfMonth != null) {
            listOf(task.dayOfMonth)
        } else null

        val request = CreateTaskRequest(
            title = task.name,
            description = null,
            task_type = taskType,
            recurrence = recurrence,
            settlement_track = "regular",   // 默认常规轨道
            difficulty_level = "medium",    // 可配置
            estimated_focus_minutes = null,
            weekdays = weekdays,
            month_days = monthDays,
            metric_key = null,
            target_value = null,
            progress_target = null,
            reward_primary = null,
            penalty_primary = null,
            starts_on = null,
            ends_on = null,
            due_at = null,
            status = "active",
            tags = null,
            ai_metadata = null
        )

        val response = taskApi.createTask(request)
        if (response.success) {
            val remoteTask = response.data
            val newTask = task.copy(
                id = remoteTask.id,
                rewardAmount = remoteTask.reward_primary
            )
            taskDao.insertPeriodicTask(newTask)
            return newTask
        } else {
            throw Exception(response.message)
        }
    }

    suspend fun deletePeriodicTask(task: PeriodicTask) {
        try {
            val response = taskApi.deleteTask(task.id)
            if (response.isSuccessful) {
                taskDao.deletePeriodicTask(task)   // API 成功，删除本地
            } else {
                throw Exception("删除失败: ${response.code()}")
            }
        } catch (e: Exception) {
            // 网络失败或后端错误，抛出让 ViewModel 处理
            throw Exception("删除周期任务失败: ${e.message}")
        }
    }

    suspend fun isPeriodicTaskCompletedToday(taskId: Int, date: LocalDate): Boolean {
        return taskDao.getPeriodicTaskCompletion(taskId, date) != null
    }

    fun getAllPeriodicTaskCompletions(): Flow<List<PeriodicTaskCompletion>> = taskDao.getAllPeriodicTaskCompletions()

    suspend fun getPeriodicTaskById(id: Int): PeriodicTask? = taskDao.getPeriodicTaskById(id)

    // ---------- 一次性任务 ----------
    fun getAllOneShotTasks(): Flow<List<OneShotTask>> = taskDao.getAllOneShotTasks()

    suspend fun addOneShotTask(task: OneShotTask): OneShotTask {
        val request = CreateTaskRequest(
            title = task.name,
            description = task.description,
            task_type = "one_time",
            recurrence = null,
            settlement_track = task.settlementTrack,
            difficulty_level = "medium",
            estimated_focus_minutes = task.estimatedFocusMinutes,
            weekdays = null,
            month_days = null,
            metric_key = null,
            target_value = null,
            progress_target = task.progress,   // 当前进度（通常为0）
            reward_primary = null,                // 让后端定价，或设置默认值
            penalty_primary = null,
            starts_on = null,
            ends_on = null,
            due_at = task.deadline.toString(), // 需要格式化为 ISO 8601，如 "2026-05-30T23:59:59Z"
            status = "active",
            tags = null,
            ai_metadata = null
        )

        val response = taskApi.createTask(request)
        if (response.success) {
            val remoteTask = response.data
            val newTask = task.copy(
                id = remoteTask.id,
                reward = remoteTask.reward_primary,
                penalty = remoteTask.penalty_primary
            )
            taskDao.insertOneShotTask(newTask)
            return newTask
        } else {
            throw Exception(response.message)
        }
    }

    suspend fun updateOneShotTask(task: OneShotTask) {
        // 本地更新不需要立即同步，进度更新有专门的 API
        taskDao.updateOneShotTask(task)
    }

    // 更新专注时长进度
    suspend fun updateExplorationProgress(taskId: Int, focusedMinutes: Int): Boolean {
        return try {
            // 假设后端接受 PATCH /api/v1/tasks/tasks/{id}/ 更新 progress 字段
            val request = PartialUpdateTaskRequest(progress_target = focusedMinutes)
            taskApi.partialUpdateTask(taskId, request)
            true
        } catch (e: Exception) {
            false
        }
    }

    suspend fun deleteOneShotTask(task: OneShotTask) {
        try {
            val response = taskApi.deleteTask(task.id)
            if (response.isSuccessful) {
                taskDao.deleteOneShotTask(task)
            } else {
                throw Exception("删除失败: ${response.code()}")
            }
        } catch (e: Exception) {
            throw Exception("删除一次性任务失败: ${e.message}")
        }
    }

    suspend fun getOneShotTaskById(id: Int): OneShotTask? = taskDao.getOneShotTaskById(id)

    // 更新一次性任务进度（调用 API）
    suspend fun updateOneShotProgress(taskId: Int, progress: Int): Boolean {
        return try {
            val request = PartialUpdateTaskRequest(progress_target = progress)
            val updatedTask = taskApi.partialUpdateTask(taskId, request)
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    suspend fun evaluateOneShotTask(taskId: Int): Boolean {
        return try {
            taskApi.evaluateOneShotTask(taskId)
            // 评估后重新从云端拉取该任务的最新状态并更新本地
            syncAllTasks()   // 简单粗暴：全量同步。也可以单独拉取一个任务，但为了简便先这样
            true
        } catch (e: Exception) {
            false
        }
    }

    // 获取任务历史记录
    suspend fun getTaskHistory(): List<TaskOccurrence> {
        return try {
            val response = taskApi.getTaskHistory()
            if (response.success) {
                response.data
            } else {
                throw Exception(response.message)
            }
        } catch (e: Exception) {
            // 网络失败时返回空列表，UI 会显示空状态
            emptyList()
        }
    }

    // 获取今天的任务列表
    suspend fun getTodayTaskOccurrences(date: LocalDate? = null): List<TaskOccurrence> {
        return try {
            val dateStr = date?.toString()
            val response = taskApi.getTodayTasks(dateStr)
            if (response.success) {
                response.data
            } else {
                throw Exception(response.message)
            }
        } catch (e: Exception) {
            // 网络失败时返回空列表，UI 会显示无任务
            emptyList()
        }
    }

    // 删除周期任务
    suspend fun deletePeriodicTaskById(taskId: Int) {
        val response = taskApi.deleteTask(taskId)
        if (!response.isSuccessful) throw Exception("删除失败")
    }

    /**
     * 完成并结算任务实例
     * @param taskId 任务ID
     * @param occurrenceDate 日期，默认为今天
     * @param progress 进度值（可选，不传则使用任务的 progress_target）
     * @return 结算后的 TaskOccurrence
     */
    suspend fun completeTaskOccurrence(
        taskId: Int,
        occurrenceDate: LocalDate = LocalDate.now(),
        progress: Int? = null
    ): TaskOccurrence {
        val request = CompleteTaskRequest(
            occurrence_date = occurrenceDate.toString(),
            progress = progress
        )
        val response = taskApi.completeTask(taskId, request)
        if (response.success) {
            return response.data
        } else {
            throw Exception(response.message)
        }
    }

    // 创建AI定价对话
    suspend fun createPricingSession(payload: TaskPayload): PricingSession {
        val response = taskApi.createPricingSession(CreatePricingSessionRequest(payload))
        if (!response.success) throw Exception(response.message)
        return response.data
    }

    // 提交定价反馈
    suspend fun submitFeedback(sessionId: Int, action: String, direction: String? = null, text: String? = null): PricingSession {
        val request = FeedbackRequest(action, direction, text)
        val response = taskApi.submitFeedback(sessionId, request)
        if (!response.success) throw Exception(response.message)
        return response.data
    }
}