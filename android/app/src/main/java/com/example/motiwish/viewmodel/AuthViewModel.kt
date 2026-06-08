package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.network.AuthApi
import com.example.motiwish.data.network.LoginRequest
import com.example.motiwish.data.network.RegisterRequest
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONObject
import retrofit2.HttpException

import com.example.motiwish.data.network.TokenManager

class AuthViewModel(private val authApi: AuthApi) : ViewModel() {

    // 输入框状态
    var username = MutableStateFlow("")
    var password = MutableStateFlow("")
    var confirmPassword = MutableStateFlow("")
    val email = MutableStateFlow("")

    // UI 状态
    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()

    // 页面展示状态：是否显示登录框 (启动页延时后变为 true)
    private val _showLoginPanel = MutableStateFlow(false)
    val showLoginPanel = _showLoginPanel.asStateFlow()

    // 控制当前是登录还是注册模式（false为登录，true为注册）
    private val _isRegisterMode = MutableStateFlow(false)
    val isRegisterMode = _isRegisterMode.asStateFlow()

    // 用于向 UI 发送一次性事件 (如：登录成功导航、Snackbar 报错)
    private val _authEvent = MutableSharedFlow<AuthEvent>()
    val authEvent = _authEvent.asSharedFlow()

    init {
        // 模拟启动页展示 1.5 秒后，弹出登录框
        viewModelScope.launch {
            delay(1500)
            // 这里可以加一个判断：如果本地已有 Token 且未过期，直接发送 NavigateToMain 事件
            // 否则展示登录框：
            _showLoginPanel.value = true
        }
    }

    // 切换登录和注册模式
    fun toggleMode() {
        _isRegisterMode.value = !_isRegisterMode.value
        // 切换模式时清空错误输入，提升体验
        password.value = ""
        confirmPassword.value = ""
        email.value = ""
    }

    fun login() {
        val currentUsername = username.value.trim()
        val currentPassword = password.value.trim()

        if (currentUsername.isEmpty() || currentPassword.isEmpty()) {
            viewModelScope.launch { _authEvent.emit(AuthEvent.ShowError("账号密码不能为空")) }
            return
        }

        viewModelScope.launch {
            _isLoading.value = true
            try {
                // 调用后端接口
                val response = authApi.login(LoginRequest(currentUsername, currentPassword))
                if (response.success && response.data != null) {
                    val token = response.data.access
                    // TODO: 将 token 保存到 DataStore 或 SharedPreferences 中
                    TokenManager.saveToken(response.data.access)
                    _authEvent.emit(AuthEvent.NavigateToMain)
                } else {
                    _authEvent.emit(AuthEvent.ShowError(cleanUpErrorMsg(response.message)))
                }
            } catch (e: Exception) {
                // 处理网络异常
                val readableErrorMsg = parseErrorMessage(e)
                _authEvent.emit(AuthEvent.ShowError(cleanUpErrorMsg(readableErrorMsg)))
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun register() {
        val currentUsername = username.value.trim()
        val currentEmail = email.value.trim()
        val currentPassword = password.value.trim()
        val currentConfirmPassword = confirmPassword.value.trim()

        if (currentUsername.isEmpty() || currentEmail.isEmpty() || currentPassword.isEmpty()) {
            viewModelScope.launch { _authEvent.emit(AuthEvent.ShowError("请填写完整的注册信息")) }
            return
        }
        if (currentPassword.length < 8) {
            viewModelScope.launch { _authEvent.emit(AuthEvent.ShowError("密码长度至少为 8 位")) }
            return
        }
        if (currentPassword != currentConfirmPassword) {
            viewModelScope.launch { _authEvent.emit(AuthEvent.ShowError("两次输入的密码不一致")) }
            return
        }

        viewModelScope.launch {
            _isLoading.value = true
            try {
                val response = authApi.register(
                    RegisterRequest(currentUsername, currentEmail, currentPassword, currentConfirmPassword)
                )
                if (response.success && response.data != null) {
                    TokenManager.saveToken(response.data.access)
                    _authEvent.emit(AuthEvent.NavigateToMain)
                } else {
                    _authEvent.emit(AuthEvent.ShowError(cleanUpErrorMsg(response.message)))
                }
            } catch (e: Exception) {
                val readableErrorMsg = parseErrorMessage(e)
                _authEvent.emit(AuthEvent.ShowError(cleanUpErrorMsg(readableErrorMsg)))
            } finally {
                _isLoading.value = false
            }
        }
    }

    // 解析后端返回的 JSON 错误信息
    private fun parseErrorMessage(e: Exception): String {
        if (e is HttpException) {
            try {
                val errorBody = e.response()?.errorBody()?.string()
                if (!errorBody.isNullOrBlank()) {
                    val json = JSONObject(errorBody)

                    // 🌟 核心修改：如果返回中包含 data 字段且不为空，优先遍历提取具体的字段错误
                    if (json.has("data") && !json.isNull("data")) {
                        val dataObj = json.optJSONObject("data")
                        if (dataObj != null && dataObj.length() > 0) {
                            val keys = dataObj.keys()
                            val errorMessages = mutableListOf<String>()

                            while (keys.hasNext()) {
                                val key = keys.next()
                                val fieldErrors = dataObj.optJSONArray(key)
                                if (fieldErrors != null && fieldErrors.length() > 0) {
                                    // 提取该字段的第一个错误信息（例如 password: 这个密码不能全部为数字。）
                                    errorMessages.add("$key: ${fieldErrors.getString(0)}")
                                } else {
                                    val fieldErrorStr = dataObj.optString(key)
                                    if (fieldErrorStr.isNotEmpty()) {
                                        errorMessages.add("$key: $fieldErrorStr")
                                    }
                                }
                            }
                            if (errorMessages.isNotEmpty()) {
                                // 将所有字段的错误连起来，用分号隔开
                                return "操作失败: " + errorMessages.joinToString("; ")
                            }
                        }
                    }

                    // 兜底逻辑：如果 data 为空，再读取全局提示字段
                    val rawMessage = when {
                        json.has("detail") -> json.getString("detail")
                        json.has("non_field_errors") -> json.getJSONArray("non_field_errors").getString(0)
                        json.has("error") -> json.getString("error")
                        json.has("message") -> json.getString("message")
                        json.has("username") -> "用户名无效: " + json.getJSONArray("username").getString(0)
                        json.has("password") -> "密码无效: " + json.getJSONArray("password").getString(0)
                        else -> "输入的信息有误，请检查"
                    }

                    return rawMessage.replace(Regex("[\\[\\]\"]"), "").trim()
                }
            } catch (ex: Exception) {
                return "请求失败 (HTTP ${e.code()})"
            }
        }
        return "网络开小差了，请检查网络"
    }

    private fun cleanUpErrorMsg(rawMsg: String?): String {
        if (rawMsg.isNullOrBlank()) return "操作失败"
        return rawMsg
            .replace(Regex("[\\[\\]{}()\"']"), "")
            // 过滤掉 DRF 的英文前缀
            .replace("non_field_errors:", "")
            .replace("detail:", "")
            // 翻译特定的字段属性
            .replace("username:", "用户名 ")
            .replace("password:", "密码 ")
            .replace("password_confirm:", "确认密码 ")
            .replace("email:", "电子邮箱 ")
            // 去掉结尾的句号
            .replace("。", "")
            .replace(".", "")
            .trim()
    }

    sealed class AuthEvent {
        object NavigateToMain : AuthEvent()
        data class ShowError(val message: String) : AuthEvent()
    }
}