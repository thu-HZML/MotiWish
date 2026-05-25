package com.example.motiwish.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.example.motiwish.viewmodel.AuthViewModel

@Composable
fun SplashAuthScreen(
    navController: NavController,
    viewModel: AuthViewModel
) {
    val showLoginPanel by viewModel.showLoginPanel.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val username by viewModel.username.collectAsState()
    val password by viewModel.password.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    // 处理 ViewModel 发来的导航和报错事件
    LaunchedEffect(Unit) {
        viewModel.authEvent.collect { event ->
            when (event) {
                is AuthViewModel.AuthEvent.NavigateToMain -> {
                    navController.navigate("tasks") {
                        // 登录成功后，清空返回栈，防止用户按返回键回到登录页
                        popUpTo("splash") { inclusive = true }
                    }
                }
                is AuthViewModel.AuthEvent.ShowError -> {
                    snackbarHostState.showSnackbar(event.message)
                }
            }
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { padding ->
        // 底层：蓝色的启动页背景
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.primary) // 使用主题的蓝色
                .padding(padding),
            contentAlignment = Alignment.Center
        ) {
            // 1. Logo 区域 (根据是否显示登录框，Logo 可能会稍微上移)
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.offset(y = if (showLoginPanel) (-150).dp else 0.dp)
            ) {
                // 替换为你真实的 App Logo
                Icon(
                    imageVector = Icons.Default.Lock,
                    contentDescription = "Logo",
                    modifier = Modifier.size(80.dp),
                    tint = Color.White
                )
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "MotiWish",
                    style = MaterialTheme.typography.displaySmall,
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
            }

            // 2. 登录弹窗卡片 (带有向上滑动和淡入的动画)
            AnimatedVisibility(
                visible = showLoginPanel,
                enter = fadeIn(animationSpec = tween(500)) + slideInVertically(
                    initialOffsetY = { it / 2 },
                    animationSpec = tween(500)
                ),
                modifier = Modifier.align(Alignment.BottomCenter)
            ) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 24.dp)
                        .padding(bottom = 64.dp), // 距离底部一段距离
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier
                            .padding(24.dp)
                            .fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "欢迎回来",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(24.dp))

                        // 账号输入框
                        OutlinedTextField(
                            value = username,
                            onValueChange = { viewModel.username.value = it },
                            label = { Text("用户名") },
                            leadingIcon = { Icon(Icons.Default.Person, contentDescription = null) },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        Spacer(modifier = Modifier.height(16.dp))

                        // 密码输入框
                        OutlinedTextField(
                            value = password,
                            onValueChange = { viewModel.password.value = it },
                            label = { Text("密码") },
                            leadingIcon = { Icon(Icons.Default.Lock, contentDescription = null) },
                            visualTransformation = PasswordVisualTransformation(),
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        Spacer(modifier = Modifier.height(32.dp))

                        // 登录按钮
                        Button(
                            onClick = { viewModel.login() },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(50.dp),
                            enabled = !isLoading,
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            if (isLoading) {
                                CircularProgressIndicator(
                                    color = Color.White,
                                    modifier = Modifier.size(24.dp),
                                    strokeWidth = 2.dp
                                )
                            } else {
                                Text("登 录", style = MaterialTheme.typography.titleMedium)
                            }
                        }
                    }
                }
            }
        }
    }
}