package com.example.motiwish.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.OneShotTask
import com.example.motiwish.data.model.PeriodicTask
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.TaskRepository
import com.example.motiwish.data.network.TaskOccurrence
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter

data class HistoryItem(
    val title: String,
    val date: String,
    val status: String,
    val reward: Int,
    val type: String,
    val isDeadline: Boolean = false   // 新增：是否为截止日
)

class HistoryViewModel(
    private val taskRepository: TaskRepository,
    private val currencyRepository: CurrencyRepository
) : ViewModel() {

    private val _historyItems = MutableStateFlow<List<HistoryItem>>(emptyList())
    val historyItems: StateFlow<List<HistoryItem>> = _historyItems

    // 存储已完成的任务实例（从云端获取，用于标记状态）
    private val _completedOccurrences = MutableStateFlow<Set<String>>(emptySet()) // key: "taskId_date"

    init {
        loadTaskTemplates()
        loadCompletedOccurrences() // 从云端获取已完成实例
    }

    private fun loadTaskTemplates() {
        viewModelScope.launch {
            combine(
                taskRepository.getAllActivePeriodicTasks(),
                taskRepository.getAllOneShotTasks()
            ) { periodicTasks, oneShotTasks ->
                generateHistoryItems(periodicTasks, oneShotTasks)
            }.collect { items ->
                _historyItems.value = items
            }
        }
    }

    private fun loadCompletedOccurrences() {
        viewModelScope.launch {
            val occurrences = taskRepository.getTaskHistory() // 复用之前的历史接口，获取已完成实例
            val completedSet = occurrences
                .filter { it.status == "completed" }
                .map { "${it.task.id}_${it.occurrence_date}" }
                .toSet()
            _completedOccurrences.value = completedSet
        }
    }

    private fun generateHistoryItems(periodicTasks: List<PeriodicTask>, oneShotTasks: List<OneShotTask>): List<HistoryItem> {
        val items = mutableListOf<HistoryItem>()
        val today = LocalDate.now()
        val startDate = today.minusMonths(3) // 显示最近3个月，可调整
        val endDate = today.plusMonths(3)
        Log.d("HistoryVM", "periodicTasks size: ${periodicTasks.size}, oneShotTasks size: ${oneShotTasks.size}")
        // 处理周期任务
        periodicTasks.forEach { task ->
            var currentDate = maxOf(startDate, task.createdDate ?: startDate) // 需要 PeriodicTask 添加 createdDate 字段，如果没有则用 startDate
            while (currentDate <= endDate) {
                if (shouldShowOnDate(task, currentDate)) {
                    val isCompleted = _completedOccurrences.value.contains("${task.id}_$currentDate")
                    items.add(HistoryItem(
                        title = task.name,
                        date = currentDate.toString(),
                        status = if (isCompleted) "已完成" else "待完成",
                        reward = if (isCompleted) task.rewardAmount else 0,
                        type = "周期"
                    ))
                }
                currentDate = currentDate.plusDays(1)
            }
        }

        // 处理一次性任务
        oneShotTasks.forEach { task ->
            val start = maxOf(startDate, task.createdDate ?: startDate)
            val end = minOf(endDate, task.deadline.toLocalDate())
            var currentDate = start
            while (currentDate <= end) {
                val isCompleted = _completedOccurrences.value.contains("${task.id}_$currentDate") ||
                        (currentDate == task.deadline.toLocalDate() && task.status == "COMPLETED")
                val isDeadline = currentDate == task.deadline.toLocalDate()   // 标记截止日
                items.add(HistoryItem(
                    title = task.name,
                    date = currentDate.toString(),
                    status = if (isCompleted) "已完成" else "待完成",
                    reward = if (isCompleted) task.reward else 0,
                    type = "一次性",
                    isDeadline = isDeadline
                ))
                currentDate = currentDate.plusDays(1)
            }
        }

        return items.sortedByDescending { it.date }
    }

    private fun shouldShowOnDate(task: PeriodicTask, date: LocalDate): Boolean {
        return when (task.type) {
            "DAILY" -> true
            "WEEKLY" -> task.dayOfWeek == date.dayOfWeek.value
            "MONTHLY" -> task.dayOfMonth == date.dayOfMonth
            else -> false
        }
    }

    // 刷新（手动调用）
    fun refresh() {
        loadTaskTemplates()
        loadCompletedOccurrences()
    }

    /**
     * 获取指定月份的任务分组数据（按日期）
     * 此方法无需改动，因为 historyItems 已经是从云端获取的数据
     */
    fun getTasksByMonth(yearMonth: YearMonth): Flow<Map<LocalDate, List<HistoryItem>>> {
        return historyItems.map { items ->
            items.filter { item ->
                try {
                    val date = LocalDate.parse(item.date)
                    YearMonth.from(date) == yearMonth
                } catch (e: Exception) {
                    false
                }
            }.groupBy { LocalDate.parse(it.date) }
        }
    }
}