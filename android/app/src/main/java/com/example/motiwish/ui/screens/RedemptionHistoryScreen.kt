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
    // 拉取两个不同的数据源
    val records by viewModel.records.collectAsStateWithLifecycle()
    val inventoryList by viewModel.inventoryList.collectAsStateWithLifecycle()
    val isLoading by viewModel.isLoading.collectAsStateWithLifecycle()

    // 0 = 我的背包 (Inventory), 1 = 兑换记录 (History)
    var selectedTabIndex by remember { mutableIntStateOf(0) }

    val snackbarHostState = remember { SnackbarHostState() }

    // 监听 ViewModel 发来的消息并弹窗
    LaunchedEffect(Unit) {
        viewModel.uiMessage.collect { message ->
            snackbarHostState.showSnackbar(message)
        }
    }

    // 根据当前选中的 Tab 拉取对应的数据
    LaunchedEffect(selectedTabIndex) {
        if (selectedTabIndex == 0) {
            viewModel.fetchInventory() // 确保 ViewModel 里有这个拉取背包的方法
        } else {
            // 注意：如果你 ViewModel 里的方法名不叫 fetchRecords，请替换为你原本拉取历史的方法名
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
                // 顶部 Tab 切换栏
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
                        text = { Text("📜 兑换记录", fontWeight = FontWeight.Bold) }
                    )
                }
            }
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else {
                // 根据 Tab 渲染不同列表
                if (selectedTabIndex == 0) {
                    // ==================== 背包页面 ====================
                    if (inventoryList.isEmpty()) {
                        EmptyStateText("背包空空如也\n快去商城进货吧！")
                    } else {
                        LazyColumn(
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(inventoryList) { invItem ->
                                InventoryItemCard(
                                    invItem = invItem,
                                    onUseClick = {
                                        viewModel.useItem(invItem.id) {
                                            // 道具使用成功后，立刻通知货币系统去后端刷新最新余额（清空负债）！
                                            currencyViewModel.refreshWallet()
                                        }
                                    }
                                )
                            }
                        }
                    }
                } else {
                    // ==================== 历史/愿望页面 ====================
                    if (records.isEmpty()) {
                        EmptyStateText("暂无兑换记录\n快去商城看看有什么好东西吧！")
                    } else {
                        LazyColumn(
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(records) { record ->
                                RedemptionRecordCard(
                                    record = record,
                                    onFulfillClick = { viewModel.fulfillRecord(record.id) }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

// 提取的空状态组件，保持代码整洁
@Composable
fun BoxScope.EmptyStateText(text: String) {
    Text(
        text = text,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.align(Alignment.Center),
        textAlign = TextAlign.Center
    )
}

// ==================== 1. 真实的背包道具卡片 (新增) ====================
@Composable
fun InventoryItemCard(
    invItem: com.example.motiwish.data.network.UserInventoryItem, // 请确保你在数据模型里加了这个类
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
                // invItem.item 是嵌套的商品详情
                Text(
                    text = invItem.item.name, // 直接改成这样！
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "拥有数量: ${invItem.quantity}",
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.SemiBold
                )
            }
            Button(
                onClick = onUseClick,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
            ) {
                Text("立即使用")
            }
        }
    }
}

// ==================== 2. 兑换记录/愿望卡片 (保留原有) ====================
@Composable
fun RedemptionRecordCard(
    record: com.example.motiwish.data.network.NetworkRedemptionRecord,
    onFulfillClick: () -> Unit
) {
    val formattedTime = try {
        java.time.ZonedDateTime.parse(record.created_at)
            .format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"))
    } catch (e: Exception) {
        "未知时间"
    }

    val (statusText, statusColor) = when (record.status) {
        "completed", "fulfilled" -> Pair("已享受 🎉", Color(0xFF388E3C))
        "requested" -> Pair("待去享受", Color(0xFFF57C00))
        "rejected" -> Pair("已退回", Color(0xFFD32F2F))
        else -> Pair("未知状态", Color.Gray)
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
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = statusText, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = statusColor)
                }
            }

            if (record.status == "requested") {
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedButton(
                    onClick = onFulfillClick,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("我已在现实中享受该愿望！")
                }
            }
        }
    }
}