package com.example.motiwish.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.TaskRepository
import com.example.motiwish.data.network.RemoteTask
import com.example.motiwish.data.network.TaskOccurrence
import kotlinx.coroutines.async
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
    val isDeadline: Boolean = false
)

class HistoryViewModel(
    private val taskRepository: TaskRepository,
    private val currencyRepository: CurrencyRepository
) : ViewModel() {

    private val _historyItems = MutableStateFlow<List<HistoryItem>>(emptyList())
    val historyItems: StateFlow<List<HistoryItem>> = _historyItems

    private fun loadHistory() {
        viewModelScope.launch {
            try {
                // 并行获取任务模板和已完成实例
                val tasksDeferred = async { taskRepository.fetchAllActiveTasksFromCloud() }
                val occurrencesDeferred = async { taskRepository.getTaskHistory() }
                val allTasks = tasksDeferred.await()
                val allOccurrences = occurrencesDeferred.await()

                // 构建已完成实例的快速查找 Map: "taskId_date" -> TaskOccurrence
                val occurrenceMap = allOccurrences.associateBy { "${it.task.id}_${it.occurrence_date}" }

                val items = generateHistoryItems(allTasks, occurrenceMap)
                _historyItems.value = items
                Log.d("HistoryVM", "Loaded ${items.size} history items from cloud")
            } catch (e: Exception) {
                Log.e("HistoryVM", "Failed to load history", e)
                _historyItems.value = emptyList()
            }
        }
    }

    /**
     * 根据云端任务模板和已有实例生成日历项
     * @param tasks 云端任务模板列表
     * @param occurrenceMap 已有实例映射，key = "taskId_date"
     */
    private fun generateHistoryItems(
        tasks: List<RemoteTask>,
        occurrenceMap: Map<String, TaskOccurrence>
    ): List<HistoryItem> {
        val items = mutableListOf<HistoryItem>()
        val today = LocalDate.now()
        val startDate = today.minusMonths(3)
        val endDate = today.plusMonths(3)

        for (task in tasks) {
            // 判断任务类型：一次性 vs 周期
            val isOneTime = task.task_type == "one_time"

            if (isOneTime) {
                // 一次性任务：从 starts_on 或 created_at 到 due_at（含截止日）
                val taskStartDate = parseDate(task.starts_on) ?: parseDate(task.created_at) ?: startDate
                val dueDate = parseDate(task.due_at) ?: continue
                val start = maxOf(startDate, taskStartDate)
                val end = minOf(endDate, dueDate)
                var currentDate = start
                while (currentDate <= end) {
                    val key = "${task.id}_$currentDate"
                    val occurrence = occurrenceMap[key]
                    val status = occurrence?.status ?: "pending"
                    val isCompleted = status == "completed"
                    val isDeadline = currentDate == dueDate
                    items.add(
                        HistoryItem(
                            title = task.title,
                            date = currentDate.toString(),
                            status = when (status) {
                                "pending" -> "待完成"
                                "completed" -> "已完成"
                                "missed" -> "已错过"
                                "cancelled" -> "已取消"
                                else -> status
                            },
                            reward = if (isCompleted) task.reward_primary else 0,
                            type = "一次性",
                            isDeadline = isDeadline
                        )
                    )
                    currentDate = currentDate.plusDays(1)
                }
            } else {
                // 周期任务：根据 recurrence 和 weekdays/month_days 判断
                val taskStartDate = parseDate(task.starts_on) ?: parseDate(task.created_at) ?: startDate
                var currentDate = maxOf(startDate, taskStartDate)
                while (currentDate <= endDate) {
                    if (shouldShowRecurringTask(task, currentDate)) {
                        val key = "${task.id}_$currentDate"
                        val occurrence = occurrenceMap[key]
                        val status = occurrence?.status ?: "pending"
                        val isCompleted = status == "completed"
                        items.add(
                            HistoryItem(
                                title = task.title,
                                date = currentDate.toString(),
                                status = when (status) {
                                    "pending" -> "待完成"
                                    "completed" -> "已完成"
                                    "missed" -> "已错过"
                                    "cancelled" -> "已取消"
                                    else -> status
                                },
                                reward = if (isCompleted) task.reward_primary else 0,
                                type = "周期",
                                isDeadline = false
                            )
                        )
                    }
                    currentDate = currentDate.plusDays(1)
                }
            }
        }
        return items.sortedByDescending { it.date }
    }

    /**
     * 判断周期任务在指定日期是否应该出现
     * 根据任务字段 recurrence + weekdays/month_days
     */
    private fun shouldShowRecurringTask(task: RemoteTask, date: LocalDate): Boolean {
        return when (task.recurrence) {
            "daily" -> true
            "weekly" -> {
                val weekdays = task.weekdays ?: return false
                // 后端 weekdays: 0=周一 ~ 6=周日，LocalDate.dayOfWeek 周一=1 ~ 周日=7，转换到0-6
                val todayWeekday = when (date.dayOfWeek.value) {
                    1 -> 0   // 周一
                    2 -> 1   // 周二
                    3 -> 2
                    4 -> 3
                    5 -> 4
                    6 -> 5
                    7 -> 6
                    else -> -1
                }
                weekdays.contains(todayWeekday)
            }
            "monthly" -> {
                val monthDays = task.month_days ?: return false
                monthDays.contains(date.dayOfMonth)
            }
            else -> false
        }
    }

    /**
     * 解析 ISO 日期字符串（支持 "yyyy-MM-dd" 或 "yyyy-MM-ddTHH:mm:ssZ"）
     */
    private fun parseDate(dateStr: String?): LocalDate? {
        if (dateStr.isNullOrEmpty()) return null
        return try {
            if (dateStr.length >= 10) LocalDate.parse(dateStr.substring(0, 10))
            else null
        } catch (e: Exception) {
            null
        }
    }

    /**
     * 手动刷新
     */
    fun refresh() {
        loadHistory()
    }

    /**
     * 获取指定月份的任务分组（按日期）
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