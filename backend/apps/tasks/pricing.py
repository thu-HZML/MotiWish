from dataclasses import dataclass

from apps.tasks.models import DifficultyLevel, SettlementTrack, TaskType


REGULAR_FORMULAS = {
    TaskType.ONE_TIME: "Reward = round_5(R * F_progress(p) * F_time)",
    TaskType.RECURRING: "RecurringReward = round_5(B * F_cycle(r) * S)",
    TaskType.DAILY: "RecurringReward = round_5(B * F_cycle(r) * S)",
}

EXPLORATION_FORMULA = "ExplorationReward = round_5(T_focus * K_difficulty)"

DIFFICULTY_FACTORS = {
    DifficultyLevel.LOW: 15,
    DifficultyLevel.MEDIUM: 25,
    DifficultyLevel.HIGH: 40,
}


@dataclass
class PricingContext:
    settlement_track: str
    task_type: str
    formula: str
    normalized_payload: dict


def build_pricing_context(*, task_data: dict) -> PricingContext:
    settlement_track = task_data.get("settlement_track", SettlementTrack.REGULAR)
    task_type = task_data.get("task_type", TaskType.ONE_TIME)

    if settlement_track == SettlementTrack.EXPLORATION:
        formula = EXPLORATION_FORMULA
        normalized_payload = {
            "settlement_track": settlement_track,
            "task_type": task_type,
            "difficulty_level": task_data.get("difficulty_level", DifficultyLevel.MEDIUM),
            "estimated_focus_minutes": task_data.get("estimated_focus_minutes"),
            "difficulty_factor_hint": DIFFICULTY_FACTORS.get(
                task_data.get("difficulty_level", DifficultyLevel.MEDIUM),
                DIFFICULTY_FACTORS[DifficultyLevel.MEDIUM],
            ),
            "tags": task_data.get("tags", []),
        }
    else:
        formula = REGULAR_FORMULAS.get(task_type, REGULAR_FORMULAS[TaskType.ONE_TIME])
        normalized_payload = {
            "settlement_track": settlement_track,
            "task_type": task_type,
            "recurrence": task_data.get("recurrence"),
            "progress_target": task_data.get("progress_target"),
            "metric_key": task_data.get("metric_key"),
            "target_value": task_data.get("target_value"),
            "weekdays": task_data.get("weekdays", []),
            "month_days": task_data.get("month_days", []),
            "tags": task_data.get("tags", []),
        }

    return PricingContext(
        settlement_track=settlement_track,
        task_type=task_type,
        formula=formula,
        normalized_payload=normalized_payload,
    )
