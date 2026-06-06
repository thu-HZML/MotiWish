package com.example.motiwish.data.model

import com.example.motiwish.data.network.WishQuotePayload

data class WishDraft(
    val id: Int,                      // 本地临时ID
    val sessionId: Int?,              // 后端会话ID
    val title: String,
    val description: String?,
    val tags: List<String>?,
    val status: String,               // "pricing", "quoted", "accepted", "cancelled", "failed"
    val quotePayload: WishQuotePayload?,
    val createdAt: Long,
    val isDailyRefresh: Boolean = false   // 新增：标识是否为每日专属愿望
)