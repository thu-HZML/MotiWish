package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.repository.CurrencyRepository
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.launch
import kotlin.random.Random
import kotlinx.coroutines.flow.asSharedFlow

class GachaViewModel(private val currencyRepository: CurrencyRepository) : ViewModel() {
    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    suspend fun draw(primaryCost: Int): Boolean {
        if (!currencyRepository.deductPrimaryCurrency(primaryCost, "抽卡消费")) {
            _uiMessage.emit("一级货币不足")
            return false
        }
        val baseSecondary = primaryCost * 5
        val random = Random.nextDouble()
        val multiplier = when {
            random < 0.05 -> 5.0
            random < 0.15 -> 3.0
            random < 0.35 -> 2.0
            else -> 1.0
        }
        val earned = (baseSecondary * multiplier).toInt()
        currencyRepository.addSecondaryCurrency(earned, "抽卡获得")
        val message = when (multiplier) {
            5.0 -> "✨ 大暴击！获得 ${earned} 二级货币 ✨"
            3.0 -> "⭐ 暴击！获得 ${earned} 二级货币 ⭐"
            2.0 -> "🌟 小暴击！获得 ${earned} 二级货币 🌟"
            else -> "获得 ${earned} 二级货币"
        }
        _uiMessage.emit(message)
        return true
    }
}