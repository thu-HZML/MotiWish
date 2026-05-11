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

