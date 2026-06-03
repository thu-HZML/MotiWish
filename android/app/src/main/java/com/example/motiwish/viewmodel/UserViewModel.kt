package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.network.UserApi
import com.example.motiwish.data.network.UserProfile
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

import android.content.Context
import android.net.Uri
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import java.io.ByteArrayOutputStream
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

import android.util.Log
import com.example.motiwish.data.network.BasicProfileRequest
import com.example.motiwish.data.network.StableProfileRequest
import com.example.motiwish.data.network.StableProfileResponse
import retrofit2.HttpException

class UserViewModel(private val userApi: UserApi) : ViewModel() {

    private val _userProfile = MutableStateFlow<UserProfile?>(null)
    val userProfile = _userProfile.asStateFlow()
    // 记录当前是否需要展示问卷
    private val _showOnboarding = MutableStateFlow(false)
    val showOnboarding = _showOnboarding.asStateFlow()

    private val _stableProfileData = MutableStateFlow<StableProfileResponse?>(null)
    val stableProfileData = _stableProfileData.asStateFlow()

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

    fun fetchStableProfile() {
        viewModelScope.launch {
            try {
                val response = userApi.getStableProfile()
                if (response.success) {
                    _stableProfileData.value = response.data
                }
            } catch (e: Exception) {
                Log.e("UserViewModel", "获取稳定画像失败", e)
            }
        }
    }

    // 检查是否需要弹窗
    fun checkProfilePromptStatus() {
        viewModelScope.launch {
            try {
                val response = userApi.getProfilePromptStatus()
                if (response.success) {
                    val status = response.data
                    if (status != null) {
                        Log.d("MotiWish_Profile", "后端状态：basic=${status.basic.should_prompt}, stable=${status.stable.should_prompt}")

                        // ✅ 【核心修复】：不仅要看后端是否要求提醒，还要看是不是“从来没被提醒过”
                        // 只要 last_prompted_at 不是 null，说明之前已经弹过向导并执行过 ack 了，坚决不再重复弹！
                        val needsBasicOnboarding = status.basic.should_prompt && status.basic.last_prompted_at == null
                        val needsStableOnboarding = status.stable.should_prompt && status.stable.last_prompted_at == null

                        if (needsBasicOnboarding || needsStableOnboarding) {
                            _showOnboarding.value = true
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e("UserViewModel", "检查画像状态失败", e)
            }
        }
    }
    fun submitOnboarding(
        nickname: String,
        gender: String,
        stableData: StableProfileRequest,
        onComplete: () -> Unit
    ) {
        viewModelScope.launch {
            try {
                // 1. 组装并发送基础信息
                val basicReq = BasicProfileRequest(
                    nickname = nickname.ifEmpty { "MotiUser" },
                    gender = gender.ifEmpty { "unknown" },
                    occupation = "undisclosed",
                    education_stage = "undisclosed",
                    language_preference = "zh-hans",
                    timezone = "Asia/Shanghai",
                    long_term_goals = listOf("unspecified"),
                    focus_areas = listOf("unspecified")
                )

                Log.d("MotiWish_Onboarding", "正在提交基础资料...")
                userApi.updateBasicProfile(basicReq)

                Log.d("MotiWish_Onboarding", "正在提交行为画像...")
                userApi.updateStableProfile(stableData)

                Log.d("MotiWish_Onboarding", "正在发送已读确权...")
                userApi.ackProfilePrompt(mapOf("layer" to "basic"))
                userApi.ackProfilePrompt(mapOf("layer" to "stable"))

                // ✅ 成功流：关闭开关，刷新用户资料，退出页面
                _showOnboarding.value = false
                fetchUserProfile()
                onComplete()

            } catch (e: Exception) {
                Log.e("UserViewModel", "新手引导提交失败: ${e.message}", e)

                // ✅ 【核心修复】：哪怕网络崩了或者报 404 了，也必须在这里强行把弹窗开关设为 false！
                // 这样能绝对保证打断循环，让用户先留在首页，不会被无限卡死
                _showOnboarding.value = false

                // 执行返回上一页
                onComplete()
            }
        }
    }

    // 提交问卷并关闭弹窗
    /*fun completeQuestionnaire(stableData: StableProfileRequest) {
        viewModelScope.launch {
            try {
                // 1. 提交数据给后端
                val response = userApi.updateStableProfile(stableData)
                if (response.success) {
                    // 2. 告诉后端我们已经展示过提醒了 (防止下次进来还重复弹)
                    userApi.ackProfilePrompt(mapOf("layer" to "stable"))
                    // 3. 关闭前端弹窗
                    _showQuestionnaire.value = false
                    // 4. 刷新一次用户信息
                    fetchUserProfile()
                }
            } catch (e: Exception) {
                Log.e("UserViewModel", "提交画像问卷失败", e)
            }
        }
    }

    // 关闭/跳过弹窗
    fun dismissQuestionnaire() {
        _showOnboarding.value = false
    }*/
    fun updateStableProfileData(stableData: StableProfileRequest) {
        viewModelScope.launch {
            try {
                val response = userApi.updateStableProfile(stableData)
                if (response.success) {
                    // 修改成功后，重新拉取一下用户信息即可
                    fetchUserProfile()
                }
            } catch (e: Exception) {
                Log.e("UserViewModel", "日常更新画像失败", e)
            }
        }
    }

    fun uploadAvatar(context: Context, uri: Uri) {
        viewModelScope.launch {
            try {
                // 1. 获取输入流并将其解码为 Bitmap
                val inputStream = context.contentResolver.openInputStream(uri)
                val originalBitmap = BitmapFactory.decodeStream(inputStream)
                inputStream?.close()

                if (originalBitmap != null) {
                    // 2. 将 Bitmap 进行 JPEG 压缩（80 的质量能大幅减小体积，且肉眼几乎看不出区别）
                    val outputStream = ByteArrayOutputStream()
                    originalBitmap.compress(Bitmap.CompressFormat.JPEG, 80, outputStream)
                    val bytes = outputStream.toByteArray()

                    // 3. 包装为 RequestBody，明确指定为 image/jpeg
                    val requestBody = bytes.toRequestBody("image/jpeg".toMediaTypeOrNull())

                    // 4. 构建 Multipart 表单字段
                    val body =
                        MultipartBody.Part.createFormData("avatar", "avatar.jpg", requestBody)

                    // 5. 发起网络请求
                    val response = userApi.updateAvatar(body)
                    if (response.success && response.data != null) {
                        _userProfile.value = response.data
                    }
                }
            } catch (e: Exception) {
                Log.e("MotiWish_Avatar", "上传异常: ${e.message}", e)
            }
        }
    }

    // 退出登录
    fun logout() {
        com.example.motiwish.data.network.TokenManager.clearToken()
        _userProfile.value = null
    }
}