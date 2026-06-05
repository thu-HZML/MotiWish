package com.example.motiwish.data.network

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

//interface TaskApi {
//    @POST("api/v1/tasks/tasks/{id}/complete/")
//    suspend fun completeTask(
//        @Path("id") taskId: Int,
//        @Body request: TaskCompleteRequest
//    ): ApiResponse<TaskCompleteRecord>
//}