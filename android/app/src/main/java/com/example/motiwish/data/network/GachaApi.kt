package com.example.motiwish.data.network

import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Path

// 请求体：告诉服务器抽几次
data class GachaDrawRequest(val times: Int)

// 响应体：每一抽的详细记录 (对应后端的 GachaDrawRecord)
data class GachaDrawRecord(
    val id: Int,
    val cost_primary: Int,
    val reward_secondary: Int,
    val reward_tier: String, // "common", "rare", "epic", "legendary"
    val pity_tier: String?
)

interface GachaApi {
    @POST("api/v1/gacha/pools/{id}/draw/")
    suspend fun draw(
        @Path("id") poolId: Int,
        @Body request: GachaDrawRequest
    ): ApiResponse<List<GachaDrawRecord>>
}