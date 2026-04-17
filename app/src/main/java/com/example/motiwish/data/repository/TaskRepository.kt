package com.example.motiwish.data.repository

import com.example.motiwish.data.database.TaskDao
import com.example.motiwish.data.model.*
import kotlinx.coroutines.flow.Flow
import java.time.LocalDate

class TaskRepository(private val taskDao: TaskDao) {
    suspend fun getDailyMetricByDate(date: LocalDate): DailyMetric? = taskDao.getDailyMetricByDate(date)

    suspend fun saveDailyMetric(metric: DailyMetric) {
        if (metric.id == 0) taskDao.insertDailyMetric(metric)
        else taskDao.updateDailyMetric(metric)
    }

    fun getAllDailyMetrics(): Flow<List<DailyMetric>> = taskDao.getAllDailyMetrics()

    suspend fun addPeriodicTask(task: PeriodicTask) = taskDao.insertPeriodicTask(task)
    suspend fun updatePeriodicTask(task: PeriodicTask) = taskDao.updatePeriodicTask(task)
    suspend fun deletePeriodicTask(task: PeriodicTask) = taskDao.deletePeriodicTask(task)
    fun getAllActivePeriodicTasks(): Flow<List<PeriodicTask>> = taskDao.getAllActivePeriodicTasks()
    suspend fun getPeriodicTaskById(id: Int): PeriodicTask? = taskDao.getPeriodicTaskById(id)

    suspend fun completePeriodicTask(taskId: Int, date: LocalDate, reward: Int) {
        val completion = PeriodicTaskCompletion(taskId = taskId, completedDate = date, rewardEarned = reward)
        taskDao.insertPeriodicTaskCompletion(completion)
    }

    suspend fun isPeriodicTaskCompletedToday(taskId: Int, date: LocalDate): Boolean {
        return taskDao.getPeriodicTaskCompletion(taskId, date) != null
    }

    fun getAllPeriodicTaskCompletions(): Flow<List<PeriodicTaskCompletion>> = taskDao.getAllPeriodicTaskCompletions()

    suspend fun addOneShotTask(task: OneShotTask) = taskDao.insertOneShotTask(task)
    suspend fun updateOneShotTask(task: OneShotTask) = taskDao.updateOneShotTask(task)
    suspend fun deleteOneShotTask(task: OneShotTask) = taskDao.deleteOneShotTask(task)
    fun getAllOneShotTasks(): Flow<List<OneShotTask>> = taskDao.getAllOneShotTasks()
    suspend fun getOneShotTaskById(id: Int): OneShotTask? = taskDao.getOneShotTaskById(id)
}