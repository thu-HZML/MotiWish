// TaskDraft.kt
package com.example.motiwish.data.model

import com.example.motiwish.data.network.QuotePayload
import java.time.LocalDateTime

data class TaskDraft(
    val id: Int,                     // 本地唯一标识
    val sessionId: Int?,             // 定价会话 ID（请求成功后填充）
    val title: String,
    val description: String?,
    val taskType: String,
    val recurrence: String?,
    val weekdays: List<Int>?,
    val monthDays: List<Int>?,
    val dueAt: LocalDateTime?,
    val settlementTrack: String,
    val estimatedFocusMinutes: Int?,
    val status: String,              // "pricing", "quoted", "repricing"
    val quotePayload: QuotePayload?, // 成功后的报价
    val createdAt: Long
)