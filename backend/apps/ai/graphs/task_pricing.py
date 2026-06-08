import json
import os
from pathlib import Path
from typing import Any

from django.conf import settings
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from apps.tasks.models import RecurrenceType, SettlementTrack, TaskType
from apps.tasks.pricing import estimate_difficulty_level, estimate_task_size, pricing_bounds_for_task_data
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
    return estimate_difficulty_level(task_payload)


def _task_size(task_payload: dict[str, Any]) -> str:
    return estimate_task_size({**task_payload, "difficulty_level": _difficulty(task_payload)})


def _pricing_rule_bounds(task_payload: dict[str, Any]) -> dict[str, Any]:
    return pricing_bounds_for_task_data({**task_payload, "difficulty_level": _difficulty(task_payload)})


def _base_reward(task_payload: dict[str, Any]) -> int:
    return int(_pricing_rule_bounds(task_payload)["reward_primary"]["recommended"])


def _base_penalty(task_payload: dict[str, Any], reward: int) -> int:
    return int(_pricing_rule_bounds(task_payload)["penalty_primary"]["recommended"])


def _pricing_bounds(task_payload: dict[str, Any], reward: int, penalty: int) -> dict[str, Any]:
    bounds = _pricing_rule_bounds(task_payload)
    return {
        "reward_primary": {**bounds["reward_primary"], "recommended": reward},
        "penalty_primary": {**bounds["penalty_primary"], "recommended": penalty},
        "difficulty_level": bounds["difficulty_level"],
        "task_size": bounds.get("size_level", _task_size(task_payload)),
    }


def _apply_profile_adjustment(reward: int, penalty: int, profile: dict[str, Any]) -> tuple[int, int, list[str]]:
    notes = []
    if profile.get("dynamic_profile_available"):
        notes.append("Dynamic profile available: reduced penalty pressure by 10%.")
        penalty = round_5(penalty * 0.9)
    if profile.get("stable_profile_completed"):
        notes.append("Stable profile is complete: confidence is higher.")
    return max(5, reward), max(0, penalty), notes


def _feedback_direction(feedback: dict[str, Any]) -> str:
    direction = feedback.get("feedback_direction")
    text = (feedback.get("feedback_text") or "").lower()
    if direction == "too_high" or "too high" in text or "expensive" in text:
        return "too_high"
    if direction == "too_low" or "too low" in text or "cheap" in text:
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
        notes.append("Adjusted downward from previous quote.")
    elif direction == "too_low":
        reward = _step_up(reward, reward_bounds["max"], 1.15)
        penalty = _step_up(penalty, penalty_bounds["max"], 1.1)
        notes.append("Adjusted upward from previous quote.")
    else:
        notes.append("Kept quote close to previous round and clarified the rationale.")

    clamped_reward = _clamp(reward, reward_bounds["min"], reward_bounds["max"])
    clamped_penalty = _clamp(penalty, penalty_bounds["min"], penalty_bounds["max"])
    if clamped_reward != reward or clamped_penalty != penalty:
        notes.append("Clamped to the documented pricing range.")
    if clamped_reward in {reward_bounds["min"], reward_bounds["max"]}:
        notes.append("Reward is touching a documented boundary.")
    if clamped_penalty in {penalty_bounds["min"], penalty_bounds["max"]}:
        notes.append("Penalty is touching a documented boundary.")
    return clamped_reward, clamped_penalty, notes


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
    settlement_track = task_payload.get("settlement_track") or SettlementTrack.REGULAR
    difficulty = _difficulty(task_payload)
    task_size = bounds.get("task_size", _task_size(task_payload))
    parts = [
        f"Classified as {task_size} task with {difficulty} difficulty before pricing. ",
        f"Pricing mode: {task_type}/{recurrence}. ",
    ]

    if settlement_track == SettlementTrack.EXPLORATION:
        minutes = int(task_payload.get("estimated_focus_minutes") or 60)
        parts.append(f"Exploration task uses focus minutes ({minutes}) and exploration cap rules. ")
    elif task_type == TaskType.ONE_TIME:
        parts.append("One-time task uses the documented size range. ")
    elif task_type == TaskType.RECURRING:
        parts.append("Recurring task uses cycle range and settlement loop rules. ")
    else:
        parts.append("Daily task uses daily behavior-building range. ")

    if feedback_history:
        direction = _feedback_direction(feedback_history[-1])
        if direction == "too_high":
            parts.append("Adjusted downward from previous quote after feedback. ")
        elif direction == "too_low":
            parts.append("Adjusted upward from previous quote after feedback. ")
        else:
            parts.append("Feedback was recorded without changing the pricing direction. ")

    parts.append(
        "Recommended reward "
        f"{reward} within {bounds['reward_primary']['min']}-{bounds['reward_primary']['max']}; "
        f"recommended penalty {penalty} within {bounds['penalty_primary']['min']}-{bounds['penalty_primary']['max']}."
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
You are the MotiWish task pricing assistant. Classify task size first, respect the documented baseline range, then return JSON only.

Pricing standard:
{state.get("pricing_standard", "")}

User profile:
{json.dumps(state.get("profile_snapshot", {}), ensure_ascii=False)}

Task payload:
{json.dumps(state.get("task_payload", {}), ensure_ascii=False)}

Feedback history:
{json.dumps(state.get("feedback_history", []), ensure_ascii=False)}

Baseline quote and hard bounds:
{json.dumps(baseline_quote, ensure_ascii=False)}

Return JSON with keys: reward_primary, penalty_primary, price_tier, confidence, reasoning, risk_notes, user_fit_notes, pricing_bounds.
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
                f"LLM refine failed, used local baseline: {str(exc)[:80]}",
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
        "price_tier": bounds.get("task_size", "medium"),
        "confidence": 0.72 if missing else 0.86,
        "reasoning": _build_reasoning(
            task_payload=task_payload,
            reward=reward,
            penalty=penalty,
            bounds=bounds,
            feedback_history=feedback_history,
        ),
        "risk_notes": [f"Missing fields: {', '.join(missing)}"] if missing else [],
        "user_fit_notes": [*user_fit_notes, *feedback_notes],
        "pricing_bounds": bounds,
        "llm_style_payload": {
            "task_type": task_type,
            "settlement_track": settlement_track,
            "difficulty_level": _difficulty(task_payload),
            "task_size": bounds.get("task_size", _task_size(task_payload)),
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
