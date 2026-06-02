package com.example.motiwish.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavController
import com.example.motiwish.data.model.Wish
import com.example.motiwish.viewmodel.CurrencyViewModel
import com.example.motiwish.viewmodel.GachaViewModel
import com.example.motiwish.viewmodel.ShopViewModel
import kotlinx.coroutines.launch
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StoreScreen(
    gachaViewModel: GachaViewModel,
    shopViewModel: ShopViewModel,
    currencyViewModel: CurrencyViewModel, // 引入货币ViewModel查看余额
    navController: NavController
) {
    val wishes by shopViewModel.wishes.collectAsStateWithLifecycle()
    val balance by currencyViewModel.balance.collectAsStateWithLifecycle()
    val primaryBalance = balance?.primaryCurrency ?: 0

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        currencyViewModel.refreshWallet()
    }

    // 监听两个 ViewModel 的消息
    LaunchedEffect(Unit) {
        launch {
            gachaViewModel.uiMessage.collect { snackbarHostState.showSnackbar(it) }
        }
        launch {
            shopViewModel.uiMessage.collect { snackbarHostState.showSnackbar(it) }
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("祈愿商城") },
                actions = {
                    IconButton(onClick = { navController.navigate("addWish?wishId=-1") }) {
                        Icon(Icons.Default.Add, contentDescription = "添加愿望")
                    }
                    IconButton(onClick = { shopViewModel.refreshSystemWish() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "刷新")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // --- 1. 资产看板 ---
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceEvenly
                ) {
                    BalanceBadge(icon = Icons.Default.CurrencyExchange, name = "一级货币", amount = balance?.primaryCurrency ?: 0)
                    BalanceBadge(icon = Icons.Default.Star, name = "二级货币", amount = balance?.secondaryCurrency ?: 0)
                }
            }

            // --- 2. 抽卡区域 (Gacha) ---
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(Icons.Default.Casino, contentDescription = null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("消耗一级货币，抽取二级货币", style = MaterialTheme.typography.titleMedium)
                        Text("十连抽必出暴击！", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodySmall)

                        Spacer(modifier = Modifier.height(16.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly
                        ) {
                            Button(
                                onClick = {
                                    // 这里可以直接调 ViewModel 的 draw(1) 了
                                    gachaViewModel.draw(1)
                                },
                                enabled = primaryBalance >= 10, // 核心逻辑：钱够 10 块才能点！
                                colors = ButtonDefaults.buttonColors(
                                    // Compose 会自动处理置灰，但你也可以显式指定颜色
                                    disabledContainerColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f),
                                    disabledContentColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                                )
                            ) {
                                Text("单次祈愿 (10币)")
                            }
                            Button(
                                onClick = {
                                    gachaViewModel.draw(10)
                                },
                                enabled = primaryBalance >= 100, // 核心逻辑：钱够 100 块才能点！
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.secondary,
                                    disabledContainerColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f),
                                    disabledContentColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                                )
                            ) {
                                Text("十连祈愿 (100币)")
                            }
                        }
                    }
                }
            }

            // --- 3. 愿望商店标题 ---
            item {
                Divider(modifier = Modifier.padding(vertical = 8.dp))
                Text("兑换愿望", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            }

            // --- 4. 愿望列表 ---
            items(wishes) { wish ->
                WishCard(wish, shopViewModel, snackbarHostState, navController)
            }
        }
    }
}

@Composable
fun BalanceBadge(icon: androidx.compose.ui.graphics.vector.ImageVector, name: String, amount: Int) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
        Spacer(modifier = Modifier.width(4.dp))
        Column {
            Text(name, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("$amount", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        }
    }
}

@Composable
fun WishCard(
    wish: Wish,
    viewModel: ShopViewModel,
    snackbarHostState: SnackbarHostState,
    navController: NavController
) {
    // ✅ 将协程作用域移到顶层（直接在 @Composable 函数内）
    val scope = rememberCoroutineScope()

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { navController.navigate("addWish?wishId=${wish.id}") },
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(wish.name, style = MaterialTheme.typography.titleMedium)
                Text("需要: ${wish.costSecondary} 二级货币", style = MaterialTheme.typography.bodySmall)
                if (wish.isSystem) {
                    Text(
                        "系统推荐",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }

            Button(
                onClick = {
                    // ✅ 直接使用顶层的 scope
                    scope.launch {
                        if (viewModel.purchaseWish(wish)) {
                            // 兑换成功时显示 Snackbar
                            snackbarHostState.showSnackbar("兑换成功！")
                        } else {
                            // 可选：显示失败提示
                            snackbarHostState.showSnackbar("兑换失败，货币不足")
                        }
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
            ) {
                Text("兑换")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddWishScreen(viewModel: ShopViewModel, navController: NavController, wishId: Int) {
    // 1. 正确地观察状态（这会触发 UI 的自动重组）
    val wishes by viewModel.wishes.collectAsStateWithLifecycle()

    // 2. 从观察到的状态列表中寻找对应的愿望
    val wish = if (wishId != -1) {
        wishes.find { it.id == wishId }
    } else null

    var name by remember { mutableStateOf(wish?.name ?: "") }
    var cost by remember { mutableStateOf(wish?.costSecondary ?: 50) }
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text(if (wishId == -1) "添加愿望" else "编辑愿望") },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("愿望名称") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = cost.toString(),
                onValueChange = { cost = it.toIntOrNull() ?: 0 },
                label = { Text("所需二级货币") },
                modifier = Modifier.fillMaxWidth()
            )

            Button(
                onClick = {
                    if (name.isNotBlank() && cost > 0) {
                        if (wishId == -1) {
                            viewModel.addCustomWish(name, cost)
                        } else {
                            // ✅ 使用 copy() 创建新对象，而不是直接修改 val 属性
                            wish?.let {
                                val updatedWish = it.copy(name = name, costSecondary = cost)
                                viewModel.updateWish(updatedWish)
                            }
                        }
                        scope.launch {
                            snackbarHostState.showSnackbar(if (wishId == -1) "添加成功" else "更新成功")
                            navController.popBackStack()
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text(if (wishId == -1) "添加" else "更新")
            }

            if (wish != null && !wish.isSystem) {
                Button(
                    onClick = {
                        viewModel.deleteWish(wish)
                        scope.launch {
                            snackbarHostState.showSnackbar("删除成功")
                            navController.popBackStack()
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("删除愿望")
                }
            }
        }
    }
}