package com.example.motiwish.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.Wish
import com.example.motiwish.data.network.CreateShopItemRequest
import com.example.motiwish.data.network.ShopApi // 新增
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.WishRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class ShopViewModel(
    private val currencyRepository: CurrencyRepository,
    private val shopApi: ShopApi
) : ViewModel() {
    private val _wishes = MutableStateFlow<List<Wish>>(emptyList())
    val wishes: StateFlow<List<Wish>> = _wishes

    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    init {
        fetchRealShopItems()
    }

    fun fetchRealShopItems() {
        viewModelScope.launch {
            try {
                val response = shopApi.getShopItems()
                if (response.success && response.data != null) {
                    val realWishes = response.data.results.map { networkItem ->
                        Wish(
                            id = networkItem.id,
                            name = networkItem.title,
                            costSecondary = networkItem.price_secondary,
                            isSystem = true,          // 后端商品视为系统商品（不可本地编辑）
                            custom = false,
                            inventory = networkItem.inventory
                        )
                    }
                    _wishes.value = realWishes
                } else {
                    _uiMessage.emit("获取商品失败: ${response.message}")
                }
            } catch (e: Exception) {
                _uiMessage.emit("网络错误: ${e.message}")
            }
        }
    }

    suspend fun createCustomShopItem(
        title: String,
        description: String?,
        priceSecondary: Int,
        priceTier: String,
        rarity: String,
        inventory: Int?,
        autoRefund: Boolean = true
    ): Boolean {
        Log.d("ShopViewModel", "开始创建商品: title=$title, price=$priceSecondary")
        return try {
            val request = CreateShopItemRequest(
                title = title,
                description = description,
                price_tier = priceTier,
                price_secondary = priceSecondary,
                rarity = rarity,
                inventory = inventory,
                auto_refund_on_reject = autoRefund
            )
            val response = shopApi.createShopItem(request)
            Log.d("ShopViewModel", "API响应: success=${response.success}, message=${response.message}")
            if (response.success) {
                _uiMessage.emit("自定义商品创建成功！")
                fetchRealShopItems()
                true
            } else {
                _uiMessage.emit("创建失败: ${response.message}")
                false
            }
        } catch (e: retrofit2.HttpException) {
            val errorBody = e.response()?.errorBody()?.string()
            Log.e("ShopViewModel", "HTTP ${e.code()} - $errorBody", e)
            _uiMessage.emit("创建失败: HTTP ${e.code()} - ${errorBody ?: "未知错误"}")
            false
        } catch (e: Exception) {
            Log.e("ShopViewModel", "创建商品异常", e)
            _uiMessage.emit("网络异常: ${e.message}")
            false
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