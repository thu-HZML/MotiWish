package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.Wish
import com.example.motiwish.data.network.ShopApi // 新增
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.WishRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class ShopViewModel(
    private val wishRepository: WishRepository,
    private val currencyRepository: CurrencyRepository,
    private val shopApi: ShopApi // 新增网络依赖
) : ViewModel() {
    private val _wishes = MutableStateFlow<List<Wish>>(emptyList())
    val wishes: StateFlow<List<Wish>> = _wishes
    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    init {
        //fetchRealShopItems()
    }
    fun fetchRealShopItems() {
        viewModelScope.launch {
            try {
                val response = shopApi.getShopItems()
                if (response.success && response.data != null) {
                    // 把服务器的 NetworkShopItem 转换成你 UI 用的 Wish 类
                    val realWishes = response.data.results.map { networkItem ->
                        Wish(
                            id = networkItem.id, // 【极其关键】：一定要用服务器的 ID！
                            name = networkItem.title,
                            costSecondary = networkItem.price_secondary,
                            isSystem = true,
                            custom = false
                        )
                    }
                    _wishes.value = realWishes
                }
            } catch (e: Exception) {
                _uiMessage.emit("获取商店列表失败，请检查网络")
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

    // 【修改点】：使用服务器接口购买愿望
    suspend fun purchaseWish(wish: Wish): Boolean {
        try {
            val response = shopApi.redeemItem(wish.id)
            if (response.success) {
                // 兑换成功，刷新钱包
                currencyRepository.refreshWalletFromServer()
                _uiMessage.emit("成功兑换 ${wish.name}！")
                // 兑换完最好重新拉取一下商品列表，刷新库存状态
                fetchRealShopItems()
                return true
            } else {
                _uiMessage.emit("兑换失败: ${response.message}")
                return false
            }
        } catch (e: Exception) {
            _uiMessage.emit("网络异常，兑换失败")
            return false
        }
    }
}