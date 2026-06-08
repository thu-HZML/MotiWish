package com.example.motiwish.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.motiwish.viewmodel.UserViewModel

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun DynamicProfileSheet(viewModel: UserViewModel, onDismiss: () -> Unit) {
    // skipPartiallyExpanded = true：因为字段变多，让底栏一弹出来就占满屏幕，防止卡在一半
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val existingData by viewModel.dynamicProfileData.collectAsState()

    // --- 8 大状态回显区 ---
    var stageTags by remember { mutableStateOf(existingData?.current_stage_tags?.toSet() ?: emptySet()) }
    var stressLevel by remember { mutableFloatStateOf(existingData?.stress_level?.toFloat() ?: 3f) }
    var sleepQuality by remember { mutableStateOf(existingData?.sleep_quality ?: "medium") }
    var moodState by remember { mutableStateOf(existingData?.mood_state ?: "medium") }
    var timeLevel by remember { mutableStateOf(existingData?.available_time_level ?: "normal") }

    var weeklyHours by remember { mutableStateOf(existingData?.weekly_time_budget_hours?.toString() ?: "") }
    var topGoal by remember { mutableStateOf(existingData?.current_top_goal ?: "") }
    var mainBlocker by remember { mutableStateOf(existingData?.current_main_blocker ?: "") }

    ModalBottomSheet(
        onDismissRequest = {
            viewModel.skipDynamicPrompt()
            onDismiss()
        },
        sheetState = sheetState
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp)
                // ✅ 开启全局垂直滚动，完美容纳所有表单
                .verticalScroll(rememberScrollState())
                .padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 头部标题
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("📅 本周状态同步", style = MaterialTheme.typography.titleLarge)
                TextButton(onClick = {
                    viewModel.skipDynamicPrompt()
                    onDismiss()
                }) {
                    Text("跳过", color = MaterialTheme.colorScheme.outline)
                }
            }

            // 1. 当前阶段 (多选)
            Text("当前处于什么阶段？(可多选)", style = MaterialTheme.typography.bodyMedium)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                // ✅ 修复：加入 holiday，并将 job_hunting 改为 job_search
                listOf(
                    "exam" to "📚 备考",
                    "crunch" to "⚡ 冲刺/加班",
                    "holiday" to "🏝️ 假期",
                    "job_search" to "💼 求职",
                    "transition" to "🔄 迷茫/过渡",
                    "recovery" to "🛌 休整"
                ).forEach { (key, label) ->
                    FilterChip(
                        selected = stageTags.contains(key),
                        onClick = {
                            stageTags = if (stageTags.contains(key)) stageTags - key else stageTags + key
                        },
                        label = { Text(label) }
                    )
                }
            }

            // 2. 压力 (滑动条) - 保持不变
            Text("这周压力大吗？(1-5)", style = MaterialTheme.typography.bodyMedium)
            Slider(
                value = stressLevel,
                onValueChange = { stressLevel = it },
                valueRange = 1f..5f,
                steps = 3,
                modifier = Modifier.fillMaxWidth()
            )

            // 3. 睡眠 (单选) - 保持不变
            Text("近期睡眠质量？", style = MaterialTheme.typography.bodyMedium)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("high" to "😎 充足", "medium" to "😐 一般", "low" to "🥱 缺觉").forEach { (key, label) ->
                    FilterChip(selected = sleepQuality == key, onClick = { sleepQuality = key }, label = { Text(label) })
                }
            }

            // 4. 情绪 (单选) - 保持不变
            Text("近期情绪状态？", style = MaterialTheme.typography.bodyMedium)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("high" to "😃 极佳", "medium" to "😐 平稳", "low" to "😔 低落").forEach { (key, label) ->
                    FilterChip(selected = moodState == key, onClick = { moodState = key }, label = { Text(label) })
                }
            }

            // 5. 可支配时间 (单选)
            Text("最近可支配时间？", style = MaterialTheme.typography.bodyMedium)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                // ✅ 修复：将 abundant 改为后端真实的 ample
                listOf("ample" to "🟢 充足", "normal" to "🟡 正常", "limited" to "🔴 紧张").forEach { (key, label) ->
                    FilterChip(selected = timeLevel == key, onClick = { timeLevel = key }, label = { Text(label) })
                }
            }

            // 6. 本周预算时间 (数字输入)
            OutlinedTextField(
                value = weeklyHours,
                onValueChange = { weeklyHours = it },
                label = { Text("本周预计可投入总时长 (小时)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth()
            )

            // 7. 当前核心目标 (文本)
            OutlinedTextField(
                value = topGoal,
                onValueChange = { topGoal = it },
                label = { Text("本周最想搞定的一件事？") },
                modifier = Modifier.fillMaxWidth()
            )

            // 8. 当前最大阻力 (文本)
            OutlinedTextField(
                value = mainBlocker,
                onValueChange = { mainBlocker = it },
                label = { Text("当前遇到的最大阻碍是什么？") },
                modifier = Modifier.fillMaxWidth()
            )

            // 提交按钮
            Button(
                onClick = {
                    viewModel.submitDynamicProfile(
                        stageTags = stageTags,
                        stressLevel = stressLevel.toInt(),
                        sleepQuality = sleepQuality,
                        moodState = moodState,
                        availableTimeLevel = timeLevel,
                        topGoal = topGoal,
                        mainBlocker = mainBlocker,
                        weeklyHoursStr = weeklyHours
                    )
                    onDismiss()
                },
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp).height(50.dp)
            ) {
                Text("保存状态")
            }

            // 垫一点底部留白防止虚拟按键遮挡
            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}