package com.example.motiwish.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavController
import com.example.motiwish.viewmodel.CurrencyViewModel
import com.example.motiwish.viewmodel.RedemptionHistoryViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RedemptionHistoryScreen(
    viewModel: RedemptionHistoryViewModel,
    currencyViewModel: CurrencyViewModel,
    navController: NavController
) {
    // 1. 获取两边的数据源
    val records by viewModel.records.collectAsStateWithLifecycle()
    val inventoryList by viewModel.inventoryList.collectAsStateWithLifecycle()
    val isLoading by viewModel.isLoading.collectAsStateWithLifecycle()

    var selectedTabIndex by remember { mutableIntStateOf(0) }
    val snackbarHostState = remember { SnackbarHostState() }

    // ✅【修改 1】：只把“待去享受”的愿望抽出来放进背包，历史记录不再过滤，直接使用 records 全集
    val pendingWishes = records.filter { it.status == "requested" }

    LaunchedEffect(Unit) {
        viewModel.uiMessage.collect { message ->
            snackbarHostState.showSnackbar(message)
        }
    }

    LaunchedEffect(selectedTabIndex) {
        if (selectedTabIndex == 0) {
            viewModel.fetchInventory()
            viewModel.fetchHistory()
        } else {
            viewModel.fetchHistory()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            Column {
                TopAppBar(
                    title = { Text("我的物品", fontWeight = FontWeight.Bold) },
                    navigationIcon = {
                        IconButton(onClick = { navController.popBackStack() }) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                )
                TabRow(
                    selectedTabIndex = selectedTabIndex,
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Tab(
                        selected = selectedTabIndex == 0,
                        onClick = { selectedTabIndex = 0 },
                        text = { Text("🎒 我的背包", fontWeight = FontWeight.Bold) }
                    )
                    Tab(
                        selected = selectedTabIndex == 1,
                        onClick = { selectedTabIndex = 1 },
                        text = { Text("📜 兑换历史", fontWeight = FontWeight.Bold) }
                    )
                }
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            if (isLoading && inventoryList.isEmpty() && records.isEmpty()) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else {
                if (selectedTabIndex == 0) {
                    // ==================== 🎒 背包页面 ====================
                    if (inventoryList.isEmpty() && pendingWishes.isEmpty()) {
                        EmptyStateText("背包空空如也\n快去商城进货吧！")
                    } else {
                        LazyColumn(
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            // 渲染 1: 真实的后端背包道具 (如还债卡)
                            items(inventoryList) { invItem ->
                                InventoryItemCard(
                                    title = invItem.item.title,
                                    subtitle = "拥有数量: ${invItem.quantity}",
                                    buttonText = "立即使用",
                                    buttonColor = MaterialTheme.colorScheme.secondary,
                                    onUseClick = {
                                        viewModel.useItem(invItem.id) {
                                            currencyViewModel.refreshWallet()
                                        }
                                    }
                                )
                            }

                            // 渲染 2: 待兑现的愿望 (伪装成背包里的消费品)
                            items(pendingWishes) { wishRecord ->
                                InventoryItemCard(
                                    title = wishRecord.item.title,
                                    subtitle = "愿望券 x 1",
                                    buttonText = "去享受！",
                                    buttonColor = MaterialTheme.colorScheme.primary,
                                    onUseClick = {
                                        viewModel.fulfillRecord(wishRecord.id)
                                    }
                                )
                            }
                        }
                    }
                } else {
                    // ==================== 📜 历史/账单页面 ====================
                    // ✅【修改 2】：直接展示无过滤的完整 records 记录
                    if (records.isEmpty()) {
                        EmptyStateText("暂无历史记录")
                    } else {
                        LazyColumn(
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(records) { record ->
                                // ✅ 现在的历史卡片纯展示，不需要传 onFulfillClick 回调了
                                RedemptionRecordCard(record = record)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun BoxScope.EmptyStateText(text: String) {
    Text(
        text = text,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.align(Alignment.Center),
        textAlign = TextAlign.Center
    )
}

// 统一样式的背包卡片 (可同时兼容系统道具和愿望券)
@Composable
fun InventoryItemCard(
    title: String,
    subtitle: String,
    buttonText: String,
    buttonColor: Color,
    onUseClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(text = title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = subtitle,
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.SemiBold
                )
            }
            Button(
                onClick = onUseClick,
                colors = ButtonDefaults.buttonColors(containerColor = buttonColor)
            ) {
                Text(buttonText)
            }
        }
    }
}

// ✅【修改 3】：兑换历史账单卡片，去掉了交互按钮，变成纯展示组件
@Composable
fun RedemptionRecordCard(
    record: com.example.motiwish.data.network.NetworkRedemptionRecord
) {
    val formattedTime = try {
        java.time.ZonedDateTime.parse(record.created_at)
            .format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"))
    } catch (e: Exception) {
        "未知时间"
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(text = record.item.title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = formattedTime, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "-${record.cost_secondary} 币",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.secondary
                    )
                    // 状态展示的代码已经从这里彻底移除，干净利落！
                }
            }
        }
    }
}