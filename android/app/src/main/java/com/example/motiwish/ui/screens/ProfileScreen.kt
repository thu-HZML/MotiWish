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

import androidx.compose.material.icons.filled.CurrencyExchange
import androidx.compose.material.icons.filled.Star

@Composable
fun ProfileScreen(
    navController: NavController,
    currencyViewModel: CurrencyViewModel,
    historyViewModel: HistoryViewModel
){
    // 观察真实的数据状态 (修正了变量名和获取方式)
    val balance by currencyViewModel.balance.collectAsStateWithLifecycle()
    val transactions by currencyViewModel.transactions.collectAsStateWithLifecycle()

    // 控制折叠状态
    var isExpanded by remember { mutableStateOf(false) }

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
                modifier = Modifier.size(80.dp),
                shape = CircleShape,
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Icon(
                    imageVector = Icons.Default.Person,
                    contentDescription = "Avatar",
                    modifier = Modifier
                        .padding(16.dp)
                        .fillMaxSize(),
                    tint = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column {
                Text(
                    text = "User",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "MotiWish 探索者",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 14.sp
                )
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
            modifier = Modifier.fillMaxWidth().animateContentSize(), // 添加尺寸变换动画
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("当前余额", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.height(12.dp))

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceAround) {
                    // 直接从 CurrencyBalance 对象读取数据 (修正了循环读取的错误)
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
                        // 使用 transactions 并读取正确的属性 (修正了属性名称)
                        items(transactions.take(10)) { transaction ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 6.dp), // 稍微增加一点上下间距
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically // 确保左右居中对齐
                            ) {
                                // 左侧：交易来源
                                Text(
                                    text = transaction.source,
                                    fontSize = 14.sp,
                                    modifier = Modifier.weight(1f) // 让文字占据多余空间，防止长文本顶到右边
                                )

                                // 右侧：图标 + 金额
                                val isIncome = transaction.type == "INCOME"
                                // 根据数据库里存的 currencyType 决定图标和颜色
                                // (假设你存的是 PRIMARY/SECONDARY 或包含 一级/二级 字眼，请根据你的 Repository 实际写入的字符串调整)
                                val isPrimary = transaction.currencyType.contains("PRIMARY", ignoreCase = true)
                                        || transaction.currencyType.contains("一级")

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = if (isPrimary) Icons.Default.CurrencyExchange else Icons.Default.Star,
                                        contentDescription = null,
                                        modifier = Modifier.size(16.dp).padding(end = 4.dp),
                                        tint = if (isPrimary) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
                                    )
                                    Text(
                                        text = "${if (isIncome) "+" else "-"}${transaction.amount}",
                                        color = if (isIncome) Color(0xFF388E3C) else Color(0xFFD32F2F), // 使用稍微柔和一点的红绿色
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
            title = "历史记录",
            subtitle = "查看过往任务与成就",
            onClick = { navController.navigate("history") }
        )

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