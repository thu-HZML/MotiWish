package com.example.motiwish.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.example.motiwish.data.network.StableProfileRequest
import com.example.motiwish.viewmodel.UserViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun QuestionnaireScreen(viewModel: UserViewModel, navController: NavController) {
    val stableData by viewModel.stableProfileData.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {
        viewModel.fetchStableProfile()
    }
    // --- 状态保存区 ---
    var challenges by remember { mutableStateOf(setOf<String>()) }
    var motivations by remember { mutableStateOf(setOf<String>()) }
    var reward by remember { mutableStateOf("") }
    var penalty by remember { mutableStateOf("") }
    var stress by remember { mutableStateOf("") }
    var disciplineScore by remember { mutableFloatStateOf(5f) }
    var chronotype by remember { mutableStateOf("") }
    var energyPeaks by remember { mutableStateOf(setOf<String>()) }
    var taskGranularity by remember { mutableStateOf("") }
    var planningStyle by remember { mutableStateOf("") }


    LaunchedEffect(stableData) {
        stableData?.let { data ->
            // 过滤掉列表里的 "unspecified" 占位符
            challenges = data.self_management_challenges?.filter { it != "unspecified" }?.toSet() ?: setOf()
            motivations = data.motivation_preferences?.filter { it != "unspecified" }?.toSet() ?: setOf()
            energyPeaks = data.energy_peak_periods?.filter { it != "unspecified" }?.toSet() ?: setOf()

            // 过滤掉字符串里的 "undisclosed" 占位符
            reward = if (data.reward_preference == "undisclosed") "" else (data.reward_preference ?: "")
            penalty = if (data.penalty_tolerance == "undisclosed") "" else (data.penalty_tolerance ?: "")
            stress = if (data.stress_sensitivity == "undisclosed") "" else (data.stress_sensitivity ?: "")
            chronotype = if (data.chronotype == "undisclosed") "" else (data.chronotype ?: "")
            taskGranularity = if (data.task_granularity_preference == "undisclosed") "" else (data.task_granularity_preference ?: "")
            planningStyle = if (data.planning_style_preference == "undisclosed") "" else (data.planning_style_preference ?: "")

            // 数值直接赋值
            disciplineScore = data.self_discipline_score?.toFloat() ?: 5f
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("自我探索画像") },
                navigationIcon = {
                    IconButton(onClick = {
                        //viewModel.dismissQuestionnaire()
                        navController.popBackStack()
                    }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Text(
                    text = "完成这份画像，MotiWish 能为你推荐更适合的愿望和任务定价哦！",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
            }

            // 1. 痛点 (多选)
            item {
                MultiChoiceCard(
                    title = "你在自我管理中最常遇到哪些困难？(多选)",
                    options = mapOf(
                        "procrastination" to "拖延", "distraction" to "注意力分散",
                        "perfectionism" to "完美主义", "overplanning" to "计划过载",
                        "consistency" to "难以坚持", "interruption" to "频繁被打断",
                        "low_energy" to "精力不足"
                    ),
                    selected = challenges,
                    onSelectionChange = { challenges = it }
                )
            }

            // 2. 动机 (多选)
            item {
                MultiChoiceCard(
                    title = "什么最能驱动你持续完成任务？(多选)",
                    options = mapOf(
                        "achievement" to "成就驱动", "collection" to "收集驱动",
                        "social" to "社交驱动", "competition" to "竞争驱动", "narrative" to "成长叙事驱动"
                    ),
                    selected = motivations,
                    onSelectionChange = { motivations = it }
                )
            }

            // 3. 奖励偏好 (单选)
            item {
                SingleChoiceCard(
                    title = "你更喜欢哪种奖励方式？",
                    options = mapOf("instant" to "偏好即时小奖励", "big_later" to "偏好延迟大奖励", "balanced" to "二者平衡"),
                    selected = reward,
                    onSelectionChange = { reward = it }
                )
            }

            // 4. 惩罚接受度 & 5. 压力敏感度 (单选)
            item {
                SingleChoiceCard(
                    title = "你对惩罚机制的接受度如何？",
                    options = mapOf("low" to "低", "medium" to "中", "high" to "高"),
                    selected = penalty,
                    onSelectionChange = { penalty = it }
                )
            }
            item {
                SingleChoiceCard(
                    title = "当压力增加时，你会受到多大影响？",
                    options = mapOf("low" to "低", "medium" to "中", "high" to "高"),
                    selected = stress,
                    onSelectionChange = { stress = it }
                )
            }

            // 6. 自律打分 (滑动条)
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("如果满分 10 分，你会给自己的自律程度打几分？: ${disciplineScore.toInt()}", fontWeight = FontWeight.Bold)
                        Slider(
                            value = disciplineScore,
                            onValueChange = { disciplineScore = it },
                            valueRange = 1f..10f,
                            steps = 8
                        )
                    }
                }
            }

            // 7. 作息 (单选) & 8. 精力 (多选)
            item {
                SingleChoiceCard(
                    title = "你更接近哪种作息类型？",
                    options = mapOf("morning" to "早起鸟", "night" to "夜猫子", "flexible" to "不固定"),
                    selected = chronotype,
                    onSelectionChange = { chronotype = it }
                )
            }
            item {
                MultiChoiceCard(
                    title = "你通常在哪些时段精力更好？(多选)",
                    options = mapOf("morning" to "上午", "afternoon" to "下午", "evening" to "晚上", "late_night" to "深夜"),
                    selected = energyPeaks,
                    onSelectionChange = { energyPeaks = it }
                )
            }

            // 9. 任务粒度 & 10. 计划风格 (单选)
            item {
                SingleChoiceCard(
                    title = "你更喜欢怎样的任务粒度？",
                    options = mapOf("small" to "喜欢拆分小任务", "balanced" to "大小都可以", "large" to "偏好大块任务"),
                    selected = taskGranularity,
                    onSelectionChange = { taskGranularity = it }
                )
            }
            item {
                SingleChoiceCard(
                    title = "你更偏好怎样的计划方式？",
                    options = mapOf("structured" to "严格按计划执行", "flexible" to "随性灵活安排", "mixed" to "二者结合"),
                    selected = planningStyle,
                    onSelectionChange = { planningStyle = it }
                )
            }

            // --- 提交按钮 ---
            item {
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = {
                        // 组装请求对象
                        val request = StableProfileRequest(
                            self_management_challenges = challenges.toList().ifEmpty { listOf("unspecified") },
                            motivation_preferences = motivations.toList().ifEmpty { listOf("unspecified") },
                            reward_preference = reward.ifEmpty { "undisclosed" },
                            penalty_tolerance = penalty.ifEmpty { "undisclosed" },
                            stress_sensitivity = stress.ifEmpty { "undisclosed" },
                            self_discipline_score = disciplineScore.toInt(),
                            chronotype = chronotype.ifEmpty { "undisclosed" },
                            energy_peak_periods = energyPeaks.toList().ifEmpty { listOf("unspecified") },
                            task_granularity_preference = taskGranularity.ifEmpty { "undisclosed" },
                            planning_style_preference = planningStyle.ifEmpty { "undisclosed" }
                        )
                        viewModel.updateStableProfileData(request)
                        navController.popBackStack()
                    },
                    modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Text("保存画像")
                }
            }
        }
    }
}

// ================= UI 辅助组件 =================

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun MultiChoiceCard(title: String, options: Map<String, String>, selected: Set<String>, onSelectionChange: (Set<String>) -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 8.dp))
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                options.forEach { (key, label) ->
                    val isSelected = selected.contains(key)
                    Surface(
                        modifier = Modifier.clickable {
                            val newSet = if (isSelected) selected - key else selected + key
                            onSelectionChange(newSet)
                        },
                        shape = RoundedCornerShape(16.dp),
                        color = if (isSelected) MaterialTheme.colorScheme.primary else Color.Transparent,
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary)
                    ) {
                        Text(
                            text = label,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                            color = if (isSelected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun SingleChoiceCard(title: String, options: Map<String, String>, selected: String, onSelectionChange: (String) -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 8.dp))
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                options.forEach { (key, label) ->
                    val isSelected = selected == key
                    Surface(
                        modifier = Modifier.clickable { onSelectionChange(key) },
                        shape = RoundedCornerShape(16.dp),
                        color = if (isSelected) MaterialTheme.colorScheme.primary else Color.Transparent,
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary)
                    ) {
                        Text(
                            text = label,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                            color = if (isSelected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }
        }
    }
}