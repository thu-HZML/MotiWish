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
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import java.io.ByteArrayOutputStream
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

import android.util.Log
import retrofit2.HttpException

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