package com.example.motiwish.data.database

import androidx.room.*
import com.example.motiwish.data.model.*
import kotlinx.coroutines.flow.Flow
import java.time.LocalDate
import java.time.LocalDateTime

@Dao
interface TaskDao {
    @Insert
    suspend fun insertDailyMetric(metric: DailyMetric)

    @Update
    suspend fun updateDailyMetric(metric: DailyMetric)

    @Query("SELECT * FROM daily_metrics WHERE date = :date")
    suspend fun getDailyMetricByDate(date: LocalDate): DailyMetric?

    @Query("SELECT * FROM daily_metrics ORDER BY date DESC")
    fun getAllDailyMetrics(): Flow<List<DailyMetric>>

    @Insert
    suspend fun insertPeriodicTask(task: PeriodicTask)

    @Update
    suspend fun updatePeriodicTask(task: PeriodicTask)

    @Delete
    suspend fun deletePeriodicTask(task: PeriodicTask)

    @Query("SELECT * FROM periodic_tasks WHERE active = 1")
    fun getAllActivePeriodicTasks(): Flow<List<PeriodicTask>>

    @Query("SELECT * FROM periodic_tasks WHERE id = :taskId")
    suspend fun getPeriodicTaskById(taskId: Int): PeriodicTask?

    @Insert
    suspend fun insertPeriodicTaskCompletion(completion: PeriodicTaskCompletion)

    @Query("SELECT * FROM periodic_task_completions WHERE taskId = :taskId AND completedDate = :date")
    suspend fun getPeriodicTaskCompletion(taskId: Int, date: LocalDate): PeriodicTaskCompletion?

    @Query("SELECT * FROM periodic_task_completions ORDER BY completedDate DESC")
    fun getAllPeriodicTaskCompletions(): Flow<List<PeriodicTaskCompletion>>

    @Insert
    suspend fun insertOneShotTask(task: OneShotTask)

    @Update
    suspend fun updateOneShotTask(task: OneShotTask)

    @Delete
    suspend fun deleteOneShotTask(task: OneShotTask)

    @Query("SELECT * FROM one_shot_tasks ORDER BY deadline ASC")
    fun getAllOneShotTasks(): Flow<List<OneShotTask>>

    @Query("SELECT * FROM one_shot_tasks WHERE id = :taskId")
    suspend fun getOneShotTaskById(taskId: Int): OneShotTask?
}