package com.example.motiwish.data.network

import com.google.gson.annotations.SerializedName
// 4. Retrofit 接口
import retrofit2.http.Body
import retrofit2.http.POST

// 1. 统一的响应包裹类
data class ApiResponse<T>(
    val success: Boolean,
    val code: String,
    val message: String,
    val data: T?
)

// 2. 登录请求体
data class LoginRequest(
    val username: String,
    val password: String
)

// 3. 登录成功后的 Token 数据
data class JWTToken(
    val access: String,
    val refresh: String,
    val user: UserDto // 简化的用户对象，根据你的需要可扩展
)

data class UserDto(
    val id: Int,
    val username: String,
    val nickname: String?,
    val avatar: String?
)



interface AuthApi {
    @POST("api/v1/users/auth/login/")
    suspend fun login(@Body request: LoginRequest): ApiResponse<JWTToken>
}