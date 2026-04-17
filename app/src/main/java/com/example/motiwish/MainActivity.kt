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
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.motiwish.data.database.AppDatabase
import com.example.motiwish.data.repository.*
import com.example.motiwish.ui.screens.*
import com.example.motiwish.ui.theme.MySelfManagementAppTheme
import com.example.motiwish.viewmodel.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import androidx.work.*
import java.util.concurrent.TimeUnit

//图标导入
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*

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

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    Scaffold(
                        bottomBar = {
                            NavigationBar(
                                containerColor = Color.White,
                                tonalElevation = 0.dp
                            ) {
                                val items = listOf(
                                    "tasks" to "任务",
                                    "gacha" to "抽卡",
                                    "shop" to "商店",
                                    "currency" to "货币",
                                    "history" to "历史"
                                )
                                val currentRoute = navController.currentBackStackEntry?.destination?.route
                                items.forEach { (route, label) ->
                                    NavigationBarItem(
                                        selected = currentRoute == route,
                                        onClick = { navController.navigate(route) {
                                            popUpTo(navController.graph.startDestinationId) {
                                                saveState = true
                                            }
                                            launchSingleTop = true
                                            restoreState = true
                                        } },
                                        icon = { Icon(Icons.Default.Circle, contentDescription = null) },
                                        label = { Text(label) }
                                    )
                                }
                            }
                        }
                    ) { innerPadding ->
                        NavHost(
                            navController = navController,
                            startDestination = "tasks",
                            modifier = Modifier.padding(innerPadding)
                        ) {
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