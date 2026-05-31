package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.network.NetworkRedemptionRecord
import com.example.motiwish.data.network.ShopApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class RedemptionHistoryViewModel(private val shopApi: ShopApi) : ViewModel() {
    private val _records = MutableStateFlow<List<NetworkRedemptionRecord>>(emptyList())
    val records: StateFlow<List<NetworkRedemptionRecord>> = _records.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

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
}