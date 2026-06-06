package com.example.motiwish.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.Wish
import com.example.motiwish.data.model.WishDraft
import com.example.motiwish.data.network.ConfirmWishPricingRequest
import com.example.motiwish.data.network.CreateShopItemRequest
import com.example.motiwish.data.network.CreateWishPricingSessionRequest
import com.example.motiwish.data.network.DailyRefreshRequest
import com.example.motiwish.data.network.ShopApi // 新增
import com.example.motiwish.data.network.WishPayload
import com.example.motiwish.data.network.WishPricingSession
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.WishRepository
import com.google.gson.GsonBuilder
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import org.json.JSONObject
import retrofit2.HttpException

class ShopViewModel(
    private val currencyRepository: CurrencyRepository,
    private val shopApi: ShopApi
) : ViewModel() {
    private val _wishes = MutableStateFlow<List<Wish>>(emptyList())
    val wishes: StateFlow<List<Wish>> = _wishes

    private val _uiMessage = MutableSharedFlow<String>()
    val uiMessage: SharedFlow<String> = _uiMessage.asSharedFlow()

    // 愿望草稿管理
    private val _wishDrafts = MutableStateFlow<List<WishDraft>>(emptyList())
    val wishDrafts: StateFlow<List<WishDraft>> = _wishDrafts

    private val _selectedWishDraftForPricing = MutableStateFlow<Pair<Int, WishPricingSession>?>(null)
    val selectedWishDraftForPricing: StateFlow<Pair<Int, WishPricingSession>?> = _selectedWishDraftForPricing

    private var nextWishDraftId = 1

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
        } catch (e: HttpException) {
            // ✅ 专门拦截 HTTP 400 等后端主动报的错误
            var errorMsg = "余额不足或商品无法兑换"
            try {
                val errorBody = e.response()?.errorBody()?.string()
                if (!errorBody.isNullOrBlank()) {
                    val json = JSONObject(errorBody)
                    // 根据你后端的常见返回格式提取文字
                    when {
                        json.has("detail") -> errorMsg = json.getString("detail")
                        json.has("error") -> errorMsg = json.getString("error")
                        json.has("message") -> errorMsg = json.getString("message")
                        json.has("non_field_errors") -> errorMsg = json.getJSONArray("non_field_errors").getString(0)
                    }
                }
            } catch (ex: Exception) {
                // 解析失败就用默认文案
            }

            // 清理掉可能存在的括号或多余符号（像我们之前做的那样）
            val cleanMsg = errorMsg
                .replace(Regex("[\\[\\]{}()\"']"), "") // 砍掉各种括号引号
                .replace("。", "")                    // 砍掉句号
                .replace("secondary", "")              // 👈 核心修改：抹除 "secondary"
                .replace("primary", "")                // 👈 顺手也把一级货币的 "primary" 抹除，防患于未然
                .trim()                                // 去掉首尾多余空格

            _uiMessage.emit("兑换失败: $cleanMsg")

            return false
        } catch (e: Exception) {
            // 真正的网络断开、超时等异常才会走到这里
            _uiMessage.emit("网络异常，请检查网络连接")
            return false
        }
    }

    /**
     * 获取今日专属愿望候选（每日刷新）
     * 如果后端返回已有会话（status = waiting_confirmation），则自动加入到草稿列表
     */
    fun fetchDailyRefreshWish(force: Boolean = false) {
        viewModelScope.launch {
            try {
                val request = DailyRefreshRequest(force = if (force) true else null)
                val response = shopApi.getDailyWishCandidate(request)

                if (response.success && response.data.status == "waiting_confirmation") {
                    val session = response.data
                    // ✅ 从 quote_payload 中获取标题
                    val title = session.quote_payload.title
                    if (title.isNullOrBlank()) {
                        _uiMessage.emit("获取的愿望标题为空，请稍后重试")
                        return@launch
                    }
                    val exists = _wishDrafts.value.any { it.sessionId == session.id }
                    if (!exists) {
                        val draftId = nextWishDraftId++
                        val draft = WishDraft(
                            id = draftId,
                            sessionId = session.id,
                            title = title,
                            description = session.quote_payload.description,
                            tags = session.wish_payload.tags,
                            status = "quoted",
                            quotePayload = session.quote_payload,
                            createdAt = System.currentTimeMillis(),
                            isDailyRefresh = true
                        )
                        _wishDrafts.value = _wishDrafts.value + draft
                        _uiMessage.emit("获取今日专属愿望成功，请确认")
                    } else {
                        _uiMessage.emit("今日专属愿望已在列表中")
                    }
                } else {
                    _uiMessage.emit("获取失败: ${response.message}")
                }
            } catch (e: Exception) {
                _uiMessage.emit("网络错误: ${e.message}")
            }
        }
    }


    // 创建愿望定价草稿（异步）
    fun createWishDraftAsync(
        title: String,
        description: String?,
        tags: List<String>? = null
    ) {
        val draftId = nextWishDraftId++
        val draft = WishDraft(
            id = draftId,
            sessionId = null,
            title = title,
            description = description,
            tags = tags,
            status = "pricing",
            quotePayload = null,
            createdAt = System.currentTimeMillis()
        )
        _wishDrafts.value = _wishDrafts.value + draft

        viewModelScope.launch {
            try {
                val request = CreateWishPricingSessionRequest(
                    wish_payload = WishPayload(title, description, tags)
                )
                val response = shopApi.createWishPricingSession(request)
                if (response.success && response.data.status == "waiting_confirmation") {
                    val session = response.data
                    _wishDrafts.value = _wishDrafts.value.map {
                        if (it.id == draftId) {
                            it.copy(
                                sessionId = session.id,
                                status = "quoted",
                                quotePayload = session.quote_payload
                            )
                        } else it
                    }
                    _uiMessage.emit("愿望定价完成，请确认")
                } else {
                    _wishDrafts.value = _wishDrafts.value.filter { it.id != draftId }
                    _uiMessage.emit("愿望定价失败: ${response.message}")
                }
            } catch (e: Exception) {
                _wishDrafts.value = _wishDrafts.value.filter { it.id != draftId }
                _uiMessage.emit("网络错误: ${e.message}")
            }
        }
    }

    // 显示定价对话框
    fun showWishPricingDialog(draftId: Int) {
        val draft = _wishDrafts.value.find { it.id == draftId }
        if (draft?.status == "quoted" && draft.quotePayload != null && draft.sessionId != null) {
            // 构建临时会话对象用于展示
            val tempSession = WishPricingSession(
                id = draft.sessionId,
                source = "manual",
                status = "waiting_confirmation",
                refresh_date = null,
                wish_payload = WishPayload(draft.title, draft.description, draft.tags),
                quote_payload = draft.quotePayload,
                generated_item = null,
                created_at = "",
                updated_at = ""
            )
            _selectedWishDraftForPricing.value = Pair(draftId, tempSession)
        }
    }

    // 取消定价对话框
    fun dismissWishPricingDialog() {
        _selectedWishDraftForPricing.value = null
    }

    // 接受定价并创建商品（需支持每日愿望）
    fun acceptWishPricing(draftId: Int) {
        viewModelScope.launch {
            val draft = _wishDrafts.value.find { it.id == draftId }
            if (draft?.sessionId == null) {
                _uiMessage.emit("草稿不存在")
                dismissWishPricingDialog()
                return@launch
            }
            dismissWishPricingDialog()
            try {
                val response = shopApi.confirmWishPricingSession(
                    draft.sessionId,
                    ConfirmWishPricingRequest("accept")
                )
                if (response.success && response.data.status == "accepted") {
                    _wishDrafts.value = _wishDrafts.value.filter { it.id != draftId }
                    fetchRealShopItems()
                    _uiMessage.emit("愿望商品创建成功！")
                } else {
                    _uiMessage.emit("创建失败: ${response.message}")
                }
            } catch (e: Exception) {
                _uiMessage.emit("网络错误: ${e.message}")
            }
        }
    }

    // 取消定价（同 accept 中的取消逻辑）
    fun cancelWishPricing(draftId: Int) {
        viewModelScope.launch {
            val draft = _wishDrafts.value.find { it.id == draftId }
            if (draft?.sessionId != null) {
                try {
                    shopApi.confirmWishPricingSession(
                        draft.sessionId,
                        ConfirmWishPricingRequest("cancel")
                    )
                } catch (e: Exception) {
                    // 忽略网络错误，仍删除本地草稿
                }
            }
            _wishDrafts.value = _wishDrafts.value.filter { it.id != draftId }
            dismissWishPricingDialog()
            _uiMessage.emit("已取消创建")
        }
    }
}