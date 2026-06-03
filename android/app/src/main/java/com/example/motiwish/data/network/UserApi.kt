package com.example.motiwish.data.network

import retrofit2.http.GET
import retrofit2.http.Body
import okhttp3.MultipartBody
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part

// 对应后端返回的详细用户模型
data class UserProfile(
    val id: Int,
    val username: String,
    val nickname: String?,
    val display_nickname: String?, // 后端计算的展示名
    val avatar_url: String?,
    val level: Int,
    val experience: Int,
    val next_level_experience: Int,
    val bio: String?
)

// --- 画像提醒状态相关模型 ---
data class ProfilePromptStatusResponse(
    val basic: PromptStatus,
    val stable: PromptStatus,
    val dynamic: PromptStatus
)

data class PromptStatus(
    val completed: Boolean? = null,         // 基础/稳定层独有
    val has_meaningful_data: Boolean? = null, // 动态层独有
    val should_prompt: Boolean ,  // 核心字段：是否需要弹窗
    val last_prompted_at: String? = null
)

// --- 稳定画像表单请求模型 (举例几个必填字段) ---
data class StableProfileRequest(
    val self_management_challenges: List<String>,
    val motivation_preferences: List<String>,
    val reward_preference: String,
    val penalty_tolerance: String,
    val stress_sensitivity: String,
    val self_discipline_score: Int,
    val chronotype: String,
    val energy_peak_periods: List<String>,
    val task_granularity_preference: String,
    val planning_style_preference: String
)
data class StableProfileResponse(
    val self_management_challenges: List<String>?,
    val motivation_preferences: List<String>?,
    val reward_preference: String?,
    val penalty_tolerance: String?,
    val stress_sensitivity: String?,
    val self_discipline_score: Int?,
    val chronotype: String?,
    val energy_peak_periods: List<String>?,
    val task_granularity_preference: String?,
    val planning_style_preference: String?
)

data class BasicProfileRequest(
    val nickname: String,
    val gender: String,
    val occupation: String,
    val education_stage: String,
    val language_preference: String,
    val timezone: String,
    val long_term_goals: List<String>,
    val focus_areas: List<String>
)

interface UserApi {
    // 获取当前用户信息接口
    @GET("api/v1/users/me/")
    suspend fun getCurrentUser(): ApiResponse<UserProfile>

    // 上传头像接口，使用 Multipart 表单格式
    @Multipart
    @PATCH("api/v1/users/me/")
    suspend fun updateAvatar(
        @Part avatar: MultipartBody.Part
    ): ApiResponse<UserProfile>

    // 画像相关
    @GET("api/v1/users/profile/prompts/")
    suspend fun getProfilePromptStatus(): ApiResponse<ProfilePromptStatusResponse>

    // 2. 确认已弹窗 (节流，避免一直弹)
    @POST("api/v1/users/profile/prompts/ack/")
    suspend fun ackProfilePrompt(@Body request: Map<String, String>): ApiResponse<Any>

    // 3. 更新基础资料
    @PATCH("api/v1/users/me/")
    suspend fun updateBasicProfile(@Body request: BasicProfileRequest): ApiResponse<UserProfile>

    // 4. 提交/更新稳定画像问卷
    @PATCH("api/v1/users/profile/stable/")
    suspend fun updateStableProfile(@Body request: StableProfileRequest): ApiResponse<Any>

    // 获取用户的稳定画像数据
    @GET("api/v1/users/profile/stable/")
    suspend fun getStableProfile(): ApiResponse<StableProfileResponse>
}