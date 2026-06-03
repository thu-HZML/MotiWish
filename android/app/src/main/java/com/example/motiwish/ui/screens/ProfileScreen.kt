package com.example.motiwish.ui.screens

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
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
    // 【修改点 1】：收集本地钱包状态，并同时收集远端 UserProfile 状态
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
        // 当用户选定图片返回时，uri 不为空，触发上传逻辑
        if (uri != null) {
            userViewModel.uploadAvatar(context, uri)
        }
    }

    // 【修改点 2】：每次进入页面时，自动触发拉取最新用户信息（刷新经验、等级等）
    LaunchedEffect(Unit) {
        userViewModel.fetchUserProfile()
        currencyViewModel.refreshWallet()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
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
                        // 点击拉起系统相册，只允许选择图片
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
                    // 后端有头像链接，使用 Coil 加载
                    AsyncImage(
                        model = ImageRequest.Builder(context)
                            .data(fullAvatarUrl)
                            .crossfade(true) // 开启淡入淡出动画
                            .build(),
                        contentDescription = "Avatar",
                        contentScale = ContentScale.Crop, // 居中裁剪填充整个圆形
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    // 后端无头像，展示默认占位图
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

            // 【修改点 3】：将原本写死的 "User" 替换为真实的动态数据判断
            Column {
                if (userProfile != null) {
                    // 显示昵称（如果没有昵称则显示用户名）
                    Text(
                        text = userProfile?.username ?: userProfile?.display_nickname ?: "User",
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold
                    )
                    // 显示等级与经验进度
                    Text(
                        text = "Lv.${userProfile?.level ?: 1} | 经验: ${userProfile?.experience ?: 0}/${userProfile?.next_level_experience ?: 0}",
                        color = MaterialTheme.colorScheme.primary,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(vertical = 2.dp)
                    )
                    // 显示个性签名
                    Text(
                        text = userProfile?.bio.takeIf { !it.isNullOrBlank() } ?: "这个人很懒，什么都没写",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 14.sp
                    )
                } else {
                    // 数据还未请求回来时的加载状态
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

        Card(
            modifier = Modifier
                .fillMaxWidth()
                .animateContentSize(), // 添加尺寸变换动画
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

                // 下拉触发按钮
                TextButton(
                    onClick = { isExpanded = !isExpanded },
                    modifier = Modifier.align(Alignment.CenterHorizontally)
                ) {
                    Text(if (isExpanded) "收起记录 ↑" else "查看最近收支记录 ↓")
                }

                // 展开后的列表部分
                if (isExpanded) {
                    HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                    LazyColumn(modifier = Modifier.heightIn(max = 300.dp)) {
                        items(transactions.take(10)) { transaction ->
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

        // 历史记录入口
        ProfileMenuItem(
            icon = { Icon(Icons.Default.History, contentDescription = null) },
            title = "兑换历史",
            subtitle = "查看过往的愿望奖励与道具",
            onClick = { navController.navigate("redemption_history") }
        )

        // 【修改点 4】：使用 Spacer 把退出登录按钮推到屏幕最底部，并使用醒目的错误色（红色）
        Spacer(modifier = Modifier.weight(1f))

        Button(
            onClick = {
                userViewModel.logout()
                navController.navigate("splash") {
                    // 清空整个路由栈，防止按返回键回到应用内
                    popUpTo(navController.graph.id) { inclusive = true }
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 16.dp),
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