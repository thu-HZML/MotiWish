package com.example.motiwish.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
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
import androidx.compose.material.icons.filled.AutoAwesome

@Composable
fun SplashAuthScreen(
    navController: NavController,
    viewModel: AuthViewModel
) {
    val showLoginPanel by viewModel.showLoginPanel.collectAsState()
    val isRegisterMode by viewModel.isRegisterMode.collectAsState()
    val isForgotPasswordMode by viewModel.isForgotPasswordMode.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val isSendingEmailCode by viewModel.isSendingEmailCode.collectAsState()
    val emailCodeCooldown by viewModel.emailCodeCooldown.collectAsState()

    val username by viewModel.username.collectAsState()
    val password by viewModel.password.collectAsState()
    val confirmPassword by viewModel.confirmPassword.collectAsState()
    val email by viewModel.email.collectAsState()
    val emailCode by viewModel.emailCode.collectAsState()
    val resetEmail by viewModel.resetEmail.collectAsState()
    val resetCode by viewModel.resetCode.collectAsState()
    val resetPassword by viewModel.resetPassword.collectAsState()
    val resetConfirmPassword by viewModel.resetConfirmPassword.collectAsState()

    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        viewModel.authEvent.collect { event ->
            when (event) {
                is AuthViewModel.AuthEvent.NavigateToMain -> {
                    navController.navigate("tasks") {
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
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.primary)
                .padding(padding),
            contentAlignment = Alignment.Center
        ) {
            // 1. Logo 区域
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.offset(y = if (showLoginPanel) (-180).dp else 0.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.AutoAwesome,
                    contentDescription = "MotiWish Logo",
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

            // 2. 动态登录/注册卡片
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
                        .padding(bottom = 48.dp),
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier
                            .padding(24.dp)
                            .fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        // 动态标题
                        Text(
                            text = when {
                                isForgotPasswordMode -> "重置密码"
                                isRegisterMode -> "创建新账号"
                                else -> "欢迎回来"
                            },
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(24.dp))

                        if (isForgotPasswordMode) {
                            OutlinedTextField(
                                value = resetEmail,
                                onValueChange = { viewModel.resetEmail.value = it },
                                label = { Text("电子邮箱") },
                                leadingIcon = { Icon(Icons.Default.Email, contentDescription = null) },
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                OutlinedTextField(
                                    value = resetCode,
                                    onValueChange = { viewModel.resetCode.value = it },
                                    label = { Text("验证码") },
                                    modifier = Modifier.weight(1f),
                                    singleLine = true
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                OutlinedButton(
                                    onClick = { viewModel.sendEmailCode("password_reset") },
                                    enabled = !isSendingEmailCode && emailCodeCooldown == 0,
                                    modifier = Modifier.height(56.dp)
                                ) {
                                    Text(if (emailCodeCooldown > 0) "${emailCodeCooldown}s" else "发送")
                                }
                            }
                            Spacer(modifier = Modifier.height(12.dp))
                            OutlinedTextField(
                                value = resetPassword,
                                onValueChange = { viewModel.resetPassword.value = it },
                                label = { Text("新密码") },
                                leadingIcon = { Icon(Icons.Default.Lock, contentDescription = null) },
                                visualTransformation = PasswordVisualTransformation(),
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            OutlinedTextField(
                                value = resetConfirmPassword,
                                onValueChange = { viewModel.resetConfirmPassword.value = it },
                                label = { Text("确认新密码") },
                                leadingIcon = { Icon(Icons.Default.Lock, contentDescription = null) },
                                visualTransformation = PasswordVisualTransformation(),
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true
                            )
                        } else {

                        // 用户名输入框
                        OutlinedTextField(
                            value = username,
                            onValueChange = { viewModel.username.value = it },
                            label = { Text("用户名或邮箱") },
                            leadingIcon = { Icon(Icons.Default.Person, contentDescription = null) },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        Spacer(modifier = Modifier.height(16.dp))

                        // 邮箱输入框：仅在注册模式下可见，带展开动画
                        AnimatedVisibility(
                            visible = isRegisterMode,
                            enter = fadeIn() + slideInVertically(initialOffsetY = { -it / 2 }),
                            exit = fadeOut()
                        ) {
                            Column {
                                OutlinedTextField(
                                    value = email,
                                    onValueChange = { viewModel.email.value = it },
                                    label = { Text("电子邮箱") },
                                    leadingIcon = { Icon(Icons.Default.Email, contentDescription = null) },
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true
                                )
                                Spacer(modifier = Modifier.height(12.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    OutlinedTextField(
                                        value = emailCode,
                                        onValueChange = { viewModel.emailCode.value = it },
                                        label = { Text("验证码") },
                                        modifier = Modifier.weight(1f),
                                        singleLine = true
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                    OutlinedButton(
                                        onClick = { viewModel.sendEmailCode("register") },
                                        enabled = !isSendingEmailCode && emailCodeCooldown == 0,
                                        modifier = Modifier.height(56.dp)
                                    ) {
                                        Text(if (emailCodeCooldown > 0) "${emailCodeCooldown}s" else "发送")
                                    }
                                }
                                Spacer(modifier = Modifier.height(16.dp))
                            }
                        }

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
                        AnimatedVisibility(
                            visible = isRegisterMode,
                            enter = fadeIn() + slideInVertically(initialOffsetY = { -it / 2 }),
                            exit = fadeOut()
                        ) {
                            Column {
                                // 把间距放在动画内部，保证切换登录模式时不会多出多余的空白
                                Spacer(modifier = Modifier.height(16.dp))
                                OutlinedTextField(
                                    value = confirmPassword,
                                    onValueChange = { viewModel.confirmPassword.value = it },
                                    label = { Text("确认密码") },
                                    leadingIcon = { Icon(Icons.Default.Lock, contentDescription = null) },
                                    visualTransformation = PasswordVisualTransformation(),
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true
                                )
                            }
                        }
                        }
                        Spacer(modifier = Modifier.height(28.dp))

                        // 主操作按钮（登录 或 注册）
                        Button(
                            onClick = {
                                when {
                                    isForgotPasswordMode -> viewModel.resetPasswordByEmail()
                                    isRegisterMode -> viewModel.register()
                                    else -> viewModel.login()
                                }
                            },
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
                                Text(
                                    text = if (isRegisterMode) "注 册" else "登 录",
                                    style = MaterialTheme.typography.titleMedium
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        // 切换模式按钮
                        TextButton(onClick = {
                            if (isForgotPasswordMode) viewModel.backToLoginMode() else viewModel.toggleMode()
                        }) {
                            Text(
                                text = if (isRegisterMode) "已有账号？立即登录" else "没有账号？切换到注册",
                                color = MaterialTheme.colorScheme.primary,
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                        AnimatedVisibility(visible = !isRegisterMode && !isForgotPasswordMode) {
                            TextButton(onClick = { viewModel.enterForgotPasswordMode() }) {
                                Text(
                                    text = "忘记密码？",
                                    color = MaterialTheme.colorScheme.primary,
                                    style = MaterialTheme.typography.bodyMedium
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
