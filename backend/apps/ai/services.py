import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from apps.common.timezones import business_localdate
from apps.ai.graphs.task_pricing import build_task_pricing_graph
from apps.ai.graphs.wish_pricing import build_wish_pricing_graph
from apps.ai.models import AITaskPricingSession, AIWishPricingSession
from apps.shop.models import ShopItemCategory, WishItem
from apps.tasks.models import PricingStatus, Task, TaskOccurrence
from apps.tasks.serializers import TaskSerializer
from apps.tasks.pricing import estimate_difficulty_level, estimate_task_size
from apps.users.models import DynamicProfile


def _run_task_pricing_graph(*, user, task_payload, feedback_history=None):
    graph = build_task_pricing_graph()
    return graph.invoke(
        {
            "user_id": user.id,
            "task_payload": task_payload,
            "feedback_history": feedback_history or [],
        }
    )


def _run_wish_pricing_graph(*, user, wish_payload, source, context_snapshot):
    graph = build_wish_pricing_graph()
    return graph.invoke(
        {
            "user_id": user.id,
            "source": source,
            "wish_payload": wish_payload,
            "context_snapshot": context_snapshot,
        }
    )


def build_wish_context_snapshot(*, user):
    recent_active_tasks = list(
        Task.objects.filter(owner=user, status="active")
        .order_by("-updated_at")
        .values(
            "id",
            "title",
            "task_type",
            "recurrence",
            "difficulty_level",
            "progress_target",
            "due_at",
        )[:8]
    )
    recent_wishes = list(
        WishItem.objects.filter(owner=user, category=ShopItemCategory.WISH)
        .order_by("-created_at")
        .values("id", "title", "price_tier", "price_secondary", "created_at")[:8]
    )
    recent_task_occurrences = list(
        TaskOccurrence.objects.filter(owner=user)
        .select_related("task")
        .order_by("-occurrence_date", "-updated_at")
        .values("id", "task_id", "task__title", "occurrence_date", "status", "progress")[:12]
    )
    snapshot = {
        "recent_active_tasks": recent_active_tasks,
        "recent_task_occurrences": recent_task_occurrences,
        "recent_wishes": recent_wishes,
    }
    return json.loads(json.dumps(snapshot, cls=DjangoJSONEncoder))


@transaction.atomic
def create_task_pricing_session(*, user, task_payload):
    state = _run_task_pricing_graph(user=user, task_payload=task_payload)
    return AITaskPricingSession.objects.create(
        owner=user,
        status=AITaskPricingSession.Status.WAITING_FEEDBACK,
        task_payload=task_payload,
        profile_snapshot=state.get("profile_snapshot", {}),
        pricing_standard_version=state.get("pricing_standard_version", "task_pricing_v1"),
        pricing_standard_excerpt=state.get("pricing_standard", ""),
        quote_payload=state["quote_payload"],
        feedback_history=[],
    )


@transaction.atomic
def create_wish_pricing_session(*, user, wish_payload, source=AIWishPricingSession.Source.MANUAL, refresh_date=None):
    context_snapshot = build_wish_context_snapshot(user=user)
    state = _run_wish_pricing_graph(
        user=user,
        wish_payload=wish_payload,
        source=source,
        context_snapshot=context_snapshot,
    )
    return AIWishPricingSession.objects.create(
        owner=user,
        source=source,
        status=AIWishPricingSession.Status.WAITING_CONFIRMATION,
        refresh_date=refresh_date,
        wish_payload=wish_payload,
        context_snapshot=context_snapshot,
        profile_snapshot=state.get("profile_snapshot", {}),
        pricing_standard_version=state.get("pricing_standard_version", "wish_pricing_v1"),
        pricing_standard_excerpt=state.get("pricing_standard", ""),
        quote_payload=state["quote_payload"],
    )


@transaction.atomic
def generate_daily_wish_refresh(*, user, refresh_date=None, force=False):
    refresh_date = refresh_date or business_localdate()
    existing = AIWishPricingSession.objects.filter(
        owner=user,
        source=AIWishPricingSession.Source.DAILY_REFRESH,
        refresh_date=refresh_date,
    ).first()
    if existing and not force:
        return existing, False
    if existing and force:
        existing.delete()

    session = create_wish_pricing_session(
        user=user,
        wish_payload={},
        source=AIWishPricingSession.Source.DAILY_REFRESH,
        refresh_date=refresh_date,
    )
    return session, True


@transaction.atomic
def accept_wish_pricing_session(*, session):
    session = AIWishPricingSession.objects.select_for_update().get(pk=session.pk)
    if session.status != AIWishPricingSession.Status.WAITING_CONFIRMATION:
        raise ValueError("只有等待确认的愿望定价会话可以确认")

    quote = session.quote_payload
    item = WishItem.objects.create(
        owner=session.owner,
        catalog_key="",
        title=quote.get("title") or session.wish_payload.get("title") or "AI 愿望奖励",
        description=quote.get("description") or session.wish_payload.get("description", ""),
        category=ShopItemCategory.WISH,
        rarity=quote.get("rarity", "common"),
        price_tier=quote["price_tier"],
        price_secondary=quote["price_secondary"],
        inventory=quote.get("inventory", session.wish_payload.get("inventory", 1)),
        is_enabled=True,
        is_stackable=True,
        auto_refund_on_reject=True,
        effect_payload={
            "source": "ai_wish_pricing",
            "pricing_session_id": session.id,
            "pricing_source": session.source,
        },
    )
    session.status = AIWishPricingSession.Status.ACCEPTED
    session.generated_item = item
    session.save(update_fields=["status", "generated_item", "updated_at"])
    return session


@transaction.atomic
def cancel_wish_pricing_session(*, session):
    session = AIWishPricingSession.objects.select_for_update().get(pk=session.pk)
    if session.status != AIWishPricingSession.Status.WAITING_CONFIRMATION:
        raise ValueError("只有等待确认的愿望定价会话可以取消")
    session.status = AIWishPricingSession.Status.CANCELLED
    session.save(update_fields=["status", "updated_at"])
    return session


@transaction.atomic
def revise_task_pricing_session(*, session, feedback_direction="", feedback_text=""):
    session = AITaskPricingSession.objects.select_for_update().get(pk=session.pk)
    if session.status != AITaskPricingSession.Status.WAITING_FEEDBACK:
        raise ValueError("只有等待反馈的定价会话可以继续调整")

    feedback = {
        "feedback_direction": feedback_direction,
        "feedback_text": feedback_text,
        "created_at": timezone.now().isoformat(),
        "previous_quote": session.quote_payload,
    }
    feedback_history = [*(session.feedback_history or []), feedback]
    state = _run_task_pricing_graph(
        user=session.owner,
        task_payload=session.task_payload,
        feedback_history=feedback_history,
    )
    session.feedback_history = feedback_history
    session.profile_snapshot = state.get("profile_snapshot", session.profile_snapshot)
    session.pricing_standard_excerpt = state.get("pricing_standard", session.pricing_standard_excerpt)
    session.quote_payload = state["quote_payload"]
    session.save(
        update_fields=[
            "feedback_history",
            "profile_snapshot",
            "pricing_standard_excerpt",
            "quote_payload",
            "updated_at",
        ]
    )
    return session


def _build_dynamic_profile_update(*, session, task):
    feedback_texts = [
        item.get("feedback_text", "")
        for item in session.feedback_history or []
        if item.get("feedback_text")
    ]
    direction_counts = {}
    for item in session.feedback_history or []:
        direction = item.get("feedback_direction") or "detail"
        direction_counts[direction] = direction_counts.get(direction, 0) + 1

    note_parts = []
    if direction_counts:
        note_parts.append(f"本次任务定价反馈轮次：{len(session.feedback_history)}，方向统计：{direction_counts}。")
    if feedback_texts:
        note_parts.append(f"用户补充偏好：{'；'.join(feedback_texts[-3:])}")
    note_parts.append(
        f"已接受任务《{task.title}》定价：奖励 {task.reward_primary}，惩罚 {task.penalty_primary}。"
    )
    refined_note = " ".join(note_parts)[:255]
    return {
        "current_top_goal": task.title,
        "current_main_blocker": refined_note,
        "pricing_feedback_summary": {
            "feedback_rounds": len(session.feedback_history or []),
            "direction_counts": direction_counts,
            "accepted_quote": session.quote_payload,
        },
    }


@transaction.atomic
def accept_task_pricing_session(*, session):
    session = AITaskPricingSession.objects.select_for_update().get(pk=session.pk)
    if session.status != AITaskPricingSession.Status.WAITING_FEEDBACK:
        raise ValueError("只有等待反馈的定价会话可以接受")

    quote = session.quote_payload
    inferred_difficulty = quote.get("pricing_bounds", {}).get("difficulty_level") or estimate_difficulty_level(
        {**session.task_payload, "auto_estimate_difficulty": True}
    )
    inferred_size = quote.get("pricing_bounds", {}).get("task_size") or estimate_task_size(
        {**session.task_payload, "difficulty_level": inferred_difficulty}
    )
    task_payload = {
        **session.task_payload,
        "difficulty_level": inferred_difficulty,
        "reward_primary": quote["reward_primary"],
        "penalty_primary": quote["penalty_primary"],
        "pricing_status": PricingStatus.APPLIED,
        "pricing_snapshot": {
            "source": "ai_task_pricing_assistant",
            "pricing_standard_version": session.pricing_standard_version,
            "quote_payload": quote,
            "feedback_history": session.feedback_history,
            "user_time_fields": {
                key: session.task_payload[key]
                for key in ("starts_on", "ends_on", "due_at")
                if session.task_payload.get(key)
            },
        },
        "ai_metadata": {
            **(session.task_payload.get("ai_metadata") or {}),
            "pricing_session_id": session.id,
            "task_size": inferred_size,
        },
    }
    serializer = TaskSerializer(data=task_payload)
    serializer.is_valid(raise_exception=True)
    task = serializer.save(owner=session.owner)
    task.pricing_status = PricingStatus.APPLIED
    task.pricing_resolved_at = timezone.now()
    task.pricing_snapshot = task_payload["pricing_snapshot"]
    task.save(update_fields=["pricing_status", "pricing_resolved_at", "pricing_snapshot", "updated_at"])

    dynamic_profile, _ = DynamicProfile.objects.select_for_update().get_or_create(user=session.owner)
    dynamic_update = _build_dynamic_profile_update(session=session, task=task)
    dynamic_profile.current_top_goal = dynamic_update["current_top_goal"]
    dynamic_profile.current_main_blocker = dynamic_update["current_main_blocker"]
    dynamic_profile.save(update_fields=["current_top_goal", "current_main_blocker", "updated_at"])

    session.status = AITaskPricingSession.Status.ACCEPTED
    session.created_task = task
    session.dynamic_profile_update = dynamic_update
    session.save(update_fields=["status", "created_task", "dynamic_profile_update", "updated_at"])
    return session
