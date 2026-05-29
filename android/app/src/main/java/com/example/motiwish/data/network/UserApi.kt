package com.example.motiwish.data.network

import retrofit2.http.GET

import okhttp3.MultipartBody
import retrofit2.http.Multipart
import retrofit2.http.PATCH
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

interface UserApi {
    // 获取当前用户信息接口
    @GET("api/v1/users/me/")
    suspend fun getCurrentUser(): ApiResponse<UserProfile>

    // 【新增】上传头像接口，使用 Multipart 表单格式
    @Multipart
    @PATCH("api/v1/users/me/")
    suspend fun updateAvatar(
        @Part avatar: MultipartBody.Part
    ): ApiResponse<UserProfile>
}