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
import com.example.motiwish.data.network.DynamicProfileData
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

    // 动态画像专用的状态和控制
    private val _showDynamicPrompt = MutableStateFlow(false)
    val showDynamicPrompt = _showDynamicPrompt.asStateFlow()

    private val _dynamicProfileData = MutableStateFlow<DynamicProfileData?>(null)
    val dynamicProfileData = _dynamicProfileData.asStateFlow()

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
                if (response.success && response.data != null) {
                    val status = response.data

                    // 之前的逻辑：基础或稳定没填，弹强制向导
                    val needsBasic = status.basic.should_prompt && status.basic.last_prompted_at == null
                    val needsStable = status.stable.should_prompt && status.stable.last_prompted_at == null
                    if (needsBasic || needsStable) {
                        _showOnboarding.value = true
                        return@launch // 强制向导优先级最高，有了它就不弹动态了
                    }

                    // 【新增逻辑】：如果不需要强制向导，且动态画像该提醒了，就弹出底部半屏
                    if (status.dynamic.should_prompt) {
                        fetchDynamicProfile() // 先拉取一下上次填的数据做回显
                        _showDynamicPrompt.value = true
                    }
                }
            } catch (e: Exception) {
                Log.e("UserViewModel", "检查画像失败", e)
            }
        }
    }
    // 2. 拉取动态画像数据
    fun fetchDynamicProfile() {
        viewModelScope.launch {
            try {
                val res = userApi.getDynamicProfile()
                if (res.success) _dynamicProfileData.value = res.data
            } catch (e: Exception) {}
        }
    }

    // 3. 提交动态画像
    fun submitDynamicProfile(
        stageTags: Set<String>,
        stressLevel: Int,
        sleepQuality: String,
        moodState: String,
        availableTimeLevel: String,
        topGoal: String,
        mainBlocker: String,
        weeklyHoursStr: String
    ) {
        // 第一步依然是安全关闭弹窗防误触
        _showDynamicPrompt.value = false

        viewModelScope.launch {
            try {
                // 动态拼装增量字典（只传有有效值的字段）
                val updateMap = mutableMapOf<String, Any>(
                    "stress_level" to stressLevel
                )

                if (stageTags.isNotEmpty()) updateMap["current_stage_tags"] = stageTags.toList()
                if (sleepQuality.isNotBlank()) updateMap["sleep_quality"] = sleepQuality
                if (moodState.isNotBlank()) updateMap["mood_state"] = moodState
                if (availableTimeLevel.isNotBlank()) updateMap["available_time_level"] = availableTimeLevel

                if (topGoal.isNotBlank()) updateMap["current_top_goal"] = topGoal
                if (mainBlocker.isNotBlank()) updateMap["current_main_blocker"] = mainBlocker

                // 将字符串安全转为整数
                weeklyHoursStr.toIntOrNull()?.let {
                    updateMap["weekly_time_budget_hours"] = it
                }

                Log.d("MotiWish_Dynamic", "--> 1. 发送全量动态更新: $updateMap")
                userApi.updateDynamicProfile(updateMap)

                Log.d("MotiWish_Dynamic", "--> 2. 更新成功！正在发送确权...")
                userApi.ackProfilePrompt(mapOf("layer" to "dynamic"))

                Log.d("MotiWish_Dynamic", "--> 3. 确权成功！刷新状态墙...")
                fetchDynamicProfile()

            } catch (e: Exception) {
                if (e is retrofit2.HttpException) {
                    val errorJson = e.response()?.errorBody()?.string()
                    Log.e("MotiWish_Dynamic", "--> ❌ 后端校验拒绝 (HTTP ${e.code()})！详情: $errorJson")
                } else {
                    Log.e("MotiWish_Dynamic", "--> ❌ 网络或其他异常: ${e.message}", e)
                }
            }
        }
    }

    // 4. 跳过动态画像
    fun skipDynamicPrompt() {
        _showDynamicPrompt.value = false
        viewModelScope.launch {
            try {
                Log.d("MotiWish_Dynamic", "--> 用户选择跳过，正在发送跳过确权...")
                userApi.ackProfilePrompt(mapOf("layer" to "dynamic"))
            } catch (e: Exception) {
                Log.e("MotiWish_Dynamic", "--> 跳过确权失败: ${e.message}")
            }
        }
    }

    // 5. 主动呼出弹窗（供个人主页点击使用）
    fun openDynamicPrompt() {
        fetchDynamicProfile()
        _showDynamicPrompt.value = true
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