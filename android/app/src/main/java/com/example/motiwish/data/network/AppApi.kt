package com.example.motiwish.data.network

import com.example.motiwish.data.model.Wish
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.GET
// --- 商店 API 请求和响应模型 ---

data class RedeemRequest(
    val id: Int // 传递你要购买的商品ID（后端可以不需要这个因为ID在URL里，这里作为一个占位符）
)

data class RedeemRecord(
    val id: Int,
    val cost_secondary: Int,
    val status: String
)

data class NetworkShopItem(
    val id: Int,
    val title: String,
    val description: String?,
    val price_secondary: Int,
    val inventory: Int?,       // 库存
    val item_kind: String
)
// 后端返回的是分页列表
data class PaginatedShopItems(
    val count: Int,
    val results: List<NetworkShopItem>
)
data class NetworkRedemptionRecord(
    val id: Int,
    val item: NetworkShopItem, // 之前定义好的商品实体
    val cost_secondary: Int,
    val status: String,        // requested(待处理), completed(已完成), fulfilled(已兑现), rejected(已拒绝)
    val created_at: String,    // 兑换时间
    val note: String?          // 备注
)
data class PaginatedRedemptions(
    val count: Int,
    val results: List<NetworkRedemptionRecord>
)

data class RedemptionActionRequest(
    val note: String = "",
    val refund: Boolean = false
)

// 自建商品请求相关
data class CreateShopItemRequest(
    val title: String,
    val description: String? = null,
    val rarity: String? = null,          // "common", "rare", "epic"
    val price_tier: String? = null,      // "small", "medium", "large"
    val price_secondary: Int,
    val inventory: Int? = null,
    val auto_refund_on_reject: Boolean? = null  // 可选，默认可能为 true
)

// 1. 背包中嵌套的商品详情（精确匹配后端返回的 JSON 字段）
data class NetworkInventoryItemDetail(
    val id: Int,
    val title: String,  // ✅ 后端叫 title，不能叫 name
    val category: String?,
    val catalog_key: String?,
    val cost_secondary: Int
)

// 2. 真正的背包条目
data class UserInventoryItem(
    val id: Int,
    val quantity: Int,
    val item: NetworkInventoryItemDetail // ✅ 使用专门的网络模型，拒绝混用
)

data class InventoryPaginatedResponse(
    val count: Int,
    val next: String?,
    val previous: String?,
    val results: List<UserInventoryItem> // 真正的数据数组包裹在这里
)

// ========== 愿望 AI 定价会话 ==========
data class WishPayload(
    val title: String?,        // ✅ 改为可空
    val description: String? = null,
    val tags: List<String>? = null
)

data class WishQuotePayload(
    val title: String,
    val description: String?,
    val price_tier: String,      // "small", "medium", "large"
    val price_secondary: Int,
    val rarity: String,           // "common", "rare", "epic"
    val inventory: Int,
    val reasoning: String,
    val pricing_bounds: PricingBounds?,
    val user_fit_notes: Any?   // ✅ 改为 Any? 接受字符串或数组
)

data class PricingBounds(
    val price_secondary: PriceBound,
    val price_tier: String
)

data class PriceBound(
    val min: Int,
    val max: Int,
    val recommended: Int
)

data class WishPricingSession(
    val id: Int,
    val source: String,           // "manual" or "daily_refresh"
    val status: String,           // "waiting_confirmation", "accepted", "cancelled", "failed"
    val refresh_date: String?,
    val wish_payload: WishPayload,
    val quote_payload: WishQuotePayload,
    val generated_item: NetworkShopItem?,
    val created_at: String,
    val updated_at: String
)

data class CreateWishPricingSessionRequest(
    val wish_payload: WishPayload
)

data class ConfirmWishPricingRequest(
    val action: String            // "accept" or "cancel"
)

data class WishPricingSessionResponse(
    val data: WishPricingSession,
    val success: Boolean,
    val code: String,
    val message: String
)

interface ShopApi {
    @GET("api/v1/shop/items/")
    suspend fun getShopItems(): ApiResponse<PaginatedShopItems>

    @GET("api/v1/shop/redemptions/")
    suspend fun getRedemptionHistory(): ApiResponse<PaginatedRedemptions>

    @POST("api/v1/shop/items/{id}/redeem/")
    suspend fun redeemItem(
        @Path("id") itemId: Int
    ): ApiResponse<RedeemRecord>

    @POST("api/v1/shop/redemptions/{id}/fulfill/")
    suspend fun fulfillRedemption(
        @Path("id") recordId: Int,
        @Body request: RedemptionActionRequest = RedemptionActionRequest()
    ): ApiResponse<NetworkRedemptionRecord>

    // 自建商品
    @POST("api/v1/shop/items/")
    suspend fun createShopItem(
        @Body request: CreateShopItemRequest
    ): ApiResponse<NetworkShopItem>   // 成功后返回创建的商品对象
  
    // 1. 获取背包中数量大于 0 的道具
    @GET("api/v1/shop/inventory/")
    suspend fun getUserInventory(): ApiResponse<InventoryPaginatedResponse>

    // 2. 使用背包中的道具 (调用后端的 use 接口)
    @POST("api/v1/shop/inventory/{id}/use/")
    suspend fun useInventoryItem(
        @Path("id") inventoryId: Int,
        @Body body: Map<String, String>
    ): ApiResponse<Any>

    // 创建愿望定价对话
    @POST("api/v1/ai/wish-pricing-sessions/")
    suspend fun createWishPricingSession(
        @Body request: CreateWishPricingSessionRequest
    ): WishPricingSessionResponse

    // 取消或确认愿望定价
    @POST("api/v1/ai/wish-pricing-sessions/{id}/confirm/")
    suspend fun confirmWishPricingSession(
        @Path("id") sessionId: Int,
        @Body request: ConfirmWishPricingRequest
    ): WishPricingSessionResponse

    // 获取愿望定价对话
    @GET("api/v1/ai/wish-pricing-sessions/")
    suspend fun getWishPricingSessions(): ApiResponse<PaginatedWishPricingSessions>

    /**
     * 每日刷新愿望候选（后端默认每天一次）
     * @param force 可选，强制重新生成
     * @param refreshDate 可选，指定日期 "YYYY-MM-DD"
     */
    @POST("api/v1/ai/wish-pricing-sessions/daily-refresh/")
    suspend fun getDailyWishCandidate(
        @Body request: DailyRefreshRequest
    ): WishPricingSessionResponse
}


// --- 任务 API 请求和响应模型 ---

data class TaskCompleteRequest(
    val occurrence_date: String? = null,
    val progress: Int? = null
)

data class TaskCompleteRecord(
    val id: Int,
    val status: String,
    val progress: Int
)

// 获取愿望定价请求体
data class PaginatedWishPricingSessions(
    val count: Int,
    val results: List<WishPricingSession>
)

// 获取每日专属任务请求体数据类
data class DailyRefreshRequest(
    val force: Boolean? = null,
    val refresh_date: String? = null
)

// 解析字符串组函数
fun Any?.toUserFitNotesString(): String? {
    return when (this) {
        null -> null
        is String -> this
        is List<*> -> this.joinToString(separator = "\n") { it.toString() }
        else -> this.toString()
    }
}

//interface TaskApi {
//    @POST("api/v1/tasks/tasks/{id}/complete/")
//    suspend fun completeTask(
//        @Path("id") taskId: Int,
//        @Body request: TaskCompleteRequest
//    ): ApiResponse<TaskCompleteRecord>
//}