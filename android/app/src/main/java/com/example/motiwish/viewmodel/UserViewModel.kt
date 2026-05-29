package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.network.UserApi
import com.example.motiwish.data.network.UserProfile
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

import android.content.Context
import android.net.Uri
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

class UserViewModel(private val userApi: UserApi) : ViewModel() {

    private val _userProfile = MutableStateFlow<UserProfile?>(null)
    val userProfile = _userProfile.asStateFlow()

    fun fetchUserProfile() {
        viewModelScope.launch {
            try {
                val response = userApi.getCurrentUser()
                if (response.success) {
                    _userProfile.value = response.data
                }
            } catch (e: Exception) {
                // 网络错误或 Token 失效处理
            }
        }
    }

    fun uploadAvatar(context: Context, uri: Uri) {
        viewModelScope.launch {
            try {
                // 1. 将本地 Uri 解析为输入流并读取所有字节
                val inputStream = context.contentResolver.openInputStream(uri)
                val bytes = inputStream?.readBytes()
                inputStream?.close()

                if (bytes != null) {
                    // 2. 包装为 RequestBody (MIME 类型指定为 image/*)
                    val requestBody = bytes.toRequestBody("image/*".toMediaTypeOrNull())

                    // 3. 构建表单的 Part 字段，字段名必须为 "avatar"，后端通过扩展名解析格式
                    val body = MultipartBody.Part.createFormData("avatar", "avatar.jpg", requestBody)

                    // 4. 发起请求
                    val response = userApi.updateAvatar(body)
                    if (response.success && response.data != null) {
                        // 成功后，后端会返回更新后的完整用户信息（包含新的 avatar_url）
                        // 直接覆盖本地状态，UI 会自动刷新头像！
                        _userProfile.value = response.data
                    }
                }
            } catch (e: Exception) {
                // 网络异常或文件读取异常处理
                e.printStackTrace()
            }
        }
    }

    // 退出登录
    fun logout() {
        com.example.motiwish.data.network.TokenManager.clearToken()
        _userProfile.value = null
    }
}