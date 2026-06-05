package com.example.motiwish.ui.screens

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.CurrencyExchange
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavController

// 导入你的 ViewModel
import com.example.motiwish.viewmodel.CurrencyViewModel
import com.example.motiwish.viewmodel.HistoryViewModel
import com.example.motiwish.viewmodel.UserViewModel

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import coil.compose.AsyncImage
import coil.request.ImageRequest

@Composable
fun ProfileScreen(
    navController: NavController,
    currencyViewModel: CurrencyViewModel,
    historyViewModel: HistoryViewModel,
    userViewModel: UserViewModel
){
    // 收集本地钱包状态，并同时收集远端 UserProfile 状态
    val balance by currencyViewModel.balance.collectAsStateWithLifecycle()
    val transactions by currencyViewModel.transactions.collectAsStateWithLifecycle()
    val userProfile by userViewModel.userProfile.collectAsStateWithLifecycle()

    // 控制折叠状态
    var isExpanded by remember { mutableStateOf(false) }

    // 获取上下文并注册照片选择器
    val context = LocalContext.current
    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri ->
        if (uri != null) {
            userViewModel.uploadAvatar(context, uri)
        }
    }

    LaunchedEffect(Unit) {
        userViewModel.fetchUserProfile()
        currencyViewModel.refreshWallet()
    }

    // 页面整体容器
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // ==========================================
        // 上半部分：可滑动的所有内容
        // 用 LazyColumn 配合 weight(1f) 占据上方全部空间
        // ==========================================
        LazyColumn(
            modifier = Modifier.weight(1f),
        ) {
            item {
                // --- 头部用户信息区 ---
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 24.dp)
                ) {
                    Surface(
                        modifier = Modifier
                            .size(80.dp)
                            .clickable {
                                photoPickerLauncher.launch(
                                    PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                                )
                            },
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.primaryContainer
                    ) {
                        if (!userProfile?.avatar_url.isNullOrEmpty()) {
                            val rawUrl = userProfile?.avatar_url
                            val fullAvatarUrl = if (rawUrl?.startsWith("http") == true) {
                                rawUrl
                            } else if (rawUrl?.startsWith("/") == true) {
                                "https://8.147.57.94$rawUrl"
                            } else {
                                "https://8.147.57.94/$rawUrl"
                            }
                            AsyncImage(
                                model = ImageRequest.Builder(context)
                                    .data(fullAvatarUrl)
                                    .crossfade(true)
                                    .build(),
                                contentDescription = "Avatar",
                                contentScale = ContentScale.Crop,
                                modifier = Modifier.fillMaxSize()
                            )
                        } else {
                            Icon(
                                imageVector = Icons.Default.Person,
                                contentDescription = "Default Avatar",
                                modifier = Modifier
                                    .padding(16.dp)
                                    .fillMaxSize(),
                                tint = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                        }
                    }
                    Spacer(modifier = Modifier.width(16.dp))

                    Column {
                        if (userProfile != null) {
                            Text(
                                text = userProfile?.username ?: userProfile?.display_nickname ?: "User",
                                fontSize = 24.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "Lv.${userProfile?.level ?: 1} | 经验: ${userProfile?.experience ?: 0}/${userProfile?.next_level_experience ?: 0}",
                                color = MaterialTheme.colorScheme.primary,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(vertical = 2.dp)
                            )
                            Text(
                                text = userProfile?.bio.takeIf { !it.isNullOrBlank() } ?: "这个人很懒，什么都没写",
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                fontSize = 14.sp
                            )
                        } else {
                            CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text("获取资料中...", fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }

                HorizontalDivider(modifier = Modifier.padding(bottom = 16.dp))

                // --- 功能入口列表 ---
                Text(
                    text = "我的数据",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
            }

            // --- 收支数据卡片 ---
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .animateContentSize(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("当前余额", style = MaterialTheme.typography.titleMedium)
                        Spacer(modifier = Modifier.height(12.dp))

                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceAround) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("一级货币", fontSize = 12.sp)
                                Text("${balance?.primaryCurrency ?: 0}", fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                            }
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("二级货币", fontSize = 12.sp)
                                Text("${balance?.secondaryCurrency ?: 0}", fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                            }
                        }

                        TextButton(
                            onClick = { isExpanded = !isExpanded },
                            modifier = Modifier.align(Alignment.CenterHorizontally)
                        ) {
                            Text(if (isExpanded) "收起记录 ↑" else "查看最近收支记录 ↓")
                        }

                        if (isExpanded) {
                            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                            // ⚠️ 核心修复：外层已经是 LazyColumn 了，这里必须换成普通的 Column + forEach 避免崩溃
                            Column(modifier = Modifier.fillMaxWidth()) {
                                transactions.take(10).forEach { transaction ->
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(vertical = 6.dp),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = transaction.source,
                                            fontSize = 14.sp,
                                            modifier = Modifier.weight(1f)
                                        )

                                        val isIncome = transaction.type == "INCOME"
                                        val isPrimary = transaction.currencyType.contains("PRIMARY", ignoreCase = true)
                                                || transaction.currencyType.contains("一级")

                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Icon(
                                                imageVector = if (isPrimary) Icons.Default.CurrencyExchange else Icons.Default.Star,
                                                contentDescription = null,
                                                modifier = Modifier
                                                    .size(16.dp)
                                                    .padding(end = 4.dp),
                                                tint = if (isPrimary) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
                                            )
                                            Text(
                                                text = "${if (isIncome) "+" else "-"}${transaction.amount}",
                                                color = if (isIncome) Color(0xFF388E3C) else Color(0xFFD32F2F),
                                                fontWeight = FontWeight.Bold,
                                                fontSize = 14.sp
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Spacer(modifier = Modifier.height(16.dp))
            }

            // --- 菜单入口 ---
            item {
                ProfileMenuItem(
                    icon = { Icon(Icons.Default.History, contentDescription = null) },
                    title = "兑换历史",
                    subtitle = "查看过往的愿望奖励与道具",
                    onClick = { navController.navigate("redemption_history") }
                )

                ProfileMenuItem(
                    icon = { Icon(Icons.Default.Person, contentDescription = null) },
                    title = "自我探索画像",
                    subtitle = "完善你的行为偏好，获取更精准的 AI 推荐",
                    onClick = { navController.navigate("questionnaire") }
                )
            }
        }

        // ==========================================
        // 下半部分：固定在底部的退出按钮
        // 因为放在了 LazyColumn 外面，所以它绝对不会被遮挡！
        // ==========================================
        Button(
            onClick = {
                userViewModel.logout()
                navController.navigate("splash") {
                    popUpTo(navController.graph.id) { inclusive = true }
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp, bottom = 16.dp), // 留出一点顶部间距
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
        ) {
            Text("退出登录", fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
fun ProfileMenuItem(
    icon: @Composable () -> Unit,
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp)
            .clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            icon()
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(text = title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                Text(text = subtitle, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
            }
            Icon(Icons.Default.ChevronRight, contentDescription = "进入")
        }
    }
}