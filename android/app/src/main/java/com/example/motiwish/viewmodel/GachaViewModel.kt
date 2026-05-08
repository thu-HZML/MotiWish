package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.repository.CurrencyRepository
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import kotlin.random.Random

class GachaViewModel(private val currencyRepository: CurrencyRepository) : ViewModel() {
    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    // 将参数改为抽卡次数 (times)
    suspend fun draw(times: Int): Boolean {
        val totalCost = times * 10
        if (!currencyRepository.deductPrimaryCurrency(totalCost, "抽卡消费 - ${times}连")) {
            _uiMessage.emit("一级货币不足，快去完成任务吧！")
            return false
        }

        var totalEarned = 0
        var highestMultiplier = 1.0

        // 独立计算每一次抽卡
        for (i in 1..times) {
            var random = Random.nextDouble()

            // 十连保底机制：如果是十连抽的最后一次，且之前没有触发过3倍及以上暴击
            if (times >= 10 && i == times && highestMultiplier < 3.0) {
                random = 0.1 // 强制进入 3倍 概率区间
            }

            val multiplier = when {
                random < 0.05 -> 5.0
                random < 0.15 -> 3.0
                random < 0.35 -> 2.0
                else -> 1.0
            }

            if (multiplier > highestMultiplier) {
                highestMultiplier = multiplier
            }

            totalEarned += (50 * multiplier).toInt()
        }

        currencyRepository.addSecondaryCurrency(totalEarned, "抽卡获得")

        // 根据最高倍率和抽卡次数定制文案
        val message = when {
            times >= 10 -> "✨ 十连祈愿完成！共获得 ${totalEarned} 二级货币 ✨"
            highestMultiplier == 5.0 -> "✨ 欧气爆发！单抽大暴击，获得 ${totalEarned} 二级货币 ✨"
            highestMultiplier == 3.0 -> "⭐ 暴击！获得 ${totalEarned} 二级货币 ⭐"
            highestMultiplier == 2.0 -> "🌟 小暴击！获得 ${totalEarned} 二级货币 🌟"
            else -> "获得 ${totalEarned} 二级货币"
        }

        _uiMessage.emit(message)
        return true
    }
}