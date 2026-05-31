package com.example.motiwish.data.network

import retrofit2.http.GET

// 1. 根据后端实体映射的钱包资产模型
data class NetworkWallet(
    val id: Int,
    val primary_balance: Int,
    val secondary_balance: Int,
    val primary_debt: Int,
    val is_in_debt: Boolean,
    val primary_debt_floor: Int
)

// 2. 根据后端实体映射的资产流水日志模型
data class NetworkTransaction(
    val id: Int,
    val currency_type: String, // "primary" 或 "secondary"
    val reason: String,        // "task_reward", "gacha_cost" 等
    val delta: Int,            // 变动绝对值，正数为存，负数为取
    val balance_before: Int,
    val balance_after: Int,
    val memo: String?,
    val created_at: String     // ISO 时间字符串
)

interface WalletApi {
    @GET("api/v1/wallet/")
    suspend fun getWalletBalance(): ApiResponse<NetworkWallet>

    @GET("api/v1/wallet/transactions/")
    suspend fun getTransactions(): ApiResponse<List<NetworkTransaction>>
}