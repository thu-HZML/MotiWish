package com.example.motiwish.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.time.LocalDate
import java.time.LocalDateTime

@Entity(tableName = "daily_metrics")
data class DailyMetric(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    val date: LocalDate,
    var wakeUpTime: String = "",
    var sleepTime: String = "",
    var phoneUsageMinutes: Int = 0,
    var waterCups: Int = 0,
    var reward: Int = 0,
    var evaluated: Boolean = false,
    var feedback: String = ""   // 新增
)

@Entity(tableName = "periodic_tasks")
data class PeriodicTask(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    val name: String,
    val type: String,
    val dayOfWeek: Int? = null,
    val dayOfMonth: Int? = null,
    val rewardAmount: Int,
    val penaltyAmount: Int,
    val active: Boolean = true,
    val createdDate: LocalDate = LocalDate.now()   // 新增字段，默认值为今天
)

@Entity(tableName = "periodic_task_completions")
data class PeriodicTaskCompletion(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    val taskId: Int,
    val completedDate: LocalDate,
    val rewardEarned: Int
)

@Entity(tableName = "one_shot_tasks")
data class OneShotTask(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    val name: String,
    val description: String,
    val deadline: LocalDateTime,
    var progressTarget: Int = 0,                    // 用于普通任务的进度目标，探索任务复用为预计专注分钟数
    var progress: Int = 0,                          // 用于普通任务的进度百分比，探索任务复用为已专注分钟数
    var status: String = "ACTIVE",
    var reward: Int = 0,
    var penalty: Int = 0,
    var evaluated: Boolean = false,
    val createdDate: LocalDate = LocalDate.now(),   // 新增字段，默认值为今天
    var settlementTrack: String = "regular",        // 是否为探索任务
    var estimatedFocusMinutes: Int? = null,          // 预估探索时长
    val actualReward: Int? = null,   // 实际获得奖励
    val actualPenalty: Int? = null   // 实际扣除惩罚
)

@Entity(tableName = "transactions")
data class Transaction(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    val amount: Int,
    val currencyType: String,
    val type: String,
    val source: String,
    val timestamp: LocalDateTime
)

@Entity(tableName = "wishes")
data class Wish(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    val name: String,
    val costSecondary: Int,
    val isSystem: Boolean = false,
    val custom: Boolean = true,
    val enabled: Boolean= true,
    val inventory: Int? = null
)

@Entity(tableName = "currency_balance")
data class CurrencyBalance(
    @PrimaryKey(autoGenerate = false)
    val id: Int = 1,
    var primaryCurrency: Int = 0,
    var secondaryCurrency: Int = 0
)