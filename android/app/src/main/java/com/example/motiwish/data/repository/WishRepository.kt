package com.example.motiwish.data.repository

import com.example.motiwish.data.database.WishDao
import com.example.motiwish.data.model.Wish
import kotlinx.coroutines.flow.Flow

class WishRepository(private val wishDao: WishDao) {
    suspend fun addWish(wish: Wish) = wishDao.insertWish(wish)
    suspend fun updateWish(wish: Wish) = wishDao.updateWish(wish)
    suspend fun deleteWish(wish: Wish) = wishDao.deleteWish(wish)
    fun getAllEnabledWishes(): Flow<List<Wish>> = wishDao.getAllEnabledWishes()
    suspend fun getWishById(id: Int): Wish? = wishDao.getWishById(id)
    suspend fun disableWish(id: Int) = wishDao.disableWish(id)
}