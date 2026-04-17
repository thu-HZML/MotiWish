package com.example.motiwish.data.database

import androidx.room.*
import com.example.motiwish.data.model.Wish
import kotlinx.coroutines.flow.Flow

@Dao
interface WishDao {
    @Insert
    suspend fun insertWish(wish: Wish)

    @Update
    suspend fun updateWish(wish: Wish)

    @Delete
    suspend fun deleteWish(wish: Wish)

    @Query("SELECT * FROM wishes WHERE enabled = 1 ORDER BY costSecondary ASC")
    fun getAllEnabledWishes(): Flow<List<Wish>>

    @Query("SELECT * FROM wishes WHERE id = :wishId")
    suspend fun getWishById(wishId: Int): Wish?

    @Query("UPDATE wishes SET enabled = 0 WHERE id = :wishId")
    suspend fun disableWish(wishId: Int)
}