package com.example.motiwish.data.repository

import com.example.motiwish.data.model.CurrencyBalance
import com.example.motiwish.data.model.Transaction
import com.example.motiwish.data.network.WalletApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.time.ZonedDateTime
import kotlin.math.abs

class CurrencyRepository(private val walletApi: WalletApi) {

    // 使用内存热流接管之前的 Room Live 数据，保持对响应式 UI 的暴露
    private val _balance = MutableStateFlow<CurrencyBalance?>(null)
    fun getCurrencyBalance(): Flow<CurrencyBalance?> = _balance.asStateFlow()

    private val _transactions = MutableStateFlow<List<Transaction>>(emptyList())
    fun getAllTransactions(): Flow<List<Transaction>> = _transactions.asStateFlow()

    /**
     * 【核心同步函数】主动去后端拉取最新资产和账单，并优雅映射转换为本地界面模型
     */
    suspend fun refreshWalletFromServer() {
        try {
            // 1. 同步最新的一级与二级代币余额
            val walletResponse = walletApi.getWalletBalance()
            if (walletResponse.success && walletResponse.data != null) {
                val serverWallet = walletResponse.data
                _balance.value = CurrencyBalance().apply {
                    primaryCurrency = serverWallet.primary_balance
                    secondaryCurrency = serverWallet.secondary_balance
                }
            }

            // 2. 同步变动明细并对非人性化标签做本地国际化翻译
            val transResponse = walletApi.getTransactions()
            if (transResponse.success && transResponse.data != null) {
                val serverTransList = transResponse.data

                val localMappedList = serverTransList.map { trans ->
                    // 将后端的 ReasonEnum 代号转换为前端友好的中文字符
                    val readableSource = when (trans.reason) {
                        "task_reward" -> "任务奖励"
                        "task_penalty" -> "任务惩罚"
                        "gacha_cost" -> "抽卡消耗"
                        "gacha_reward" -> "抽卡奖励"
                        "shop_redeem" -> "商店兑换"
                        "shop_refund" -> "商店退款"
                        "debt_reset" -> "债务重置"
                        else -> trans.memo ?: "后台调整"
                    }

                    Transaction(
                        amount = abs(trans.delta), // UI 界面需要的是没有符号的正数绝对值
                        currencyType = trans.currency_type.uppercase(), // 转换为本地大写判断 ("PRIMARY"/"SECONDARY")
                        type = if (trans.delta >= 0) "INCOME" else "EXPENSE", // 正数为收入，负数为支出
                        source = readableSource,
                        timestamp = try {
                            ZonedDateTime.parse(trans.created_at).toLocalDateTime()
                        } catch (e: Exception) {
                            java.time.LocalDateTime.now()
                        }
                    )
                }
                _transactions.value = localMappedList
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    // 注意：单机版的增减币功能在联机版中应该停用。因为当玩家完成任务时，
    // 应直接调用结算任务接口，由后端计算完毕后，前端通过调用 refreshWalletFromServer() 刷新界面。
}