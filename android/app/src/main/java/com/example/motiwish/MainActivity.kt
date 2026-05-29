package com.example.motiwish

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.motiwish.data.database.AppDatabase
import com.example.motiwish.data.repository.*
import com.example.motiwish.ui.screens.*
import com.example.motiwish.ui.theme.MySelfManagementAppTheme
import com.example.motiwish.viewmodel.*
import androidx.work.*
import java.util.concurrent.TimeUnit

// 图标导入
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.EventNote
import androidx.compose.material.icons.filled.*
import androidx.navigation.compose.currentBackStackEntryAsState

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import com.example.motiwish.data.network.AuthApi

import okhttp3.OkHttpClient
import com.example.motiwish.data.network.TokenManager
import com.example.motiwish.data.network.AuthInterceptor
import com.example.motiwish.data.network.UserApi

class MainActivity : ComponentActivity() {

    private lateinit var database: AppDatabase
    private lateinit var taskRepository: TaskRepository
    private lateinit var currencyRepository: CurrencyRepository
    private lateinit var wishRepository: WishRepository

    private lateinit var authApi: AuthApi

    private lateinit var userViewModel: UserViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 初始化数据库和仓库
        database = AppDatabase.getDatabase(this)
        taskRepository = TaskRepository(database.taskDao())
        currencyRepository = CurrencyRepository(database.currencyDao())
        wishRepository = WishRepository(database.wishDao())

        // 初始化 Token 管理器
        TokenManager.init(this)

        // 创建 OkHttpClient 并添加 AuthInterceptor
        val okHttpClient = OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor())
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl("http://8.147.57.94/")
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        authApi = retrofit.create(AuthApi::class.java)

        // 【新增 3】创建 UserApi 和 UserViewModel
        val userApi = retrofit.create(UserApi::class.java)
        userViewModel = ViewModelProvider(this, object : ViewModelProvider.Factory {
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                return UserViewModel(userApi) as T
            }
        })[UserViewModel::class.java]

        scheduleDailyReminder()

        setContent {
            MySelfManagementAppTheme {
                val navController = rememberNavController()
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentRoute = navBackStackEntry?.destination?.route

                // 【核心修改】：在 NavHost 外部创建共享的 ViewModel 实例
                // 这样无论在哪个页面，读取的都是同一个内存状态，实现秒级同步
                val currencyViewModel = remember { CurrencyViewModel(currencyRepository) }
                val shopViewModel = remember { ShopViewModel(wishRepository, currencyRepository) }
                val gachaViewModel = remember { GachaViewModel(currencyRepository) }
                val historyViewModel = remember { HistoryViewModel(taskRepository, currencyRepository) }
                val taskViewModel = remember { TaskViewModel(taskRepository, currencyRepository) }

                val authViewModel: AuthViewModel = viewModel(
                    factory = object : ViewModelProvider.Factory {
                        @Suppress("UNCHECKED_CAST")
                        override fun <T : ViewModel> create(modelClass: Class<T>): T {
                            return AuthViewModel(authApi) as T
                        }
                    }
                )

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    Scaffold(
                        bottomBar = {
                            if (currentRoute != "splash") {
                                NavigationBar(
                                    containerColor = Color.White,
                                    tonalElevation = 0.dp
                                ) {

                                    val items = listOf(
                                        Triple("tasks", "任务", Icons.Default.Checklist),
                                        Triple("history", "日程",
                                            Icons.AutoMirrored.Filled.EventNote
                                        ),
                                        Triple("store", "商城", Icons.Default.Store),
                                        Triple("profile", "我的", Icons.Default.Person)
                                    )

                                    items.forEach { (route, label, icon) ->
                                        NavigationBarItem(
                                            selected = currentRoute == route,
                                            onClick = {
                                                navController.navigate(route) {
                                                    popUpTo(navController.graph.startDestinationId) {
                                                        saveState = true
                                                    }
                                                    launchSingleTop = true
                                                    restoreState = true
                                                }
                                            },
                                            icon = { Icon(icon, contentDescription = null) },
                                            label = { Text(label) }
                                        )
                                    }
                                }
                            }
                        }
                    ) { innerPadding ->
                        NavHost(
                            navController = navController,
                            startDestination = "splash",
                            modifier = Modifier.padding(innerPadding)
                        ) {
                            composable("splash") {
                                SplashAuthScreen(
                                    navController = navController,
                                    viewModel = authViewModel
                                )
                            }

                            composable("tasks") {
                                TaskScreen(taskViewModel, navController)
                            }

                            // 【修改 2】：整合后的商城页面 (包含抽卡和商店)
                            composable("store") {
                                StoreScreen(
                                    gachaViewModel = gachaViewModel,
                                    shopViewModel = shopViewModel,
                                    currencyViewModel = currencyViewModel,
                                    navController = navController
                                )
                            }

                            // 【修改 3】：整合后的个人主页 (包含余额展示和历史入口)
                            composable("profile") {
                                ProfileScreen(
                                    navController = navController,
                                    currencyViewModel = currencyViewModel,
                                    historyViewModel = historyViewModel,
                                    userViewModel = userViewModel
                                )
                            }

                            // 这里的 history 路由保留，供个人主页跳转
                            composable("history") {
                                HistoryScreen(historyViewModel)
                            }

                            composable(
                                "addWish?wishId={wishId}",
                                arguments = listOf(navArgument("wishId") { defaultValue = -1 })
                            ) { backStackEntry ->
                                val wishId = backStackEntry.arguments?.getInt("wishId") ?: -1
                                AddWishScreen(shopViewModel, navController, wishId)
                            }

                            composable("addPeriodicTask") {
                                AddPeriodicTaskScreen(taskViewModel, navController)
                            }
                            composable("addOneShotTask") {
                                AddOneShotTaskScreen(taskViewModel, navController)
                            }
                        }
                    }
                }
            }
        }
    }

    private fun scheduleDailyReminder() {
        val workRequest = PeriodicWorkRequestBuilder<DailyReminderWorker>(
            1, TimeUnit.DAYS
        ).setInitialDelay(1, TimeUnit.MINUTES).build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "daily_reminder",
            ExistingPeriodicWorkPolicy.KEEP,
            workRequest
        )
    }
}