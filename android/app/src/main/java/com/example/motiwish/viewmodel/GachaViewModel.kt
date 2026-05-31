package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import com.example.motiwish.data.network.GachaApi
import com.example.motiwish.data.network.GachaDrawRequest
import com.example.motiwish.data.repository.CurrencyRepository
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

class GachaViewModel(
    private val gachaApi: GachaApi, // 新增了 API 依赖
    private val currencyRepository: CurrencyRepository
) : ViewModel() {

    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    // 假设当前上架的常驻卡池 ID 是 1 (后续可从 /pools/ 接口动态获取)
    private val currentPoolId = 1

    suspend fun draw(times: Int): Boolean {
        try {
            // 1. 发起网络请求，让后端服务器执行真实抽卡并扣费
            val response = gachaApi.draw(currentPoolId, GachaDrawRequest(times))

            if (response.success && response.data != null) {
                val records = response.data

                // 2. 统计总收益和本次抽卡的最高稀有度
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

                // 3. 【极其重要】触发钱包刷新！
                // 因为后端已经扣了一级货币，发了二级货币，我们要让顶部的余额 UI 更新
                currencyRepository.refreshWalletFromServer()

                // 4. 根据真实抽卡结果定制文案
                val message = when {
                    times >= 10 -> "✨ 十连祈愿完成！共获得 ${totalEarned} 二级货币 ✨"
                    hasLegendary -> "✨ 欧气爆发！单抽大暴击，获得 ${totalEarned} 二级货币 ✨"
                    hasEpic -> "⭐ 暴击！获得 ${totalEarned} 二级货币 ⭐"
                    hasRare -> "🌟 小暴击！获得 ${totalEarned} 二级货币 🌟"
                    else -> "获得 ${totalEarned} 二级货币"
                }

                _uiMessage.emit(message)
                return true
            } else {
                // 如果后端返回失败 (通常是因为 400 Bad Request, 一级货币余额不足)
                // 后端会返回具体的 message，比如 "余额不足"
                _uiMessage.emit(response.message ?: "抽卡失败，请检查余额")
                return false
            }
        } catch (e: Exception) {
            e.printStackTrace()
            _uiMessage.emit("网络异常，祈愿失败")
            return false
        }
    }
}