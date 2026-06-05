import calendar
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.tasks.models import DifficultyLevel, RecurrenceType, SettlementTrack, TaskType


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

DIFFICULTY_ORDER = (DifficultyLevel.LOW, DifficultyLevel.MEDIUM, DifficultyLevel.HIGH)

DAILY_REWARD_BASES = {
    DifficultyLevel.LOW: 15,
    DifficultyLevel.MEDIUM: 30,
    DifficultyLevel.HIGH: 55,
}

RECURRING_DAILY_REWARD_BASES = {
    DifficultyLevel.LOW: 20,
    DifficultyLevel.MEDIUM: 30,
    DifficultyLevel.HIGH: 40,
}

RECURRING_WEEKLY_REWARD_BASES = {
    DifficultyLevel.LOW: 60,
    DifficultyLevel.MEDIUM: 100,
    DifficultyLevel.HIGH: 150,
}

RECURRING_MONTHLY_REWARD_BASES = {
    DifficultyLevel.LOW: 200,
    DifficultyLevel.MEDIUM: 300,
    DifficultyLevel.HIGH: 500,
}

ONE_TIME_REWARD_BASES = {
    DifficultyLevel.LOW: 60,
    DifficultyLevel.MEDIUM: 160,
    DifficultyLevel.HIGH: 350,
}

ONE_TIME_PENALTY_BASES = {
    DifficultyLevel.LOW: 10,
    DifficultyLevel.MEDIUM: 30,
    DifficultyLevel.HIGH: 70,
}

RECURRING_PENALTY_BASES = {
    RecurrenceType.DAILY: {
        DifficultyLevel.LOW: 5,
        DifficultyLevel.MEDIUM: 10,
        DifficultyLevel.HIGH: 10,
    },
    RecurrenceType.WEEKLY: {
        DifficultyLevel.LOW: 10,
        DifficultyLevel.MEDIUM: 20,
        DifficultyLevel.HIGH: 30,
    },
    RecurrenceType.MONTHLY: {
        DifficultyLevel.LOW: 30,
        DifficultyLevel.MEDIUM: 45,
        DifficultyLevel.HIGH: 60,
    },
}

DAILY_STREAK_BONUSES = {7: 20, 14: 50, 30: 100}

TASK_SIZE_SMALL = "small"
TASK_SIZE_MEDIUM = "medium"
TASK_SIZE_LARGE = "large"
TASK_SIZE_BY_DIFFICULTY = {
    DifficultyLevel.LOW: TASK_SIZE_SMALL,
    DifficultyLevel.MEDIUM: TASK_SIZE_MEDIUM,
    DifficultyLevel.HIGH: TASK_SIZE_LARGE,
}


@dataclass
class PricingContext:
    settlement_track: str
    task_type: str
    formula: str
    normalized_payload: dict


@dataclass
class SettlementQuote:
    reward_primary: int
    penalty_primary: int
    details: dict


def round_5(value: float) -> int:
    return int(round(value / 5) * 5)


def clamp_ratio(value: float) -> float:
    return min(max(value, 0), 1)


def estimate_difficulty_level(task_data: dict) -> str:
    explicit = task_data.get("difficulty_level")
    if explicit in DifficultyLevel.values and not task_data.get("auto_estimate_difficulty"):
        return explicit

    score = 1
    minutes = int(task_data.get("estimated_focus_minutes") or 0)
    if minutes >= 180:
        score += 2
    elif minutes >= 60:
        score += 1

    progress_target = int(task_data.get("progress_target") or 100)
    if progress_target >= 300:
        score += 1

    task_type = task_data.get("task_type") or TaskType.ONE_TIME
    recurrence = task_data.get("recurrence") or RecurrenceType.NONE
    if task_type == TaskType.RECURRING and recurrence == RecurrenceType.MONTHLY:
        score += 1

    text = " ".join(
        str(part).lower()
        for part in [
            task_data.get("title", ""),
            task_data.get("description", ""),
            " ".join(task_data.get("tags", []) or []),
        ]
    )
    high_keywords = ("科研", "研究", "论文", "debug", "调试", "项目", "系统", "深度", "复杂", "考试")
    low_keywords = ("起床", "喝水", "打卡", "整理", "散步", "轻量", "简单")
    if any(keyword in text for keyword in high_keywords):
        score += 1
    if any(keyword in text for keyword in low_keywords):
        score -= 1

    if score <= 0:
        return DifficultyLevel.LOW
    if score >= 3:
        return DifficultyLevel.HIGH
    return DifficultyLevel.MEDIUM


def estimate_task_size(task_data: dict) -> str:
    difficulty = estimate_difficulty_level(task_data)
    return TASK_SIZE_BY_DIFFICULTY.get(difficulty, TASK_SIZE_MEDIUM)


def get_base_reward(task) -> int:
    difficulty = task.difficulty_level or DifficultyLevel.MEDIUM
    if task.settlement_track == SettlementTrack.EXPLORATION:
        minutes = task.estimated_focus_minutes or 60
        return round_5(minutes / 60 * DIFFICULTY_FACTORS.get(difficulty, 25))
    if task.task_type == TaskType.DAILY:
        return DAILY_REWARD_BASES.get(difficulty, DAILY_REWARD_BASES[DifficultyLevel.MEDIUM])
    if task.task_type == TaskType.RECURRING:
        if task.recurrence == RecurrenceType.MONTHLY:
            return RECURRING_MONTHLY_REWARD_BASES.get(difficulty, RECURRING_MONTHLY_REWARD_BASES[DifficultyLevel.MEDIUM])
        if task.recurrence == RecurrenceType.DAILY:
            return RECURRING_DAILY_REWARD_BASES.get(difficulty, RECURRING_DAILY_REWARD_BASES[DifficultyLevel.MEDIUM])
        return RECURRING_WEEKLY_REWARD_BASES.get(difficulty, RECURRING_WEEKLY_REWARD_BASES[DifficultyLevel.MEDIUM])
    return ONE_TIME_REWARD_BASES.get(difficulty, ONE_TIME_REWARD_BASES[DifficultyLevel.MEDIUM])


def get_base_penalty(task) -> int:
    difficulty = task.difficulty_level or DifficultyLevel.MEDIUM
    if task.settlement_track == SettlementTrack.EXPLORATION:
        return max(5, round_5(get_base_reward(task) * 0.12))
    if task.task_type == TaskType.RECURRING:
        recurrence = task.recurrence if task.recurrence in RECURRING_PENALTY_BASES else RecurrenceType.WEEKLY
        return RECURRING_PENALTY_BASES[recurrence].get(difficulty, RECURRING_PENALTY_BASES[recurrence][DifficultyLevel.MEDIUM])
    if task.task_type == TaskType.DAILY:
        return RECURRING_PENALTY_BASES[RecurrenceType.DAILY].get(difficulty, 10)
    return ONE_TIME_PENALTY_BASES.get(difficulty, ONE_TIME_PENALTY_BASES[DifficultyLevel.MEDIUM])


def progress_factor(progress_ratio: float) -> float:
    p = clamp_ratio(progress_ratio)
    if p < 0.3:
        return 0.5 * p
    if p < 0.8:
        return 0.15 + 0.9 * (p - 0.3)
    return 0.60 + 2.0 * (p - 0.8)


def cycle_factor(completion_ratio: float) -> float:
    r = clamp_ratio(completion_ratio)
    if r < 0.5:
        return 0.8 * r
    if r < 0.8:
        return 0.40 + 1.0 * (r - 0.5)
    return 0.70 + 1.5 * (r - 0.8)


def streak_multiplier(streak_count: int) -> float:
    if streak_count >= 30:
        return 1.20
    if streak_count >= 14:
        return 1.15
    if streak_count >= 7:
        return 1.10
    if streak_count >= 3:
        return 1.05
    return 1.00


def time_factor(task, settled_at=None) -> float:
    if not task.due_at:
        return 1.0
    settled_at = settled_at or timezone.now()
    if settled_at <= task.due_at:
        return 1.0
    if settled_at <= task.due_at + timedelta(hours=24):
        return 0.8
    return 0.6


def overdue_penalty(task, progress_ratio: float, settled_at=None) -> int:
    if not task.due_at:
        return 0
    settled_at = settled_at or timezone.now()
    if settled_at <= task.due_at:
        return 0
    penalty_base = task.penalty_primary or get_base_penalty(task)
    return round_5(penalty_base * ((1 - clamp_ratio(progress_ratio)) ** 1.2))


def recurring_penalty(task, completion_ratio: float) -> int:
    penalty_base = task.penalty_primary or get_base_penalty(task)
    return round_5(penalty_base * ((1 - clamp_ratio(completion_ratio)) ** 1.1))


def period_bounds(target_date, recurrence: str):
    if recurrence == RecurrenceType.MONTHLY:
        last_day = calendar.monthrange(target_date.year, target_date.month)[1]
        return target_date.replace(day=1), target_date.replace(day=last_day)
    if recurrence == RecurrenceType.WEEKLY:
        start = target_date - timedelta(days=target_date.weekday())
        return start, start + timedelta(days=6)
    return target_date, target_date


def expected_dates_in_period(task, target_date):
    start, end = period_bounds(target_date, task.recurrence)
    if task.starts_on and start < task.starts_on:
        start = task.starts_on
    if task.ends_on and end > task.ends_on:
        end = task.ends_on

    dates = []
    current = start
    while current <= end:
        if task.recurrence == RecurrenceType.WEEKLY:
            if current.weekday() in (task.weekdays or []):
                dates.append(current)
        elif task.recurrence == RecurrenceType.MONTHLY:
            if current.day in (task.month_days or []):
                dates.append(current)
        else:
            dates.append(current)
        current += timedelta(days=1)
    return dates or [target_date]


def pricing_bounds_for_task_data(task_data: dict) -> dict:
    difficulty = estimate_difficulty_level(task_data)
    size_level = TASK_SIZE_BY_DIFFICULTY.get(difficulty, TASK_SIZE_MEDIUM)
    task_type = task_data.get("task_type") or TaskType.ONE_TIME
    recurrence = task_data.get("recurrence") or RecurrenceType.NONE
    settlement_track = task_data.get("settlement_track") or SettlementTrack.REGULAR

    if settlement_track == SettlementTrack.EXPLORATION:
        minutes = int(task_data.get("estimated_focus_minutes") or 60)
        recommended_reward = round_5(minutes / 60 * DIFFICULTY_FACTORS.get(difficulty, 25))
        return {
            "difficulty_level": difficulty,
            "size_level": size_level,
            "reward_primary": {
                "min": max(5, round_5(recommended_reward * 0.5)),
                "max": max(10, round_5(recommended_reward * 2.2)),
                "recommended": recommended_reward,
            },
            "penalty_primary": {
                "min": 0,
                "max": max(5, round_5(recommended_reward * 0.2)),
                "recommended": max(5, round_5(recommended_reward * 0.12)),
            },
        }

    if task_type == TaskType.DAILY:
        ranges = {
            DifficultyLevel.LOW: (10, 20, 15, 0, 10, 5),
            DifficultyLevel.MEDIUM: (20, 40, 30, 5, 15, 10),
            DifficultyLevel.HIGH: (50, 60, 55, 10, 25, 15),
        }
    elif task_type == TaskType.RECURRING and recurrence == RecurrenceType.MONTHLY:
        ranges = {
            DifficultyLevel.LOW: (200, 250, 200, 30, 60, 30),
            DifficultyLevel.MEDIUM: (250, 400, 300, 30, 60, 45),
            DifficultyLevel.HIGH: (400, 500, 500, 30, 60, 60),
        }
    elif task_type == TaskType.RECURRING and recurrence == RecurrenceType.DAILY:
        ranges = {
            DifficultyLevel.LOW: (20, 25, 20, 5, 10, 5),
            DifficultyLevel.MEDIUM: (25, 35, 30, 5, 10, 10),
            DifficultyLevel.HIGH: (35, 40, 40, 5, 10, 10),
        }
    elif task_type == TaskType.RECURRING:
        ranges = {
            DifficultyLevel.LOW: (60, 80, 60, 10, 30, 10),
            DifficultyLevel.MEDIUM: (80, 120, 100, 10, 30, 20),
            DifficultyLevel.HIGH: (120, 150, 150, 10, 30, 30),
        }
    else:
        ranges = {
            DifficultyLevel.LOW: (30, 80, 60, 5, 15, 10),
            DifficultyLevel.MEDIUM: (100, 250, 160, 20, 40, 30),
            DifficultyLevel.HIGH: (300, 800, 350, 50, 100, 70),
        }

    reward_min, reward_max, reward, penalty_min, penalty_max, penalty = ranges.get(difficulty, ranges[DifficultyLevel.MEDIUM])
    return {
        "difficulty_level": difficulty,
        "size_level": size_level,
        "reward_primary": {"min": reward_min, "max": reward_max, "recommended": reward},
        "penalty_primary": {"min": penalty_min, "max": penalty_max, "recommended": penalty},
    }


def clamp_pricing_to_bounds(*, task, reward_primary: int, penalty_primary: int) -> tuple[int, int, dict]:
    bounds = pricing_bounds_for_task_data(
        {
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "recurrence": task.recurrence,
            "settlement_track": task.settlement_track,
            "difficulty_level": task.difficulty_level,
            "estimated_focus_minutes": task.estimated_focus_minutes,
            "progress_target": task.progress_target,
            "tags": task.tags,
        }
    )
    reward_bounds = bounds["reward_primary"]
    penalty_bounds = bounds["penalty_primary"]
    reward = min(max(round_5(reward_primary), reward_bounds["min"]), reward_bounds["max"])
    penalty = min(max(round_5(penalty_primary), penalty_bounds["min"]), penalty_bounds["max"])
    return reward, penalty, bounds


def build_pricing_context(*, task_data: dict) -> PricingContext:
    settlement_track = task_data.get("settlement_track", SettlementTrack.REGULAR)
    task_type = task_data.get("task_type", TaskType.ONE_TIME)
    difficulty_level = estimate_difficulty_level(task_data)
    pricing_bounds = pricing_bounds_for_task_data({**task_data, "difficulty_level": difficulty_level})

    if settlement_track == SettlementTrack.EXPLORATION:
        formula = EXPLORATION_FORMULA
        normalized_payload = {
            "settlement_track": settlement_track,
            "task_type": task_type,
            "difficulty_level": difficulty_level,
            "size_level": estimate_task_size({**task_data, "difficulty_level": difficulty_level}),
            "estimated_focus_minutes": task_data.get("estimated_focus_minutes"),
            "difficulty_factor_hint": DIFFICULTY_FACTORS.get(
                difficulty_level,
                DIFFICULTY_FACTORS[DifficultyLevel.MEDIUM],
            ),
            "pricing_bounds": pricing_bounds,
            "tags": task_data.get("tags", []),
        }
    else:
        formula = REGULAR_FORMULAS.get(task_type, REGULAR_FORMULAS[TaskType.ONE_TIME])
        normalized_payload = {
            "settlement_track": settlement_track,
            "task_type": task_type,
            "difficulty_level": difficulty_level,
            "size_level": estimate_task_size({**task_data, "difficulty_level": difficulty_level}),
            "recurrence": task_data.get("recurrence"),
            "progress_target": task_data.get("progress_target"),
            "metric_key": task_data.get("metric_key"),
            "target_value": task_data.get("target_value"),
            "weekdays": task_data.get("weekdays", []),
            "month_days": task_data.get("month_days", []),
            "pricing_bounds": pricing_bounds,
            "tags": task_data.get("tags", []),
        }

    return PricingContext(
        settlement_track=settlement_track,
        task_type=task_type,
        formula=formula,
        normalized_payload=normalized_payload,
    )


