package com.example.motiwish.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavController
import com.example.motiwish.data.model.Wish
import com.example.motiwish.viewmodel.CurrencyViewModel
import com.example.motiwish.viewmodel.GachaViewModel
import com.example.motiwish.viewmodel.ShopViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StoreScreen(
    gachaViewModel: GachaViewModel,
    shopViewModel: ShopViewModel,
    currencyViewModel: CurrencyViewModel,
    navController: NavController
) {
    val wishes by shopViewModel.wishes.collectAsStateWithLifecycle()
    val balance by currencyViewModel.balance.collectAsStateWithLifecycle()
    val primaryBalance = balance?.primaryCurrency ?: 0

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        currencyViewModel.refreshWallet()
        shopViewModel.fetchRealShopItems()
    }

    // 监听两个 ViewModel 的消息
    LaunchedEffect(Unit) {
        launch { gachaViewModel.uiMessage.collect { snackbarHostState.showSnackbar(it) } }
        launch { shopViewModel.uiMessage.collect { snackbarHostState.showSnackbar(it) } }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("祈愿商城") },
                actions = {
                    IconButton(onClick = { navController.navigate("addWish") }) {
                        Icon(Icons.Default.Add, contentDescription = "添加愿望")
                    }
                    IconButton(onClick = { shopViewModel.fetchRealShopItems() }) {
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
                                onClick = { gachaViewModel.draw(1) },
                                enabled = primaryBalance >= 10,
                                colors = ButtonDefaults.buttonColors(
                                    disabledContainerColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f),
                                    disabledContentColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                                )
                            ) {
                                Text("单次祈愿 (10币)")
                            }
                            Button(
                                onClick = { gachaViewModel.draw(10) },
                                enabled = primaryBalance >= 100,
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
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                Text("兑换愿望", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            }

            // --- 4. 愿望列表（售罄排最后）---
            val sortedWishes = wishes.sortedBy { it.inventory == 0 }
            items(sortedWishes) { wish ->
                WishCard(wish, shopViewModel, snackbarHostState)
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
    snackbarHostState: SnackbarHostState
) {
    val scope = rememberCoroutineScope()
    val isSoldOut = wish.inventory != null && wish.inventory == 0

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .alpha(if (isSoldOut) 0.5f else 1f),
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
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (wish.isSystem) {
                        Text(
                            "系统推荐",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                    if (wish.inventory != null && wish.inventory > 0) {
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "剩余: ${wish.inventory}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.secondary
                        )
                    }
                }
            }

            Button(
                onClick = {
                    scope.launch {
                        if (viewModel.purchaseWish(wish)) {
                            snackbarHostState.showSnackbar("兑换成功！")
                        } else {
                            snackbarHostState.showSnackbar("兑换失败，货币不足或网络错误")
                        }
                    }
                },
                enabled = !isSoldOut,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
            ) {
                Text(if (isSoldOut) "已售罄" else "兑换")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddWishScreen(
    shopViewModel: ShopViewModel,
    navController: NavController
) {
    var title by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var priceSecondary by remember { mutableStateOf("") }
    var selectedPriceTier by remember { mutableStateOf("medium") }
    var selectedRarity by remember { mutableStateOf("common") }
    var inventory by remember { mutableStateOf("1") }
    var autoRefund by remember { mutableStateOf(true) }

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    // 价格档位范围映射
    val priceRange = when (selectedPriceTier) {
        "small" -> 30..120
        "medium" -> 120..350  // 边界值 120 同时属于 small 和 medium，这里允许重叠
        "large" -> 350..1200
        else -> null
    }

    // 解析价格数值
    val priceValue = priceSecondary.toIntOrNull()
    val isPriceValid = priceValue != null && priceValue > 0 && (priceRange == null || priceValue in priceRange)

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("创建自定义愿望商品") },
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
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedTextField(
                value = title,
                onValueChange = { title = it },
                label = { Text("商品名称 *") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text("描述（可选）") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = priceSecondary,
                onValueChange = { priceSecondary = it },
                label = { Text("所需二级货币 *") },
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                isError = priceSecondary.isNotBlank() && !isPriceValid,
                supportingText = {
                    if (priceSecondary.isNotBlank() && !isPriceValid) {
                        Text("价格必须在 ${priceRange?.start} - ${priceRange?.endInclusive} 之间", color = MaterialTheme.colorScheme.error)
                    } else if (priceRange != null) {
                        Text("${priceRange.start} - ${priceRange.endInclusive} 二级货币", style = MaterialTheme.typography.bodySmall)
                    }
                }
            )

            Text("价格档次")
            Row(horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                listOf("small" to "小额 (30-120)", "medium" to "中额 (120-350)", "large" to "大额 (350-1200)").forEach { (tier, label) ->
                    FilterChip(
                        selected = selectedPriceTier == tier,
                        onClick = { selectedPriceTier = tier },
                        label = { Text(label) }
                    )
                }
            }

            Text("稀有度（可选）")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("common" to "普通", "rare" to "稀有", "epic" to "珍贵").forEach { (rarity, label) ->
                    FilterChip(
                        selected = selectedRarity == rarity,
                        onClick = { selectedRarity = rarity },
                        label = { Text(label) }
                    )
                }
            }

            OutlinedTextField(
                value = inventory,
                onValueChange = { inventory = it },
                label = { Text("库存数量（留空则无限）") },
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                supportingText = { Text("正整数表示库存，0表示售罄，留空或-1表示无限") }
            )

            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("拒绝时自动退款", modifier = Modifier.weight(1f))
                Switch(
                    checked = autoRefund,
                    onCheckedChange = { autoRefund = it }
                )
            }

            Button(
                onClick = {
                    val price = priceValue
                    if (title.isBlank()) {
                        scope.launch { snackbarHostState.showSnackbar("请填写商品名称") }
                        return@Button
                    }
                    if (price == null || price <= 0) {
                        scope.launch { snackbarHostState.showSnackbar("请填写有效的二级货币价格") }
                        return@Button
                    }
                    if (priceRange != null && price !in priceRange) {
                        scope.launch { snackbarHostState.showSnackbar("价格必须在 ${priceRange.start} - ${priceRange.endInclusive} 之间") }
                        return@Button
                    }
                    val inv = when {
                        inventory.isBlank() -> null
                        else -> inventory.toIntOrNull()?.takeIf { it >= 0 }
                    }
                    scope.launch {
                        val success = shopViewModel.createCustomShopItem(
                            title = title,
                            description = description.takeIf { it.isNotBlank() },
                            priceSecondary = price,
                            priceTier = selectedPriceTier,
                            rarity = selectedRarity,
                            inventory = inv,
                            autoRefund = autoRefund
                        )
                        if (success) {
                            navController.popBackStack()
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = title.isNotBlank() && isPriceValid  // 按钮启用条件
            ) {
                Text("创建商品")
            }
        }
    }
}