package com.example.motiwish.data.repository

import com.example.motiwish.data.database.CurrencyDao
import com.example.motiwish.data.model.CurrencyBalance
import com.example.motiwish.data.model.Transaction
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import java.time.LocalDateTime

class CurrencyRepository(private val currencyDao: CurrencyDao) {
    fun getCurrencyBalance(): Flow<CurrencyBalance?> = currencyDao.getCurrencyBalance()

    suspend fun addPrimaryCurrency(amount: Int, source: String) {
        val balance = currencyDao.getCurrencyBalance().first() ?: CurrencyBalance()
        balance.primaryCurrency += amount
        currencyDao.updateCurrencyBalance(balance)
        val transaction = Transaction(amount = amount, currencyType = "PRIMARY", type = "INCOME", source = source, timestamp = LocalDateTime.now())
        currencyDao.insertTransaction(transaction)
    }

    suspend fun deductPrimaryCurrency(amount: Int, source: String): Boolean {
        val balance = currencyDao.getCurrencyBalance().first() ?: CurrencyBalance()
        if (balance.primaryCurrency >= amount) {
            balance.primaryCurrency -= amount
            currencyDao.updateCurrencyBalance(balance)
            val transaction = Transaction(amount = amount, currencyType = "PRIMARY", type = "EXPENSE", source = source, timestamp = LocalDateTime.now())
            currencyDao.insertTransaction(transaction)
            return true
        }
        return false
    }

    suspend fun addSecondaryCurrency(amount: Int, source: String) {
        val balance = currencyDao.getCurrencyBalance().first() ?: CurrencyBalance()
        balance.secondaryCurrency += amount
        currencyDao.updateCurrencyBalance(balance)
        val transaction = Transaction(amount = amount, currencyType = "SECONDARY", type = "INCOME", source = source, timestamp = LocalDateTime.now())
        currencyDao.insertTransaction(transaction)
    }

    suspend fun deductSecondaryCurrency(amount: Int, source: String): Boolean {
        val balance = currencyDao.getCurrencyBalance().first() ?: CurrencyBalance()
        if (balance.secondaryCurrency >= amount) {
            balance.secondaryCurrency -= amount
            currencyDao.updateCurrencyBalance(balance)
            val transaction = Transaction(amount = amount, currencyType = "SECONDARY", type = "EXPENSE", source = source, timestamp = LocalDateTime.now())
            currencyDao.insertTransaction(transaction)
            return true
        }
        return false
    }

    fun getAllTransactions(): Flow<List<Transaction>> = currencyDao.getAllTransactions()
}