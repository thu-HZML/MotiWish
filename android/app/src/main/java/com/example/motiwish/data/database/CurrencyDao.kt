package com.example.motiwish.data.database

import androidx.room.*
import com.example.motiwish.data.model.CurrencyBalance
import com.example.motiwish.data.model.Transaction
import kotlinx.coroutines.flow.Flow

@Dao
interface CurrencyDao {
    @Query("SELECT * FROM currency_balance WHERE id = 1")
    fun getCurrencyBalance(): Flow<CurrencyBalance?>

    @Update
    suspend fun updateCurrencyBalance(balance: CurrencyBalance)

    @Insert
    suspend fun insertTransaction(transaction: Transaction)

    @Query("SELECT * FROM transactions ORDER BY timestamp DESC")
    fun getAllTransactions(): Flow<List<Transaction>>
}