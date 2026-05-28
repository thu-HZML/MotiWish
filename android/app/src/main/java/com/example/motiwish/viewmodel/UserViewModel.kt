package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.network.UserApi
import com.example.motiwish.data.network.UserProfile
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

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

    // 退出登录
    fun logout() {
        com.example.motiwish.data.network.TokenManager.clearToken()
        _userProfile.value = null
    }
}