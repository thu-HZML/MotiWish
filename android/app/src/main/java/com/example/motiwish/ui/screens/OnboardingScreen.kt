package com.example.motiwish.ui.screens

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.ExperimentalAnimationApi
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.motiwish.data.network.StableProfileRequest
import com.example.motiwish.viewmodel.UserViewModel
import androidx.navigation.NavController

@OptIn(ExperimentalMaterial3Api::class, ExperimentalAnimationApi::class)
@Composable
fun OnboardingScreen(viewModel: UserViewModel, navController: NavController) {
    // 步骤控制：0 = 基础信息， 1 = 行为画像
    var currentStep by remember { mutableIntStateOf(0) }

    // --- 第一步：基础信息状态 ---
    var nickname by remember { mutableStateOf("") }
    var gender by remember { mutableStateOf("unknown") }

    // --- 第二步：行为画像状态 ---
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

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (currentStep == 0) "1/2 完善基础档案" else "2/2 自我探索画像") },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
            )
        }
    ) { paddingValues ->
        AnimatedContent(targetState = currentStep, label = "step_transition") { step ->
            if (step == 0) {
                // ================= 第一步：基础信息 UI =================
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues)
                        .padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Text("欢迎来到 MotiWish！", fontSize = 24.sp, fontWeight = FontWeight.Bold)
                    Text("怎么称呼你呢？", color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 8.dp, bottom = 24.dp))

                    OutlinedTextField(
                        value = nickname,
                        onValueChange = { nickname = it },
                        label = { Text("你的昵称") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(24.dp))
                    SingleChoiceCard(
                        title = "你的性别是？(可选)",
                        options = mapOf("male" to "男生", "female" to "女生", "unknown" to "保密"),
                        selected = gender,
                        onSelectionChange = { gender = it }
                    )

                    Spacer(modifier = Modifier.height(48.dp))
                    Button(
                        onClick = { currentStep = 1 }, // 进入下一步
                        modifier = Modifier.fillMaxWidth().height(50.dp)
                    ) {
                        Text("下一步")
                    }
                }
            } else {
                // ================= 第二步：行为画像 UI =================
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(paddingValues).padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    item { Text("这些数据将帮助 AI 为你量身定制任务难度与奖励机制！", color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    item { MultiChoiceCard("自我管理中常遇到的困难？", mapOf("procrastination" to "拖延", "distraction" to "注意力分散", "low_energy" to "精力不足"), challenges) { challenges = it } }
                    item { MultiChoiceCard("什么最能驱动你？", mapOf("achievement" to "成就感", "collection" to "收集癖", "narrative" to "成长叙事"), motivations) { motivations = it } }
                    item { SingleChoiceCard("奖励偏好？", mapOf("instant" to "即时小奖励", "big_later" to "延迟大奖励"), reward) { reward = it } }
                    item { SingleChoiceCard("惩罚接受度？", mapOf("low" to "低", "medium" to "中", "high" to "高"), penalty) { penalty = it } }
                    item { SingleChoiceCard("压力敏感度？", mapOf("low" to "低", "medium" to "中", "high" to "高"), stress) { stress = it } }
                    item { SingleChoiceCard("作息类型？", mapOf("morning" to "早起鸟", "night" to "夜猫子", "flexible" to "不固定"), chronotype) { chronotype = it } }
                    item { MultiChoiceCard("精力高峰时段？", mapOf("morning" to "上午", "afternoon" to "下午", "evening" to "晚上"), energyPeaks) { energyPeaks = it } }
                    item { SingleChoiceCard("任务粒度偏好？", mapOf("small" to "拆分小任务", "large" to "大块任务"), taskGranularity) { taskGranularity = it } }
                    item { SingleChoiceCard("计划风格？", mapOf("structured" to "严格按计划", "flexible" to "随性灵活"), planningStyle) { planningStyle = it } }

                    item {
                        Button(
                            onClick = {
                                // 组装请求对象并提交终极方法
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
                                // 【调用二合一提交】
                                viewModel.submitOnboarding(nickname, gender, request) {
                                    navController.popBackStack()
                                }
                            },
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(bottom = 24.dp)
                                .height(50.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                        ) {
                            Text("完成并开启 MotiWish")
                        }
                    }
                }
            }
        }
    }
}