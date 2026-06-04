// TaskRepository.kt
package com.example.motiwish.data.repository

import android.util.Log
import com.example.motiwish.data.database.TaskDao
import com.example.motiwish.data.model.*
import com.example.motiwish.data.network.*
import com.google.gson.GsonBuilder
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

class TaskRepository(
    private val taskDao: TaskDao,
    private val taskApi: TaskApi          // 新增网络 API
) {
    /**
     * 从云端获取所有活跃任务（包括周期和一次性）
     */
    suspend fun fetchAllActiveTasksFromCloud(): List<RemoteTask> {
        var page = 1
        val allTasks = mutableListOf<RemoteTask>()
        while (true) {
            val response = taskApi.getTasks(page)

            // 检查顶层 success
            if (!response.success) {
                break
            }

            val data = response.data
            val results = data.results
            if (results.isEmpty()) {
                break
            }

            // 直接添加，无需再解包
            allTasks.addAll(results.filter { it.status == "active" })

            if (data.next == null) break
            page++
        }
        return allTasks
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
    suspend fun updateOneShotTask(task: OneShotTask) {
        // 本地更新不需要立即同步，进度更新有专门的 API
        taskDao.updateOneShotTask(task)
    }

    // 更新专注时长进度
    suspend fun updateExplorationProgress(taskId: Int, focusedMinutes: Int): Boolean {
        return try {
            // 假设后端接受 PATCH /api/v1/tasks/tasks/{id}/ 更新 progress 字段
            val request = PartialUpdateTaskRequest(progress = focusedMinutes)
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
            val request = PartialUpdateTaskRequest(progress = progress)
            taskApi.partialUpdateTask(taskId, request)
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    // 新增：手动完成一次性任务（regular 自动完成或 exploration 手动评估都调用此方法）
    suspend fun completeOneShotTask(taskId: Int, progress: Int? = null): TaskOccurrence {
        return completeTaskOccurrence(taskId, LocalDate.now(), progress)
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