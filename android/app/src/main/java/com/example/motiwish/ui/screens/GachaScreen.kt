package com.example.motiwish.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.motiwish.viewmodel.GachaViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GachaScreen(viewModel: GachaViewModel) {
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    var drawCount by remember { mutableStateOf(1) }

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
                title = { Text("抽卡系统") },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.primary)
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(24.dp)
        ) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text("抽卡规则", style = MaterialTheme.typography.titleMedium)
                    Text("每消耗10一级货币，可获得50基础二级货币")
                    Text("暴击概率: 2倍(20%), 3倍(10%), 5倍(5%)")
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("⭐ 试试你的运气吧！", color = MaterialTheme.colorScheme.primary)
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("抽卡次数: ")
                IconButton(onClick = { if (drawCount > 1) drawCount-- }) {
                    Icon(Icons.Default.Remove, contentDescription = "减少")
                }
                Text("$drawCount", style = MaterialTheme.typography.headlineSmall)
                IconButton(onClick = { drawCount++ }) {
                    Icon(Icons.Default.Add, contentDescription = "增加")
                }
            }

            Button(
                onClick = {
                    scope.launch {
                        val cost = drawCount * 10
                        viewModel.draw(cost)
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text("花费 ${drawCount * 10} 一级货币抽卡")
            }

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(
                        Icons.Default.Casino,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.primary
                    )
                    Text("点击抽卡，获取二级货币", style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}