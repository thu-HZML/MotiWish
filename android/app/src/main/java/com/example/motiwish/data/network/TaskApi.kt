// TaskApi.kt
package com.example.motiwish.data.network

import retrofit2.http.*
import java.time.LocalDate
import java.time.LocalDateTime
import retrofit2.Response

// ---------- 请求/响应 DTO ----------
// 任务列表分页响应（外层）
data class TaskListResponse(
    val success: Boolean,
    val code: String,
    val message: String,
    val data: TaskListData
)

// data 中的每一项
data class TaskListData(
    val count: Int,
    val next: String?,
    val previous: String?,
    val results: List<RemoteTask>
)

data class RemoteTask(
    val id: Int,
    val title: String,
    val description: String?,
    val task_type: String,          // "daily", "weekly", "monthly", "one_time", "metric"
    val recurrence: String,         // "none", "daily", "weekly", "monthly"
    val settlement_track: String,
    val difficulty_level: String?,
    val estimated_focus_minutes: Int?,
    val weekdays: List<Int>?,       // 0=周一 ~ 6=周日
    val month_days: List<Int>?,
    val metric_key: String?,
    val target_value: Int?,
    val progress_target: Int?,
    val reward_primary: Int,
    val penalty_primary: Int,
    val pricing_status: String,
    val pricing_requested_at: String?,
    val pricing_resolved_at: String?,
    val pricing_snapshot: Any?,
    val starts_on: String?,         // "YYYY-MM-DD"
    val ends_on: String?,
    val due_at: String?,            // "YYYY-MM-DDTHH:MM:SSZ"
    val status: String,             // "active", "archived"
    val tags: List<String>?,
    val ai_metadata: Any?,
    val created_at: String,
    val updated_at: String
)

// ---------- 创建任务请求体 ----------
data class CreateTaskRequest(
    val title: String,
    val description: String? = null,
    val task_type: String,          // "daily", "recurring", "one_time"
    val recurrence: String? = null, // "none", "daily", "weekly", "monthly"
    val settlement_track: String? = null,   // "regular", "exploration"
    val difficulty_level: String? = null,
    val estimated_focus_minutes: Int? = null,
    val weekdays: List<Int>? = null,        // 0=周一 ~ 6=周日
    val month_days: List<Int>? = null,
    val metric_key: String? = null,
    val target_value: Int? = null,
    val progress_target: Int? = null,
    val reward_primary: Int? = null,
    val penalty_primary: Int? = null,
    val starts_on: String? = null,          // "YYYY-MM-DD"
    val ends_on: String? = null,
    val due_at: String? = null,             // ISO 8601 日期时间
    val status: String? = null,             // "active", "archived"
    val tags: List<String>? = null,
    val ai_metadata: Any? = null
)

// ---------- 创建任务响应 ----------
data class CreateTaskResponse(
    val data: TaskData,
    val success: Boolean,
    val code: String,
    val message: String
)

data class TaskData(
    val id: Int,
    val title: String,
    val description: String?,
    val task_type: String,
    val recurrence: String?,
    val settlement_track: String?,
    val difficulty_level: String?,
    val estimated_focus_minutes: Int?,
    val weekdays: List<Int>?,
    val month_days: List<Int>?,
    val metric_key: String?,
    val target_value: Int?,
    val progress_target: Int?,
    val reward_primary: Int,
    val penalty_primary: Int,
    val pricing_status: String,
    val pricing_requested_at: String?,
    val pricing_resolved_at: String?,
    val pricing_snapshot: Any?,
    val starts_on: String?,
    val ends_on: String?,
    val due_at: String?,
    val status: String,
    val tags: List<String>?,
    val ai_metadata: Any?,
    val created_at: String,
    val updated_at: String
)

// 日常指标评估请求
data class EvaluateDailyMetricRequest(
    val wake_up_time: String,
    val sleep_time: String,
    val phone_usage_minutes: Int,
    val water_cups: Int
)

data class EvaluateDailyMetricResponse(
    val success: Boolean,
    val reward: Int,
    val message: String
)

// ---------- 历史记录相关模型 ----------
data class TaskOccurrenceResponse(
    val data: List<TaskOccurrence>,
    val success: Boolean,
    val code: String,
    val message: String
)

data class TaskOccurrence(
    val id: Int,
    val task: TaskBrief,
    val occurrence_date: String,       // "YYYY-MM-DD"
    val status: String,                // "pending", "completed", "missed", "cancelled"
    val progress: Int,
    val settled_at: String?,
    val reward_transaction_id: Int?,
    val penalty_transaction_id: Int?,
    val created_at: String,
    val updated_at: String,
    val settlement_details: SettlementDetails? = null
)

data class TaskBrief(
    val id: Int,
    val title: String,
    val description: String?,
    val task_type: String,
    val recurrence: String?,
    val settlement_track: String?,
    val difficulty_level: String?,
    val estimated_focus_minutes: Int?,
    val weekdays: List<Int>?,
    val month_days: List<Int>?,
    val metric_key: String?,
    val target_value: Int?,
    val progress_target: Int?,
    val reward_primary: Int,
    val penalty_primary: Int,
    val pricing_status: String,
    val status: String,
    val starts_on: String?,
    val ends_on: String?,
    val due_at: String?,
    val created_at: String,
    val updated_at: String
)

data class SettlementDetails(
    val settlement_track: String,
    val formula: String,
    val base_reward: Int,
    val progress_ratio: Double,
    val progress_factor: Double,
    val time_factor: Double,
    val reward_primary: Int,
    val penalty_primary: Int,
    val task_reward_primary: Int,
    val task_penalty_primary: Int
)

// 完成任务相关
// 请求体
data class CompleteTaskRequest(
    val occurrence_date: String? = null,  // 格式 YYYY-MM-DD，默认今天
    val progress: Int? = null              // 进度值，不传则使用任务的 progress_target
)

// 响应（复用已有的 TaskOccurrenceResponse，但这里只返回单个对象）
data class CompleteTaskResponse(
    val data: TaskOccurrence,
    val success: Boolean,
    val code: String,
    val message: String
)

// ---------- AI 定价会话相关 ----------
data class CreatePricingSessionRequest(
    val task_payload: TaskPayload
)

data class TaskPayload(
    val title: String,
    val description: String? = null,
    val task_type: String,          // "daily", "recurring", "one_time"
    val recurrence: String? = null,
    val settlement_track: String? = null,
    val difficulty_level: String? = null,
    val estimated_focus_minutes: Int? = null,
    val weekdays: List<Int>? = null,
    val month_days: List<Int>? = null,
    val metric_key: String? = null,
    val target_value: Int? = null,
    val progress_target: Int? = null,
    val due_at: String? = null,            // 新增：截止时间（ISO 8601 字符串）
    val tags: List<String>? = null
)

data class PricingSessionResponse(
    val data: PricingSession,
    val success: Boolean,
    val code: String,
    val message: String
)

data class PricingSession(
    val id: Int,
    val status: String,  // "waiting_feedback", "accepted", etc.
    val task_payload: TaskPayload,
    val quote_payload: QuotePayload,
    val feedback_history: List<Any>?,
    val created_task: CreatedTask?
)

data class QuotePayload(
    val reward_primary: Int,
    val penalty_primary: Int,
    val price_tier: String,
    val confidence: Double,
    val reasoning: String,
    val risk_notes: List<String>,
    val user_fit_notes: List<String>,
    val llm_style_payload: Any
)

data class CreatedTask(
    val id: Int,
    val title: String,
    val reward_primary: Int,
    val penalty_primary: Int,
    val pricing_status: String
)

// 提交反馈请求
data class FeedbackRequest(
    val action: String,  // "accept" or "revise"
    val feedback_direction: String? = null,  // "too_high", "too_low", "detail"
    val feedback_text: String? = null
)

// 反馈响应
data class FeedbackResponse(
    val data: PricingSession,
    val success: Boolean,
    val code: String,
    val message: String
)

// ---------- API 接口 ----------
interface TaskApi {
    // 获取任务列表（支持分页）
    @GET("/api/v1/tasks/tasks/")
    suspend fun getTasks(@Query("page") page: Int = 1): TaskListResponse

    // 获取指定日期的任务列表
    @GET("/api/v1/tasks/tasks/today/")
    suspend fun getTodayTasks(@Query("date") date: String? = null): TaskOccurrenceResponse

    // 创建任务（后端定价后自动创建任务，暂时用不到）
    @POST("/api/v1/tasks/tasks/")
    suspend fun createTask(@Body request: CreateTaskRequest): CreateTaskResponse

    // 评估日常指标
    @POST("/api/daily-metrics/evaluate")
    suspend fun evaluateDailyMetric(@Body request: EvaluateDailyMetricRequest): EvaluateDailyMetricResponse

    // 完成任务
    @POST("/api/v1/tasks/tasks/{id}/complete/")
    suspend fun completeTask(
        @Path("id") id: Int,
        @Body request: CompleteTaskRequest
    ): CompleteTaskResponse

    // 部分更新任务（更新一次性任务进度）
    @PATCH("/api/v1/tasks/tasks/{id}/")
    suspend fun partialUpdateTask(
        @Path("id") id: Int,
        @Body request: PartialUpdateTaskRequest
    ): TaskData  // 返回更新后的完整任务数据

    // 评估一次性任务（通常后端会自动评估，但也可以手动触发）
    @POST("/api/one-shot-tasks/{id}/evaluate")
    suspend fun evaluateOneShotTask(@Path("id") id: Int)

    // 删除任务
    @DELETE("/api/v1/tasks/tasks/{id}/")
    suspend fun deleteTask(@Path("id") id: Int): Response<Unit>  // 204 响应无内容，使用 Response<Unit

    // 获取任务历史记录
    @GET("/api/v1/tasks/tasks/history/")
    suspend fun getTaskHistory(): TaskOccurrenceResponse

    // 创建定价会话
    @POST("/api/v1/ai/task-pricing-sessions/")
    suspend fun createPricingSession(@Body request: CreatePricingSessionRequest): PricingSessionResponse

    // 提交反馈（接受或修订）
    @POST("/api/v1/ai/task-pricing-sessions/{sessionId}/feedback/")
    suspend fun submitFeedback(
        @Path("sessionId") sessionId: Int,
        @Body request: FeedbackRequest
    ): FeedbackResponse
}

// 请求体 DTO
data class OneShotTaskRequest(
    val title: String,
    val description: String,
    val due_at: LocalDateTime,
    val reward_primary: Int = 0,
    val penalty_primary: Int = 0
)

data class PeriodicTaskRequest(
    val title: String,
    val task_type: String,      // "daily", "weekly", "monthly"
    val weekdays: List<Int>? = null,
    val month_days: List<Int>? = null,
    val reward_primary: Int
)

// 部分更新任务请求体 DTO（所有字段可选，对应 PATCH 语义）
data class PartialUpdateTaskRequest(
    val title: String? = null,
    val description: String? = null,
    val task_type: String? = null,
    val recurrence: String? = null,
    val settlement_track: String? = null,
    val difficulty_level: String? = null,
    val estimated_focus_minutes: Int? = null,
    val weekdays: List<Int>? = null,
    val month_days: List<Int>? = null,
    val metric_key: String? = null,
    val target_value: Int? = null,
    val progress_target: Int? = null,
    val progress: Int? = null,    // 用于更新一次性任务的进度
    val reward_primary: Int? = null,
    val penalty_primary: Int? = null,
    val starts_on: String? = null,
    val ends_on: String? = null,
    val due_at: String? = null,
    val status: String? = null,
    val tags: List<String>? = null,
    val ai_metadata: Any? = null
)