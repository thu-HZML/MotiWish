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
import com.example.motiwish.data.model.WishDraft
import com.example.motiwish.data.network.WishPricingSession
import com.example.motiwish.data.network.toUserFitNotesString
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

    // AI定价相关变量
    val wishDrafts by shopViewModel.wishDrafts.collectAsStateWithLifecycle()
    val selectedWishDraft by shopViewModel.selectedWishDraftForPricing.collectAsStateWithLifecycle()

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
                                onClick = {
                                    gachaViewModel.draw(1)
                                },
                                enabled = primaryBalance >= 50,
                                colors = ButtonDefaults.buttonColors(
                                    disabledContainerColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f),
                                    disabledContentColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                                )
                            ) {
                                Text("单次祈愿 (50币)")
                            }
                            Button(
                                onClick = {
                                    gachaViewModel.draw(10)
                                },
                                enabled = primaryBalance >= 500,
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.secondary,
                                    disabledContainerColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f),
                                    disabledContentColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                                )
                            ) {
                                Text("十连祈愿 (500币)")
                            }
                        }
                    }
                }
            }

            // --- 3. 定价中的愿望卡片 ---
            // 定价中的愿望卡片
            if (wishDrafts.isNotEmpty()) {
                item {
                    WishPricingDraftsCard(
                        drafts = wishDrafts,
                        viewModel = shopViewModel
                    )
                }
            }

            // --- 4. 愿望商店标题 ---
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    HorizontalDivider(modifier = Modifier.weight(1f))
                    Text(
                        text = "兑换愿望",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 12.dp)
                    )

                    // 专属愿望按钮
                    Button(onClick = { shopViewModel.fetchDailyRefreshWish() }) {
                        Text("获取今日专属愿望")
                    }
                }
            }

            // --- 5. 愿望列表（售罄排最后）---
            val sortedWishes = wishes.sortedBy { it.inventory == 0 }
            items(sortedWishes) { wish ->
                WishCard(wish, shopViewModel, snackbarHostState)
            }
        }
    }

    // 定价对话框（需要区分每日愿望展示额外信息）
    selectedWishDraft?.let { (draftId, session) ->
        WishPricingDialog(
            session = session,
            isDailyRefresh = session.source == "daily_refresh",  // 假设后端返回 source 字段
            onAccept = { shopViewModel.acceptWishPricing(draftId) },
            onCancel = { shopViewModel.cancelWishPricing(draftId) },
            onDismiss = { shopViewModel.dismissWishPricingDialog() }
        )
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
    var tagsText by remember { mutableStateOf("") }  // 逗号分隔

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("添加愿望") },
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
                label = { Text("愿望名称 *") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text("愿望描述（可选）") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = tagsText,
                onValueChange = { tagsText = it },
                label = { Text("标签（可选，逗号分隔）") },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("例如：娱乐,美食,旅行") }
            )

            Button(
                onClick = {
                    if (title.isBlank()) {
                        scope.launch { snackbarHostState.showSnackbar("请填写愿望名称") }
                        return@Button
                    }
                    val tags = tagsText.split(",")
                        .map { it.trim() }
                        .filter { it.isNotEmpty() }
                    shopViewModel.createWishDraftAsync(title, description, tags)
                    navController.popBackStack()  // 返回商店页面
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("提交愿望，AI定价")
            }
        }
    }
}

// 定价对话框组件
@Composable
fun WishPricingDialog(
    session: WishPricingSession,
    isDailyRefresh: Boolean = false,
    onAccept: () -> Unit,
    onCancel: () -> Unit,
    onDismiss: () -> Unit
) {
    val quote = session.quote_payload
    val fitNotes = quote.user_fit_notes.toUserFitNotesString()

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(if (isDailyRefresh) "✨ 今日专属愿望 ✨" else "AI 愿望定价建议")
        },
        text = {
            Column {
                Text("愿望：${quote.title}", style = MaterialTheme.typography.titleMedium)
                if (quote.description != null) {
                    Text(quote.description, style = MaterialTheme.typography.bodySmall)
                }
                Spacer(modifier = Modifier.height(8.dp))
                Text("建议价格：${quote.price_secondary} 二级货币")
                Text("档位：${when (quote.price_tier) {
                    "small" -> "小额 (30-120)"
                    "medium" -> "中额 (120-350)"
                    "large" -> "大额 (350-1200)"
                    else -> quote.price_tier
                }}")
                Text("稀有度：${when (quote.rarity) {
                    "common" -> "普通"
                    "rare" -> "稀有"
                    "epic" -> "珍贵"
                    else -> quote.rarity
                }}")
                Text("库存：${if (quote.inventory > 0) quote.inventory else "无限"}")
                Spacer(modifier = Modifier.height(8.dp))
                Text("理由：${quote.reasoning}", style = MaterialTheme.typography.bodySmall)

                if (!fitNotes.isNullOrEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = fitNotes,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onAccept) {
                Text(if (isDailyRefresh) "领取专属愿望" else "接受并创建")
            }
        },
        dismissButton = {
            TextButton(onClick = onCancel) {
                Text("取消")
            }
        }
    )
}

// 定价草稿卡片
@Composable
fun WishPricingDraftsCard(
    drafts: List<WishDraft>,
    viewModel: ShopViewModel
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "定价中的愿望",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.primary
            )
            drafts.forEach { draft ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = if (draft.isDailyRefresh) "🎁 ${draft.title} (专属)" else draft.title,
                            style = MaterialTheme.typography.bodyLarge
                        )
                        if (draft.isDailyRefresh && draft.quotePayload?.user_fit_notes != null) {
                            Text(
                                text = draft.quotePayload.user_fit_notes.toUserFitNotesString()?.take(30) ?: "",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                    when (draft.status) {
                        "pricing" -> {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("AI 定价中...", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                        "quoted" -> {
                            Button(
                                onClick = { viewModel.showWishPricingDialog(draft.id) },
                                modifier = Modifier.wrapContentWidth()
                            ) {
                                Text("查看定价")
                            }
                        }
                        else -> {
                            Text(draft.status, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
                if (draft != drafts.last()) {
                    Divider(modifier = Modifier.padding(vertical = 4.dp))
                }
            }
        }
    }
}
