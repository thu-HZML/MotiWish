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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavController
import com.example.motiwish.data.model.Wish
import com.example.motiwish.viewmodel.ShopViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShopScreen(viewModel: ShopViewModel, navController: NavController) {
    val wishes by viewModel.wishes.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        viewModel.uiMessage.collect { message ->
            scope.launch {
                snackbarHostState.showSnackbar(message)
            }
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("愿望商店") },
                actions = {
                    IconButton(onClick = { navController.navigate("addWish?wishId=-1") }) {
                        Icon(Icons.Default.Add, contentDescription = "添加愿望")
                    }
                    IconButton(onClick = { viewModel.refreshSystemWish() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "刷新系统愿望")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.primary)
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text("使用二级货币兑换愿望", style = MaterialTheme.typography.titleMedium)
            }

            items(wishes) { wish ->
                WishCard(wish, viewModel, snackbarHostState, navController)
            }
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
    val wish = if (wishId != -1) {
        viewModel.wishes.value.find { it.id == wishId }
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