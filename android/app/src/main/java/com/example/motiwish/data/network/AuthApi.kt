package com.example.motiwish.data.network

import com.google.gson.annotations.SerializedName
// Retrofit 接口
import retrofit2.http.Body
import retrofit2.http.POST


// 响应包裹类
data class ApiResponse<T>(
    val success: Boolean,
    val code: String,
    val message: String,
    val data: T?
)

// 登录请求体
data class LoginRequest(
    val username: String,
    val password: String
)

// 注册请求体：根据后端 OpenAPI 规范，最小注册必填项为用户名、邮箱和密码
data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String,
    @SerializedName("password_confirm") val passwordConfirm: String
)

// 登录成功后的 Token 数据
data class JWTToken(
    val access: String,
    val refresh: String,
    val user: UserDto
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

    // 注册接口
    @POST("api/v1/users/auth/register/")
    suspend fun register(@Body request: RegisterRequest): ApiResponse<JWTToken>
}