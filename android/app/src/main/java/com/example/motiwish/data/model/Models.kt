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
    var wakeUpTime: String,
    var sleepTime: String,
    var phoneUsageMinutes: Int,
    var waterCups: Int,
    var reward: Int = 0,
    var evaluated: Boolean = false
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
    val active: Boolean = true
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
    var progress: Int = 0,
    var status: String = "ACTIVE",
    var reward: Int = 0,
    var penalty: Int = 0,
    var evaluated: Boolean = false
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
    val enabled: Boolean = true
)

@Entity(tableName = "currency_balance")
data class CurrencyBalance(
    @PrimaryKey(autoGenerate = false)
    val id: Int = 1,
    var primaryCurrency: Int = 0,
    var secondaryCurrency: Int = 0
)