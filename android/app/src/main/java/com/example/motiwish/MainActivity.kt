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

//图标导入
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*

import androidx.navigation.compose.currentBackStackEntryAsState

class MainActivity : ComponentActivity() {

    private lateinit var database: AppDatabase
    private lateinit var taskRepository: TaskRepository
    private lateinit var currencyRepository: CurrencyRepository
    private lateinit var wishRepository: WishRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize database and repositories
        database = AppDatabase.getDatabase(this)
        taskRepository = TaskRepository(database.taskDao())
        currencyRepository = CurrencyRepository(database.currencyDao())
        wishRepository = WishRepository(database.wishDao())

        // Schedule daily reminder for daily tasks
        scheduleDailyReminder()

        setContent {
            MySelfManagementAppTheme {
                val navController = rememberNavController()

                // 获取当前路由的状态，用来判断是否在 splash 页面
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentRoute = navBackStackEntry?.destination?.route

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
                                    "tasks" to "任务",
                                    "gacha" to "抽卡",
                                    "shop" to "商店",
                                    "profile" to "我的"
                                    //"currency" to "货币",
                                    //"history" to "历史"
                                )
                                val currentRoute =
                                    navController.currentBackStackEntry?.destination?.route
                                items.forEach { (route, label) ->
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
                                        icon = {
                                            Icon(
                                                Icons.Default.Circle,
                                                contentDescription = null
                                            )
                                        },
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
                                SplashScreen(navController)
                            }
                            composable("tasks") {
                                val viewModel = TaskViewModel(taskRepository, currencyRepository)
                                TaskScreen(viewModel, navController)
                            }
                            composable("gacha") {
                                val viewModel = GachaViewModel(currencyRepository)
                                GachaScreen(viewModel)
                            }
                            composable("shop") {
                                val viewModel = ShopViewModel(wishRepository, currencyRepository)
                                ShopScreen(viewModel, navController)
                            }

                            composable("profile") {
                                val currencyViewModel = CurrencyViewModel(currencyRepository)
                                val historyViewModel = HistoryViewModel(taskRepository, currencyRepository)
                                ProfileScreen(navController, currencyViewModel, historyViewModel)
                            }

                            composable("currency") {
                                val viewModel = CurrencyViewModel(currencyRepository)
                                CurrencyScreen(viewModel)
                            }
                            composable("history") {
                                val viewModel = HistoryViewModel(taskRepository, currencyRepository)
                                HistoryScreen(viewModel)
                            }
                            composable(
                                "addWish?wishId={wishId}",
                                arguments = listOf(navArgument("wishId") { defaultValue = -1 })
                            ) { backStackEntry ->
                                val wishId = backStackEntry.arguments?.getInt("wishId") ?: -1
                                val viewModel = ShopViewModel(wishRepository, currencyRepository)
                                AddWishScreen(viewModel, navController, wishId)
                            }
                            composable("addPeriodicTask") {
                                val viewModel = TaskViewModel(taskRepository, currencyRepository)
                                AddPeriodicTaskScreen(viewModel, navController)
                            }
                            composable("addOneShotTask") {
                                val viewModel = TaskViewModel(taskRepository, currencyRepository)
                                AddOneShotTaskScreen(viewModel, navController)
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