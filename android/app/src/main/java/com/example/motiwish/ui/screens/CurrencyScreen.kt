package com.example.motiwish.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.motiwish.viewmodel.CurrencyViewModel
import androidx.compose.ui.graphics.Color
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CurrencyScreen(viewModel: CurrencyViewModel) {
    val balance by viewModel.balance.collectAsStateWithLifecycle()
    val transactions by viewModel.transactions.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("货币系统") },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.primary)
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { viewModel.addMockCurrency() },
                containerColor = MaterialTheme.colorScheme.secondary
            ) {
                Icon(Icons.Default.AttachMoney, contentDescription = "模拟充值")
            }
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("我的货币", style = MaterialTheme.typography.titleLarge)
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Icon(Icons.Default.CurrencyExchange, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                Text("一级货币", style = MaterialTheme.typography.bodyMedium)
                                Text("${balance?.primaryCurrency ?: 0}", style = MaterialTheme.typography.headlineMedium)
                            }
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Icon(Icons.Default.Star, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                                Text("二级货币", style = MaterialTheme.typography.bodyMedium)
                                Text("${balance?.secondaryCurrency ?: 0}", style = MaterialTheme.typography.headlineMedium)
                            }
                        }
                    }
                }
            }

            item {
                Text("账单记录", style = MaterialTheme.typography.titleMedium)
            }

            items(transactions) { transaction ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text(transaction.source, style = MaterialTheme.typography.bodyMedium)
                            Text(
                                transaction.timestamp.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")),
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                        Text(
                            "${if (transaction.type == "INCOME") "+" else "-"}${transaction.amount}",
                            color = if (transaction.type == "INCOME") Color.Green else Color.Red,
                            style = MaterialTheme.typography.titleMedium
                        )
                    }
                }
            }
        }
    }
}