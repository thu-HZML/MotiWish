package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import com.example.motiwish.data.network.GachaApi
import com.example.motiwish.data.network.GachaDrawRequest
import com.example.motiwish.data.repository.CurrencyRepository
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.first
class GachaViewModel(
    private val gachaApi: GachaApi, // 新增了 API 依赖
    private val currencyRepository: CurrencyRepository
) : ViewModel() {

    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    // 假设当前上架的常驻卡池 ID 是 1 (后续可从 /pools/ 接口动态获取)
    private val currentPoolId = 1

    fun draw(times: Int) {
        // 2. 用 viewModelScope.launch 把原有的代码包起来
        viewModelScope.launch {
            try {
                val costPerDraw = 10
                val totalCost = times * costPerDraw

                val currentBalance = currencyRepository.getCurrencyBalance().first()?.primaryCurrency ?: 0

                if (currentBalance < totalCost) {
                    _uiMessage.emit("一级货币不足！需要 $totalCost 币，当前仅有 $currentBalance 币")
                    return@launch // 注意：这里的 return 加上 @launch
                }

                val response = gachaApi.draw(currentPoolId, GachaDrawRequest(times))

                if (response.success && response.data != null) {
                    val records = response.data
                    var totalEarned = 0
                    var hasLegendary = false
                    var hasEpic = false
                    var hasRare = false

                    records.forEach { record ->
                        totalEarned += record.reward_secondary
                        when (record.reward_tier) {
                            "legendary" -> hasLegendary = true
                            "epic" -> hasEpic = true
                            "rare" -> hasRare = true
                        }
                    }

                    currencyRepository.refreshWalletFromServer()

                    val message = when {
                        times >= 10 -> "✨ 十连祈愿完成！共获得 ${totalEarned} 二级货币 ✨"
                        hasLegendary -> "✨ 欧气爆发！单抽大暴击，获得 ${totalEarned} 二级货币 ✨"
                        hasEpic -> "⭐ 暴击！获得 ${totalEarned} 二级货币 ⭐"
                        hasRare -> "🌟 小暴击！获得 ${totalEarned} 二级货币 🌟"
                        else -> "获得 ${totalEarned} 二级货币"
                    }

                    _uiMessage.emit(message)
                } else {
                    _uiMessage.emit(response.message ?: "抽卡失败，请检查余额")
                }
            } catch (e: Exception) {
                e.printStackTrace()
                _uiMessage.emit("网络异常，祈愿失败")
            }
        }
    }
}