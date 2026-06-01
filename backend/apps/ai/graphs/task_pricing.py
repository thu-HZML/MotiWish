import json
import os
from pathlib import Path
from typing import Any

from django.conf import settings
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from apps.tasks.models import DifficultyLevel, RecurrenceType, SettlementTrack, TaskType
from apps.users.models import DynamicProfile, StableProfile, User

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover - dependency is declared in requirements.
    ChatOpenAI = None


class TaskPricingState(TypedDict, total=False):
    user_id: int
    task_payload: dict[str, Any]
    feedback_history: list[dict[str, Any]]
    profile_snapshot: dict[str, Any]
    pricing_standard: str
    pricing_standard_version: str
    quote_payload: dict[str, Any]


def round_5(value: float) -> int:
    return int(round(value / 5) * 5)


def _clamp(value: int, lower: int, upper: int) -> int:
    return min(max(value, lower), upper)


def load_profile(state: TaskPricingState) -> dict[str, Any]:
    user = User.objects.get(pk=state["user_id"])
    StableProfile.objects.get_or_create(user=user)
    DynamicProfile.objects.get_or_create(user=user)
    return {"profile_snapshot": user.build_prompt_profile()}


def load_pricing_standard(state: TaskPricingState) -> dict[str, Any]:
    path = Path(settings.BASE_DIR) / "apps" / "ai" / "prompts" / "task_pricing_standard.md"
    return {
        "pricing_standard": path.read_text(encoding="utf-8"),
        "pricing_standard_version": "task_pricing_v1",
    }


def _difficulty(task_payload: dict[str, Any]) -> str:
    return task_payload.get("difficulty_level") or DifficultyLevel.MEDIUM


def _difficulty_index(task_payload: dict[str, Any]) -> int:
    return {
        DifficultyLevel.LOW: 0,
        DifficultyLevel.MEDIUM: 1,
        DifficultyLevel.HIGH: 2,
    }.get(_difficulty(task_payload), 1)


def _base_reward(task_payload: dict[str, Any]) -> int:
    task_type = task_payload.get("task_type") or TaskType.ONE_TIME
    recurrence = task_payload.get("recurrence") or RecurrenceType.NONE
    settlement_track = task_payload.get("settlement_track") or SettlementTrack.REGULAR
    difficulty_index = _difficulty_index(task_payload)

    if settlement_track == SettlementTrack.EXPLORATION:
        minutes = int(task_payload.get("estimated_focus_minutes") or 60)
        factor = [15, 25, 40][difficulty_index]
        return round_5(minutes / 60 * factor)

    if task_type == TaskType.DAILY or recurrence == RecurrenceType.DAILY:
        return [20, 30, 50][difficulty_index]

    if task_type == TaskType.RECURRING:
        if recurrence == RecurrenceType.MONTHLY:
            return [200, 300, 500][difficulty_index]
        return [60, 100, 150][difficulty_index]

    return [60, 160, 350][difficulty_index]


def _base_penalty(task_payload: dict[str, Any], reward: int) -> int:
    task_type = task_payload.get("task_type") or TaskType.ONE_TIME
    recurrence = task_payload.get("recurrence") or RecurrenceType.NONE
    settlement_track = task_payload.get("settlement_track") or SettlementTrack.REGULAR
    difficulty_index = _difficulty_index(task_payload)

    if settlement_track == SettlementTrack.EXPLORATION:
        return max(5, round_5(reward * 0.12))
    if task_type == TaskType.DAILY or recurrence == RecurrenceType.DAILY:
        return [5, 10, 15][difficulty_index]
    if task_type == TaskType.RECURRING:
        if recurrence == RecurrenceType.MONTHLY:
            return [30, 45, 60][difficulty_index]
        return [10, 20, 30][difficulty_index]
    return [10, 30, 70][difficulty_index]


def _pricing_bounds(task_payload: dict[str, Any], reward: int, penalty: int) -> dict[str, Any]:
    task_type = task_payload.get("task_type") or TaskType.ONE_TIME
    recurrence = task_payload.get("recurrence") or RecurrenceType.NONE
    settlement_track = task_payload.get("settlement_track") or SettlementTrack.REGULAR
    difficulty_index = _difficulty_index(task_payload)

    if settlement_track == SettlementTrack.EXPLORATION:
        reward_min = max(5, round_5(reward * 0.5))
        reward_max = max(reward_min + 5, round_5(reward * 2.2))
        penalty_min = 0
        penalty_max = max(5, round_5(reward_max * 0.2))
    elif task_type == TaskType.DAILY or recurrence == RecurrenceType.DAILY:
        reward_min, reward_max = [(10, 30), (15, 60), (30, 90)][difficulty_index]
        penalty_min, penalty_max = [(0, 10), (5, 15), (10, 25)][difficulty_index]
    elif task_type == TaskType.RECURRING and recurrence == RecurrenceType.MONTHLY:
        reward_min, reward_max = [(100, 350), (150, 600), (250, 900)][difficulty_index]
        penalty_min, penalty_max = [(15, 60), (25, 90), (30, 120)][difficulty_index]
    elif task_type == TaskType.RECURRING:
        reward_min, reward_max = [(30, 120), (50, 200), (80, 300)][difficulty_index]
        penalty_min, penalty_max = [(5, 25), (10, 40), (15, 60)][difficulty_index]
    else:
        reward_min, reward_max = [(30, 120), (80, 300), (180, 800)][difficulty_index]
        penalty_min, penalty_max = [(0, 25), (10, 60), (25, 120)][difficulty_index]

    reward_min = min(reward_min, reward)
    reward_max = max(reward_max, reward)
    penalty_min = min(penalty_min, penalty)
    penalty_max = min(max(penalty_max, penalty), reward_max)
    return {
        "reward_primary": {
            "min": reward_min,
            "max": reward_max,
            "recommended": reward,
        },
        "penalty_primary": {
            "min": penalty_min,
            "max": penalty_max,
            "recommended": penalty,
        },
    }


def _apply_profile_adjustment(reward: int, penalty: int, profile: dict[str, Any]) -> tuple[int, int, list[str]]:
    notes = []
    dynamic_available = profile.get("dynamic_profile_available")
    if dynamic_available:
        notes.append("检测到用户已有动态画像，建议保持惩罚温和，避免在压力波动期放大挫败。")
        penalty = round_5(penalty * 0.9)
    if profile.get("stable_profile_completed"):
        notes.append("用户稳定画像较完整，定价可信度略高。")
    return max(5, reward), max(0, penalty), notes


def _feedback_direction(feedback: dict[str, Any]) -> str:
    direction = feedback.get("feedback_direction")
    text = (feedback.get("feedback_text") or "").lower()
    if direction == "too_high" or "偏高" in text or "太高" in text:
        return "too_high"
    if direction == "too_low" or "偏低" in text or "太低" in text:
        return "too_low"
    return "detail"


def _step_down(value: int, lower: int, factor: float) -> int:
    if value <= lower:
        return lower
    return _clamp(min(round_5(value * factor), value - 5), lower, value)


def _step_up(value: int, upper: int, factor: float) -> int:
    if value >= upper:
        return upper
    return _clamp(max(round_5(value * factor), value + 5), value, upper)


def _apply_feedback(
    reward: int,
    penalty: int,
    feedback_history: list[dict[str, Any]],
    bounds: dict[str, Any],
) -> tuple[int, int, list[str]]:
    if not feedback_history:
        return max(5, reward), max(0, penalty), []

    feedback = feedback_history[-1]
    previous_quote = feedback.get("previous_quote") or {}
    reward = int(previous_quote.get("reward_primary") or reward)
    penalty = int(previous_quote.get("penalty_primary") or penalty)
    direction = _feedback_direction(feedback)
    notes = []

    reward_bounds = bounds["reward_primary"]
    penalty_bounds = bounds["penalty_primary"]
    if direction == "too_high":
        reward = _step_down(reward, reward_bounds["min"], 0.85)
        penalty = _step_down(penalty, penalty_bounds["min"], 0.85)
        notes.append("已根据本轮反馈下调奖励与惩罚。")
    elif direction == "too_low":
        reward = _step_up(reward, reward_bounds["max"], 1.15)
        penalty = _step_up(penalty, penalty_bounds["max"], 1.1)
        notes.append("已根据本轮反馈上调奖励与惩罚。")
    else:
        notes.append("已记录详细反馈，本轮保持数值不变。")

    clamped_reward = _clamp(reward, reward_bounds["min"], reward_bounds["max"])
    clamped_penalty = _clamp(penalty, penalty_bounds["min"], penalty_bounds["max"])
    if clamped_reward != reward or clamped_penalty != penalty:
        notes.append("本轮结果已限制在建议定价范围内。")
    if clamped_reward in {reward_bounds["min"], reward_bounds["max"]}:
        notes.append("奖励已到达当前任务建议范围边界。")
    if clamped_penalty in {penalty_bounds["min"], penalty_bounds["max"]}:
        notes.append("惩罚已到达当前任务建议范围边界。")
    return clamped_reward, clamped_penalty, notes


def _task_type_label(value: str) -> str:
    return dict(TaskType.choices).get(value, value)


def _recurrence_label(value: str) -> str:
    return dict(RecurrenceType.choices).get(value, value)


def _difficulty_label(value: str) -> str:
    return dict(DifficultyLevel.choices).get(value, value)


def _build_reasoning(
    *,
    task_payload: dict[str, Any],
    reward: int,
    penalty: int,
    bounds: dict[str, Any],
    feedback_history: list[dict[str, Any]],
) -> str:
    task_type = task_payload.get("task_type") or TaskType.ONE_TIME
    recurrence = task_payload.get("recurrence") or RecurrenceType.NONE
    difficulty = _difficulty(task_payload)
    settlement_track = task_payload.get("settlement_track") or SettlementTrack.REGULAR
    parts = [
        f"该任务按{_task_type_label(task_type)}、{_recurrence_label(recurrence)}、{_difficulty_label(difficulty)}难度估算。",
    ]

    if settlement_track == SettlementTrack.EXPLORATION:
        minutes = int(task_payload.get("estimated_focus_minutes") or 60)
        parts.append(f"探索轨道按约 {minutes} 分钟专注投入折算，惩罚保持偏轻。")
    elif task_type == TaskType.ONE_TIME:
        parts.append("一次性任务以满额完成作为奖励基准，适合配合进度结算。")
    elif task_type == TaskType.RECURRING:
        parts.append("周期任务以周期完成率作为结算基准，奖励不按单次无限放大。")
    else:
        parts.append("日常任务按小习惯定价，控制单日产币速度。")

    if feedback_history:
        direction = _feedback_direction(feedback_history[-1])
        if direction == "too_high":
            parts.append("本轮收到“偏高”反馈，因此在上一轮报价基础上下调。")
        elif direction == "too_low":
            parts.append("本轮收到“偏低”反馈，因此在上一轮报价基础上上调。")
        else:
            parts.append("本轮收到详细反馈，暂不改变数值但保留给后续模型参考。")

    parts.append(
        "当前建议范围为奖励 "
        f"{bounds['reward_primary']['min']}-{bounds['reward_primary']['max']}，"
        f"惩罚 {bounds['penalty_primary']['min']}-{bounds['penalty_primary']['max']}；"
        f"本次建议奖励 {reward}、惩罚 {penalty}。"
    )
    return "".join(parts)


def _clamp_quote_to_bounds(quote: dict[str, Any]) -> dict[str, Any]:
    bounds = quote["pricing_bounds"]
    quote["reward_primary"] = _clamp(
        int(quote["reward_primary"]),
        bounds["reward_primary"]["min"],
        bounds["reward_primary"]["max"],
    )
    quote["penalty_primary"] = _clamp(
        int(quote["penalty_primary"]),
        bounds["penalty_primary"]["min"],
        bounds["penalty_primary"]["max"],
    )
    return quote


def _try_llm_refine_quote(state: TaskPricingState, baseline_quote: dict[str, Any]) -> dict[str, Any]:
    if os.getenv("AI_PROVIDER", "mock") not in {"openai-compatible", "openai"}:
        return baseline_quote
    if ChatOpenAI is None or not os.getenv("AI_API_KEY"):
        return baseline_quote

    llm = ChatOpenAI(
        model=os.getenv("AI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("AI_API_KEY"),
        base_url=os.getenv("AI_BASE_URL") or None,
        temperature=float(os.getenv("AI_TEMPERATURE", "0.2")),
        timeout=int(os.getenv("AI_TIMEOUT", "60")),
        max_retries=int(os.getenv("AI_MAX_RETRIES", "2")),
    )
    prompt = f"""
你是 MotiWish 的任务定价助手。请基于全局定价标准、用户画像、任务草稿、用户反馈和本地规则基线，输出更合适的任务定价 JSON。

全局定价标准：
{state.get("pricing_standard", "")}

用户画像：
{json.dumps(state.get("profile_snapshot", {}), ensure_ascii=False)}

任务草稿：
{json.dumps(state.get("task_payload", {}), ensure_ascii=False)}

用户反馈历史：
{json.dumps(state.get("feedback_history", []), ensure_ascii=False)}

本地规则基线：
{json.dumps(baseline_quote, ensure_ascii=False)}

只输出 JSON，字段必须包含：
reward_primary, penalty_primary, price_tier, confidence, reasoning, risk_notes, user_fit_notes, pricing_bounds
"""
    try:
        response = llm.invoke(prompt)
        parsed = json.loads(response.content)
        reward = round_5(float(parsed.get("reward_primary", baseline_quote["reward_primary"])))
        penalty = round_5(float(parsed.get("penalty_primary", baseline_quote["penalty_primary"])))
        quote = {
            **baseline_quote,
            **parsed,
            "reward_primary": reward,
            "penalty_primary": penalty,
            "pricing_bounds": baseline_quote["pricing_bounds"],
            "llm_style_payload": {
                **baseline_quote.get("llm_style_payload", {}),
                "provider": "openai-compatible",
            },
        }
        return _clamp_quote_to_bounds(quote)
    except Exception as exc:  # Keep local dev and pricing flow robust.
        return {
            **baseline_quote,
            "risk_notes": [
                *baseline_quote.get("risk_notes", []),
                f"真实 LLM 定价失败，已回退本地规则：{str(exc)[:80]}",
            ],
        }


def draft_pricing_quote(state: TaskPricingState) -> dict[str, Any]:
    task_payload = state["task_payload"]
    profile = state.get("profile_snapshot", {})
    feedback_history = state.get("feedback_history", [])

    reward = _base_reward(task_payload)
    penalty = _base_penalty(task_payload, reward)
    reward, penalty, user_fit_notes = _apply_profile_adjustment(reward, penalty, profile)
    bounds = _pricing_bounds(task_payload, reward, penalty)
    reward, penalty, feedback_notes = _apply_feedback(reward, penalty, feedback_history, bounds)
    bounds["reward_primary"]["recommended"] = reward
    bounds["penalty_primary"]["recommended"] = penalty

    task_type = task_payload.get("task_type") or TaskType.ONE_TIME
    settlement_track = task_payload.get("settlement_track") or SettlementTrack.REGULAR
    missing = []
    if not task_payload.get("title"):
        missing.append("title")
    if settlement_track == SettlementTrack.EXPLORATION and not task_payload.get("estimated_focus_minutes"):
        missing.append("estimated_focus_minutes")

    quote = {
        "reward_primary": reward,
        "penalty_primary": penalty,
        "price_tier": "medium" if reward >= 100 else "small",
        "confidence": 0.72 if missing else 0.86,
        "reasoning": _build_reasoning(
            task_payload=task_payload,
            reward=reward,
            penalty=penalty,
            bounds=bounds,
            feedback_history=feedback_history,
        ),
        "risk_notes": [f"缺少字段：{', '.join(missing)}"] if missing else [],
        "user_fit_notes": [*user_fit_notes, *feedback_notes],
        "pricing_bounds": bounds,
        "llm_style_payload": {
            "task_type": task_type,
            "settlement_track": settlement_track,
            "feedback_rounds": len(feedback_history),
        },
    }
    quote = _try_llm_refine_quote(state, quote)
    return {"quote_payload": quote}


def build_task_pricing_graph():
    builder = StateGraph(TaskPricingState)
    builder.add_node("load_profile", load_profile)
    builder.add_node("load_pricing_standard", load_pricing_standard)
    builder.add_node("draft_pricing_quote", draft_pricing_quote)
    builder.add_edge(START, "load_profile")
    builder.add_edge("load_profile", "load_pricing_standard")
    builder.add_edge("load_pricing_standard", "draft_pricing_quote")
    builder.add_edge("draft_pricing_quote", END)
    return builder.compile()
