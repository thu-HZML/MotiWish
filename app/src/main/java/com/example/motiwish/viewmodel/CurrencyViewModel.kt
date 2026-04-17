package com.example.motiwish.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.motiwish.data.model.CurrencyBalance
import com.example.motiwish.data.model.Transaction
import com.example.motiwish.data.repository.CurrencyRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class CurrencyViewModel(private val currencyRepository: CurrencyRepository) : ViewModel() {
    private val _balance = MutableStateFlow<CurrencyBalance?>(null)
    val balance: StateFlow<CurrencyBalance?> = _balance
    private val _transactions = MutableStateFlow<List<Transaction>>(emptyList())
    val transactions: StateFlow<List<Transaction>> = _transactions

    init {
        currencyRepository.getCurrencyBalance().onEach { _balance.value = it }.launchIn(viewModelScope)
        currencyRepository.getAllTransactions().onEach { _transactions.value = it }.launchIn(viewModelScope)
    }

    fun addMockCurrency() {
        viewModelScope.launch {
            currencyRepository.addPrimaryCurrency(100, "模拟充值（测试）")
        }
    }
}