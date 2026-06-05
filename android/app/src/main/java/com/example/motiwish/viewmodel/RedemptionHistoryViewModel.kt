package com.example.motiwish.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.network.NetworkRedemptionRecord
import com.example.motiwish.data.network.ShopApi
import com.example.motiwish.data.network.UserInventoryItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import org.json.JSONObject
import retrofit2.HttpException

class RedemptionHistoryViewModel(private val shopApi: ShopApi) : ViewModel() {
    private val _records = MutableStateFlow<List<NetworkRedemptionRecord>>(emptyList())
    val records: StateFlow<List<NetworkRedemptionRecord>> = _records.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    // 存放背包道具的列表
    private val _inventoryList = MutableStateFlow<List<UserInventoryItem>>(emptyList())
    val inventoryList = _inventoryList.asStateFlow()

    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage = _uiMessage.asSharedFlow()

    fun fetchHistory() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val response = shopApi.getRedemptionHistory()
                if (response.success && response.data != null) {
                    _records.value = response.data.results
                }
            } catch (e: Exception) {
                e.printStackTrace()
                // 网络异常可以只打印，不打断用户操作
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun fulfillRecord(recordId: Int) {
        viewModelScope.launch {
            try {
                // 调用后端的兑现接口
                val response = shopApi.fulfillRedemption(recordId)
                if (response.success) {
                    // 兑现成功后，重新拉取一次历史记录，刷新列表状态
                    fetchHistory()
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    // 1. 获取背包列表
    fun fetchInventory() {
        viewModelScope.launch {
            try {
                val response = shopApi.getUserInventory()
                if (response.success && response.data != null) {
                    // ✅ 第一步：把真正的数组（results）从外壳里剥离出来
                    val actualList = response.data.results

                    // 如果你有打印日志的需求，请对 actualList 进行操作，而不是 response.data
                    // Log.d("InventoryDebug", "背包拉取成功，数量: ${actualList.size}")

                    // ✅ 第二步：把剥离出来的纯净数组赋值给 UI 状态
                    _inventoryList.value = actualList
                } else {
                    _inventoryList.value = emptyList()
                }
            } catch (e: Exception) {
                Log.e("InventoryViewModel", "获取背包失败", e)
                _inventoryList.value = emptyList()
            }
        }
    }

    // 2. 使用道具（带钱包刷新回调）
    fun useItem(inventoryId: Int, onWalletRefreshNeeded: () -> Unit) {
        viewModelScope.launch {
            try {
                val response = shopApi.useInventoryItem(inventoryId, emptyMap())
                if (response.success) {
                    _uiMessage.emit("道具使用成功！")

                    // 刷新背包（数量扣减为 0 的会自动被后端过滤掉）
                    fetchInventory()

                    // 【核心】：触发回调，通知 CurrencyViewModel 去后端拉取最新余额，清零负债！
                    onWalletRefreshNeeded()
                } else {
                    _uiMessage.emit("使用失败：${response.message}")
                }
            } catch (e: HttpException) {
                // ✅ 专门拦截 HTTP 400 等后端主动报的错误 (例如：当前没有负债)
                var errorMsg = "条件不满足，无法使用该道具"
                try {
                    val errorBody = e.response()?.errorBody()?.string()
                    if (!errorBody.isNullOrBlank()) {
                        val json = JSONObject(errorBody)
                        when {
                            json.has("detail") -> errorMsg = json.getString("detail")
                            json.has("error") -> errorMsg = json.getString("error")
                            json.has("message") -> errorMsg = json.getString("message")
                            json.has("non_field_errors") -> errorMsg = json.getJSONArray("non_field_errors").getString(0)
                        }
                    }
                } catch (ex: Exception) {
                    // 解析失败时保留默认提示
                }

                // 字符串净水器：清理括号、句号和多余空格
                val cleanMsg = errorMsg.replace(Regex("[\\[\\]{}()\"']"), "").replace("。", "").trim()
                _uiMessage.emit("使用失败: $cleanMsg")

            } catch (e: Exception) {
                Log.e("InventoryViewModel", "使用道具失败", e)
                _uiMessage.emit("网络异常，请重试")
            }
        }
    }
}