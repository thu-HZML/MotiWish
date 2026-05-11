package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.TaskRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter

data class HistoryItem(val title: String, val date: String, val status: String, val reward: Int, val type: String)

class HistoryViewModel(
    private val taskRepository: TaskRepository,
    private val currencyRepository: CurrencyRepository
) : ViewModel() {
    private val _historyItems = MutableStateFlow<List<HistoryItem>>(emptyList())
    val historyItems: StateFlow<List<HistoryItem>> = _historyItems

    init {
        loadHistory()
    }

    private fun loadHistory() {
        viewModelScope.launch {
            val dailyMetricsFlow = taskRepository.getAllDailyMetrics()
            val completionsFlow = taskRepository.getAllPeriodicTaskCompletions()
            val oneShotTasksFlow = taskRepository.getAllOneShotTasks()

            combine(dailyMetricsFlow, completionsFlow, oneShotTasksFlow) { metrics, completions, oneShots ->
                val items = mutableListOf<HistoryItem>()

                // 日常指标
                metrics.forEach { metric ->
                    items.add(HistoryItem(
                        title = "日常任务 - ${metric.date}",
                        date = metric.date.toString(),
                        status = if (metric.evaluated) "已完成" else "未填写",
                        reward = metric.reward,
                        type = "日常"
                    ))
                }

                // 周期任务完成记录
                completions.forEach { completion ->
                    val task = taskRepository.getPeriodicTaskById(completion.taskId)
                    items.add(HistoryItem(
                        title = "周期任务: ${task?.name ?: "未知"}",
                        date = completion.completedDate.toString(),
                        status = "已完成",
                        reward = completion.rewardEarned,
                        type = "周期"
                    ))
                }

                // 一次性任务
                oneShots.forEach { task ->
                    val statusText = when (task.status) {
                        "COMPLETED" -> "已完成"
                        "FAILED" -> "失败"
                        else -> "进行中"
                    }
                    items.add(HistoryItem(
                        title = task.name,
                        date = task.deadline.toLocalDate().toString(),
                        status = statusText,
                        reward = task.reward - task.penalty,
                        type = "一次性"
                    ))
                }

                items.sortedByDescending { it.date }
            }.collect { sortedItems ->
                _historyItems.value = sortedItems
            }
        }
    }

    /**
     * 获取指定月份的任务分组数据（按日期）
     * @param yearMonth 要查询的年月
     * @return Flow<Map<LocalDate, List<HistoryItem>>> 当月每一天的任务列表
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