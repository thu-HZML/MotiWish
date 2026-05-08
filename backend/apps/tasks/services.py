from django.db import transaction
from django.utils import timezone

from apps.tasks.models import (
    OccurrenceStatus,
    PricingStatus,
    RecurrenceType,
    Task,
    TaskOccurrence,
    TaskType,
)
from apps.tasks.pricing import build_pricing_context
from apps.wallet.models import CurrencyType, TransactionReason
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
def complete_task(*, task, target_date=None, progress=None):
    target_date = target_date or timezone.localdate()
    occurrence, _ = TaskOccurrence.objects.select_for_update().get_or_create(
        task=task,
        occurrence_date=target_date,
        defaults={"owner": task.owner},
    )
    if occurrence.status == OccurrenceStatus.COMPLETED:
        return occurrence
    occurrence.progress = progress if progress is not None else task.progress_target
    occurrence.status = OccurrenceStatus.COMPLETED
    occurrence.settled_at = timezone.now()
    if task.reward_primary:
        _, reward_transaction = change_balance(
            user=task.owner,
            currency_type=CurrencyType.PRIMARY,
            delta=task.reward_primary,
            reason=TransactionReason.TASK_REWARD,
            reference_type="task_occurrence",
            reference_id=occurrence.id,
            memo=f"完成任务：{task.title}",
        )
        occurrence.reward_transaction = reward_transaction
    occurrence.save()
    return occurrence


@transaction.atomic
def request_task_pricing(*, task):
    pricing_context = build_pricing_context(
        task_data={
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
    task.reward_primary = reward_primary
    task.penalty_primary = penalty_primary
    task.pricing_status = PricingStatus.APPLIED
    task.pricing_resolved_at = timezone.now()
    task.pricing_snapshot = {
        **(task.pricing_snapshot or {}),
        "applied_reward_primary": reward_primary,
        "applied_penalty_primary": penalty_primary,
        "pricing_payload": pricing_payload,
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
