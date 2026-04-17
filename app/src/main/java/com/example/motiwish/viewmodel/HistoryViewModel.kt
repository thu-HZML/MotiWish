package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.repository.CurrencyRepository
import com.example.motiwish.data.repository.TaskRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

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
            val items = mutableListOf<HistoryItem>()
            taskRepository.getAllDailyMetrics().collect { metrics ->
                items.clear()
                metrics.forEach { metric ->
                    items.add(HistoryItem("日常任务 - ${metric.date}", metric.date.toString(), if (metric.evaluated) "已完成" else "未填写", metric.reward, "日常"))
                }
                taskRepository.getAllPeriodicTaskCompletions().collect { completions ->
                    completions.forEach { completion ->
                        val task = taskRepository.getPeriodicTaskById(completion.taskId)
                        items.add(HistoryItem("周期任务: ${task?.name ?: "未知"}", completion.completedDate.toString(), "已完成", completion.rewardEarned, "周期"))
                    }
                }
                taskRepository.getAllOneShotTasks().collect { oneShots ->
                    oneShots.forEach { task ->
                        val statusText = when (task.status) {
                            "COMPLETED" -> "已完成"
                            "FAILED" -> "失败"
                            else -> "进行中"
                        }
                        items.add(HistoryItem(task.name, task.deadline.toLocalDate().toString(), statusText, task.reward - task.penalty, "一次性"))
                    }
                }
                _historyItems.value = items.sortedByDescending { it.date }
            }
        }
    }
}