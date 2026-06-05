from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.tasks.models import (
    OccurrenceStatus,
    PricingStatus,
    RecurrenceType,
    SettlementTrack,
    Task,
    TaskOccurrence,
    TaskType,
)
from apps.tasks.pricing import (
    DAILY_STREAK_BONUSES,
    build_pricing_context,
    clamp_pricing_to_bounds,
    clamp_ratio,
    cycle_factor,
    expected_dates_in_period,
    get_base_penalty,
    get_base_reward,
    overdue_penalty,
    recurring_penalty,
    progress_factor,
    round_5,
    streak_multiplier,
    time_factor,
)
from apps.wallet.models import CurrencyType, TransactionReason, Wallet
from apps.wallet.services import change_balance


def _task_matches_date(task, target_date):
    if task.status != "active":
        return False
    if task.starts_on and target_date < task.starts_on:
        return False
    if task.ends_on and target_date > task.ends_on:
        return False
    if task.task_type == TaskType.ONE_TIME:
        available_from = task.starts_on or timezone.localdate(task.created_at)
        if target_date < available_from:
            return False
        return target_date <= task.due_at.date() if task.due_at else True
    if task.task_type == TaskType.DAILY or task.recurrence == RecurrenceType.DAILY:
        return True
    if task.recurrence == RecurrenceType.WEEKLY:
        return target_date.weekday() in task.weekdays
    if task.recurrence == RecurrenceType.MONTHLY:
        return target_date.day in task.month_days
    return False



def _task_can_settle_date(task, target_date):
    if task.status != "active":
        return False
    if task.starts_on and target_date < task.starts_on:
        return False
    if task.task_type == TaskType.ONE_TIME:
        available_from = task.starts_on or timezone.localdate(task.created_at)
        return target_date >= available_from
    return _task_matches_date(task, target_date)

def ensure_occurrences_for_date(user, target_date):
    tasks = Task.objects.filter(owner=user)
    occurrence_ids = []
    for task in tasks:
        if _task_matches_date(task, target_date):
            occurrence, _ = TaskOccurrence.objects.get_or_create(
                task=task,
                occurrence_date=target_date,
                defaults={"owner": user},
            )
            occurrence_ids.append(occurrence.id)
    return TaskOccurrence.objects.filter(id__in=occurrence_ids).select_related("task")


@transaction.atomic
def update_task_progress(*, task, progress, target_date=None):
    target_date = target_date or timezone.localdate()
    if not _task_matches_date(task, target_date):
        raise ValueError("该任务在指定日期不可用，无法更新进度")
    if progress > task.progress_target:
        raise ValueError(f"任务进度不能超过进度目标 {task.progress_target}")

    occurrence, _ = TaskOccurrence.objects.select_for_update().get_or_create(
        task=task,
        occurrence_date=target_date,
        defaults={"owner": task.owner},
    )
    if occurrence.status == OccurrenceStatus.COMPLETED:
        raise ValueError("已完成的任务实例不能修改进度")

    occurrence.progress = progress
    occurrence.save(update_fields=["progress", "updated_at"])
    return occurrence


def _progress_ratio(task, progress):
    target = task.progress_target or 100
    if task.settlement_track == SettlementTrack.EXPLORATION:
        target = task.estimated_focus_minutes or target
    return clamp_ratio(progress / target if target else 1)


def _completed_streak_before(task, target_date):
    streak = 0
    cursor = target_date - timedelta(days=1)
    while True:
        exists = TaskOccurrence.objects.filter(
            task=task,
            occurrence_date=cursor,
            status=OccurrenceStatus.COMPLETED,
        ).exists()
        if not exists:
            break
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _completed_periods_before(task, target_date):
    streak = 0
    cursor = target_date
    while True:
        if task.recurrence == RecurrenceType.MONTHLY:
            first = cursor.replace(day=1)
            cursor = first - timedelta(days=1)
        elif task.recurrence == RecurrenceType.WEEKLY:
            cursor = cursor - timedelta(days=cursor.weekday() + 1)
        else:
            cursor = cursor - timedelta(days=1)

        dates = expected_dates_in_period(task, cursor)
        if not dates:
            break
        completed = TaskOccurrence.objects.filter(
            task=task,
            occurrence_date__in=dates,
            status=OccurrenceStatus.COMPLETED,
        ).count()
        if completed < len(dates):
            break
        streak += 1
    return streak


def _period_reward_already_paid(task, expected_dates, occurrence):
    queryset = TaskOccurrence.objects.filter(
        task=task,
        occurrence_date__in=expected_dates,
        reward_transaction__isnull=False,
    ).exclude(pk=occurrence.pk)
    return queryset.aggregate(total=Sum("reward_transaction__delta"))["total"] or 0


def _quote_exploration(task, progress):
    focus_minutes = progress if progress is not None else task.estimated_focus_minutes or 0
    difficulty_factor = {"low": 15, "medium": 25, "high": 40}.get(task.difficulty_level, 25)
    reward = round_5((focus_minutes / 60) * difficulty_factor)
    ratio = _progress_ratio(task, focus_minutes)
    penalty = overdue_penalty(task, ratio)
    return reward, penalty, {
        "settlement_track": SettlementTrack.EXPLORATION,
        "formula": "ExplorationReward = round_5(T_focus * K_difficulty)",
        "focus_minutes": focus_minutes,
        "difficulty_factor": difficulty_factor,
        "progress_ratio": ratio,
    }


def _quote_one_time(task, progress, now):
    ratio = _progress_ratio(task, progress)
    reward_base = task.reward_primary or get_base_reward(task)
    factor_progress = progress_factor(ratio)
    factor_time = time_factor(task, now)
    reward = round_5(reward_base * factor_progress * factor_time)
    penalty = overdue_penalty(task, ratio, now)
    return reward, penalty, {
        "settlement_track": SettlementTrack.REGULAR,
        "formula": "Reward = round_5(R * F_progress(p) * F_time)",
        "base_reward": reward_base,
        "progress_ratio": ratio,
        "progress_factor": factor_progress,
        "time_factor": factor_time,
    }


def _quote_daily(task, target_date):
    base_reward = task.reward_primary or get_base_reward(task)
    streak = _completed_streak_before(task, target_date) + 1
    multiplier = streak_multiplier(streak)
    streak_bonus = DAILY_STREAK_BONUSES.get(streak, 0)
    reward = round_5(base_reward * multiplier) + streak_bonus
    return reward, 0, {
        "settlement_track": SettlementTrack.REGULAR,
        "formula": "DailyReward = round_5(B * S) + streak_bonus",
        "base_reward": base_reward,
        "streak_count": streak,
        "streak_multiplier": multiplier,
        "streak_bonus": streak_bonus,
    }


def _quote_recurring(task, target_date, occurrence):
    expected_dates = expected_dates_in_period(task, target_date)
    completed_count = TaskOccurrence.objects.filter(
        task=task,
        occurrence_date__in=expected_dates,
        status=OccurrenceStatus.COMPLETED,
    ).exclude(pk=occurrence.pk).count() + 1
    expected_count = len(expected_dates)
    completion_ratio = clamp_ratio(completed_count / expected_count if expected_count else 1)
    base_reward = task.reward_primary or get_base_reward(task)
    streak = _completed_periods_before(task, target_date)
    multiplier = streak_multiplier(streak)
    desired_period_reward = round_5(base_reward * cycle_factor(completion_ratio) * multiplier)
    already_paid = _period_reward_already_paid(task, expected_dates, occurrence)
    reward_delta = max(0, desired_period_reward - already_paid)
    penalty_base = task.penalty_primary or get_base_penalty(task)
    penalty = 0
    return reward_delta, penalty, {
        "settlement_track": SettlementTrack.REGULAR,
        "formula": "RecurringReward = round_5(B * F_cycle(r) * S)",
        "base_reward": base_reward,
        "expected_count": expected_count,
        "completed_count": completed_count,
        "completion_ratio": completion_ratio,
        "cycle_factor": cycle_factor(completion_ratio),
        "streak_periods": streak,
        "streak_multiplier": multiplier,
        "desired_period_reward": desired_period_reward,
        "already_paid_in_period": already_paid,
        "penalty_base": penalty_base,
    }


def _calculate_settlement(task, occurrence, progress, now):
    if task.settlement_track == SettlementTrack.EXPLORATION:
        return _quote_exploration(task, progress)
    if task.task_type == TaskType.ONE_TIME:
        return _quote_one_time(task, progress, now)
    if task.task_type == TaskType.DAILY or task.recurrence == RecurrenceType.DAILY:
        return _quote_daily(task, occurrence.occurrence_date)
    if task.task_type == TaskType.RECURRING:
        return _quote_recurring(task, occurrence.occurrence_date, occurrence)
    return task.reward_primary or get_base_reward(task), 0, {"formula": "fixed_reward"}


def _ensure_period_occurrences(task, expected_dates):
    occurrences = []
    for expected_date in expected_dates:
        occurrence, _ = TaskOccurrence.objects.select_for_update().get_or_create(
            task=task,
            occurrence_date=expected_date,
            defaults={"owner": task.owner},
        )
        occurrences.append(occurrence)
    return occurrences


def _period_representative_occurrence(task, target_date, occurrences):
    for occurrence in occurrences:
        if occurrence.occurrence_date == target_date:
            return occurrence
    occurrence, _ = TaskOccurrence.objects.select_for_update().get_or_create(
        task=task,
        occurrence_date=target_date,
        defaults={"owner": task.owner},
    )
    return occurrence


@transaction.atomic
def settle_task_period(*, task, target_date=None):
    target_date = target_date or timezone.localdate()
    if task.task_type not in {TaskType.DAILY, TaskType.RECURRING} and task.recurrence == RecurrenceType.NONE:
        raise ValueError("只有日常任务或周期任务支持周期结算")
    if not _task_can_settle_date(task, target_date):
        raise ValueError("该任务在指定日期不可用，无法结算")

    expected_dates = expected_dates_in_period(task, target_date)
    occurrences = _ensure_period_occurrences(task, expected_dates)
    representative = _period_representative_occurrence(task, target_date, occurrences)
    completed_count = sum(1 for occurrence in occurrences if occurrence.status == OccurrenceStatus.COMPLETED)
    expected_count = len(expected_dates) or 1
    completion_ratio = completed_count / expected_count
    base_reward = task.reward_primary or get_base_reward(task)
    streak = _completed_periods_before(task, target_date)
    multiplier = streak_multiplier(streak)
    desired_period_reward = round_5(base_reward * cycle_factor(completion_ratio) * multiplier)
    already_paid = _period_reward_already_paid(task, expected_dates, representative)
    reward_delta = max(0, desired_period_reward - already_paid)
    penalty_primary = recurring_penalty(task, completion_ratio)

    now = timezone.now()
    missed_count = 0
    for occurrence in occurrences:
        if occurrence.status == OccurrenceStatus.PENDING:
            occurrence.status = OccurrenceStatus.MISSED
            occurrence.settled_at = now
            occurrence.save(update_fields=["status", "settled_at", "updated_at"])
            missed_count += 1

    details = {
        "settlement_mode": "period",
        "settlement_track": SettlementTrack.REGULAR,
        "formula": "RecurringReward = round_5(B * F_cycle(r) * S); RecurringPenalty = round_5(Q * (1 - r)^1.1)",
        "base_reward": base_reward,
        "penalty_base": task.penalty_primary or get_base_penalty(task),
        "expected_count": expected_count,
        "completed_count": completed_count,
        "missed_count": missed_count,
        "completion_ratio": completion_ratio,
        "cycle_factor": cycle_factor(completion_ratio),
        "streak_periods": streak,
        "streak_multiplier": multiplier,
        "desired_period_reward": desired_period_reward,
        "already_paid_in_period": already_paid,
        "reward_primary": reward_delta,
        "penalty_primary": penalty_primary,
    }

    if reward_delta:
        _, reward_transaction = change_balance(
            user=task.owner,
            currency_type=CurrencyType.PRIMARY,
            delta=reward_delta,
            reason=TransactionReason.TASK_REWARD,
            reference_type="task_period",
            reference_id=representative.id,
            memo=f"周期任务结算奖励：{task.title}",
            payload=details,
        )
        representative.reward_transaction = reward_transaction

    penalty_transaction, applied_penalty = _apply_penalty_with_debt_floor(
        user=task.owner,
        penalty=penalty_primary,
        occurrence=representative,
        details=details,
    )
    representative.penalty_transaction = penalty_transaction
    if applied_penalty != penalty_primary:
        details["applied_penalty_primary"] = applied_penalty
    representative.settled_at = representative.settled_at or now
    representative._settlement_details = details
    representative.save(update_fields=["reward_transaction", "penalty_transaction", "settled_at", "updated_at"])
    return representative


def _apply_penalty_with_debt_floor(*, user, penalty, occurrence, details):
    if penalty <= 0:
        return None, 0

    from apps.shop.services import check_and_apply_failure_protection

    protected, protection_type = check_and_apply_failure_protection(user=user)
    if protected:
        details["penalty_protected"] = True
        details["protection_type"] = protection_type
        details["calculated_penalty_primary"] = penalty
        return None, 0

    wallet, _ = Wallet.objects.select_for_update().get_or_create(owner=user)
    allowed_penalty = min(penalty, max(0, wallet.primary_balance - Wallet.PRIMARY_DEBT_FLOOR))
    if allowed_penalty <= 0:
        details["penalty_skipped_reason"] = "primary_debt_floor_reached"
        details["calculated_penalty_primary"] = penalty
        return None, 0
    _, penalty_transaction = change_balance(
        user=user,
        currency_type=CurrencyType.PRIMARY,
        delta=-allowed_penalty,
        reason=TransactionReason.TASK_PENALTY,
        reference_type="task_occurrence",
        reference_id=occurrence.id,
        memo=f"任务结算惩罚：{occurrence.task.title}",
        payload={**details, "calculated_penalty_primary": penalty},
    )
    return penalty_transaction, allowed_penalty


@transaction.atomic
def complete_task(*, task, target_date=None, progress=None, settle_period=False):
    if settle_period:
        return settle_task_period(task=task, target_date=target_date)

    target_date = target_date or timezone.localdate()
    if not _task_can_settle_date(task, target_date):
        raise ValueError("该任务在指定日期不可用，无法结算")

    occurrence, _ = TaskOccurrence.objects.select_for_update().get_or_create(
        task=task,
        occurrence_date=target_date,
        defaults={"owner": task.owner},
    )
    if occurrence.status == OccurrenceStatus.COMPLETED:
        return occurrence

    effective_progress = progress if progress is not None else occurrence.progress or task.progress_target
    if task.settlement_track == SettlementTrack.EXPLORATION:
        max_progress = max(task.estimated_focus_minutes or 0, effective_progress)
    else:
        max_progress = task.progress_target
    if effective_progress > max_progress:
        raise ValueError(f"任务进度不能超过进度目标 {max_progress}")

    now = timezone.now()
    occurrence.progress = effective_progress
    reward_primary, penalty_primary, details = _calculate_settlement(task, occurrence, effective_progress, now)
    details = {
        **details,
        "reward_primary": reward_primary,
        "penalty_primary": penalty_primary,
        "task_reward_primary": task.reward_primary,
        "task_penalty_primary": task.penalty_primary,
    }

    occurrence.status = OccurrenceStatus.COMPLETED
    occurrence.settled_at = now
    occurrence.save(update_fields=["progress", "status", "settled_at", "updated_at"])

    if reward_primary:
        _, reward_transaction = change_balance(
            user=task.owner,
            currency_type=CurrencyType.PRIMARY,
            delta=reward_primary,
            reason=TransactionReason.TASK_REWARD,
            reference_type="task_occurrence",
            reference_id=occurrence.id,
            memo=f"完成任务：{task.title}",
            payload=details,
        )
        occurrence.reward_transaction = reward_transaction

    penalty_transaction, applied_penalty = _apply_penalty_with_debt_floor(
        user=task.owner,
        penalty=penalty_primary,
        occurrence=occurrence,
        details=details,
    )
    occurrence.penalty_transaction = penalty_transaction
    if applied_penalty != penalty_primary:
        details["applied_penalty_primary"] = applied_penalty
    occurrence._settlement_details = details

    occurrence.save(update_fields=["reward_transaction", "penalty_transaction", "updated_at"])
    return occurrence


@transaction.atomic
def request_task_pricing(*, task):
    pricing_context = build_pricing_context(
        task_data={
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "recurrence": task.recurrence,
            "settlement_track": task.settlement_track,
            "difficulty_level": task.difficulty_level,
            "estimated_focus_minutes": task.estimated_focus_minutes,
            "progress_target": task.progress_target,
            "metric_key": task.metric_key,
            "target_value": task.target_value,
            "weekdays": task.weekdays,
            "month_days": task.month_days,
            "tags": task.tags,
        }
    )
    task.pricing_status = PricingStatus.PENDING
    task.pricing_requested_at = timezone.now()
    task.pricing_snapshot = {
        "formula": pricing_context.formula,
        "normalized_payload": pricing_context.normalized_payload,
        "requested": True,
    }
    task.save(update_fields=["pricing_status", "pricing_requested_at", "pricing_snapshot", "updated_at"])
    return task


@transaction.atomic
def apply_task_pricing(*, task, reward_primary, penalty_primary, pricing_payload):
    clamped_reward, clamped_penalty, bounds = clamp_pricing_to_bounds(
        task=task,
        reward_primary=reward_primary,
        penalty_primary=penalty_primary,
    )
    task.reward_primary = clamped_reward
    task.penalty_primary = clamped_penalty
    task.pricing_status = PricingStatus.APPLIED
    task.pricing_resolved_at = timezone.now()
    task.pricing_snapshot = {
        **(task.pricing_snapshot or {}),
        "applied_reward_primary": clamped_reward,
        "applied_penalty_primary": clamped_penalty,
        "raw_reward_primary": reward_primary,
        "raw_penalty_primary": penalty_primary,
        "pricing_bounds": bounds,
        "pricing_payload": pricing_payload,
        "server_clamped": clamped_reward != reward_primary or clamped_penalty != penalty_primary,
    }
    task.save(
        update_fields=[
            "reward_primary",
            "penalty_primary",
            "pricing_status",
            "pricing_resolved_at",
            "pricing_snapshot",
            "updated_at",
        ]
    )
    return task

