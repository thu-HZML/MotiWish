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


def _apply_profile_adjustment(reward: int, penalty: int, profile: dict[str, Any]) -> tuple[int, int, list[str]]:
    notes = []
    dynamic_available = profile.get("dynamic_profile_available")
    if dynamic_available:
        notes.append("检测到用户已有动态画像，建议保持惩罚温和，避免在压力波动期放大挫败。")
        penalty = round_5(penalty * 0.9)
    if profile.get("stable_profile_completed"):
        notes.append("用户稳定画像较完整，定价可信度略高。")
    return max(5, reward), max(0, penalty), notes


def _apply_feedback(reward: int, penalty: int, feedback_history: list[dict[str, Any]]) -> tuple[int, int]:
    for feedback in feedback_history or []:
        direction = feedback.get("feedback_direction")
        text = (feedback.get("feedback_text") or "").lower()
        if direction == "too_high" or "偏高" in text or "太高" in text:
            reward = round_5(reward * 0.85)
            penalty = round_5(penalty * 0.85)
        elif direction == "too_low" or "偏低" in text or "太低" in text:
            reward = round_5(reward * 1.15)
            penalty = round_5(penalty * 1.1)
    return max(5, reward), max(0, penalty)


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
reward_primary, penalty_primary, price_tier, confidence, reasoning, risk_notes, user_fit_notes
"""
    try:
        response = llm.invoke(prompt)
        parsed = json.loads(response.content)
        reward = round_5(float(parsed.get("reward_primary", baseline_quote["reward_primary"])))
        penalty = round_5(float(parsed.get("penalty_primary", baseline_quote["penalty_primary"])))
        return {
            **baseline_quote,
            **parsed,
            "reward_primary": max(5, reward),
            "penalty_primary": max(0, penalty),
            "llm_style_payload": {
                **baseline_quote.get("llm_style_payload", {}),
                "provider": "openai-compatible",
            },
        }
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
    reward, penalty = _apply_feedback(reward, penalty, feedback_history)

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
        "reasoning": (
            "已依据全局任务定价标准、任务类型、重复规则、难度和用户画像生成初步报价。"
            "一次性任务会把该值作为满额完成基准，周期任务会作为周期完成率结算基准。"
        ),
        "risk_notes": [f"缺少字段：{', '.join(missing)}"] if missing else [],
        "user_fit_notes": user_fit_notes,
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
