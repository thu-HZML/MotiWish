package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.Wish
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.WishRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class ShopViewModel(
    private val wishRepository: WishRepository,
    private val currencyRepository: CurrencyRepository
) : ViewModel() {
    private val _wishes = MutableStateFlow<List<Wish>>(emptyList())
    val wishes: StateFlow<List<Wish>> = _wishes
    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    init {
        loadWishes()
        maybeAddSystemWishes()
    }

    private fun loadWishes() {
        wishRepository.getAllEnabledWishes().onEach { _wishes.value = it }.launchIn(viewModelScope)
    }

    private fun maybeAddSystemWishes() {
        viewModelScope.launch {
            if (_wishes.value.isEmpty()) {
                val systemWishes = listOf(
                    Wish(name ="周末电影票", costSecondary = 100, isSystem = true, custom = false),
                    Wish(name = "新书一本", costSecondary = 80, isSystem = true, custom = false),
                    Wish(name = "咖啡券", costSecondary = 50, isSystem = true, custom = false),
                    Wish(name = "游戏皮肤", costSecondary = 200, isSystem = true, custom = false)
                )
                systemWishes.forEach { wishRepository.addWish(it) }
            }
        }
    }

    fun addCustomWish(name: String, cost: Int) {
        viewModelScope.launch {
            wishRepository.addWish(Wish(name = name, costSecondary = cost, custom = true))
            _uiMessage.emit("愿望添加成功")
        }
    }

    fun updateWish(wish: Wish) {
        viewModelScope.launch { wishRepository.updateWish(wish) }
    }

    fun deleteWish(wish: Wish) {
        viewModelScope.launch {
            wishRepository.deleteWish(wish)
            _uiMessage.emit("愿望已删除")
        }
    }

    suspend fun purchaseWish(wish: Wish): Boolean {
        if (currencyRepository.deductSecondaryCurrency(wish.costSecondary, "兑换愿望: ${wish.name}")) {
            wishRepository.disableWish(wish.id)
            _uiMessage.emit("成功兑换 ${wish.name}！")
            return true
        } else {
            _uiMessage.emit("二级货币不足")
            return false
        }
    }

    fun refreshSystemWish() {
        viewModelScope.launch {
            val randomWishes = listOf(
                Wish(name = "奶茶一杯", costSecondary = 30, isSystem = true, custom = false),
                Wish(name = "健身房周卡", costSecondary = 150, isSystem = true, custom = false),
                Wish(name = "音乐会门票", costSecondary = 300, isSystem = true, custom = false),
                Wish(name = "精美笔记本", costSecondary = 60, isSystem = true, custom = false),
                Wish(name = "下午茶套餐", costSecondary = 90, isSystem = true, custom = false)
            )
            val newWish = randomWishes.random()
            wishRepository.addWish(newWish)
            _uiMessage.emit("系统刷新了新愿望：${newWish.name}")
        }
    }
}