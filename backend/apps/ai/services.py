from django.db import transaction
from django.utils import timezone

from apps.ai.graphs.task_pricing import build_task_pricing_graph
from apps.ai.models import AITaskPricingSession
from apps.tasks.models import PricingStatus
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
