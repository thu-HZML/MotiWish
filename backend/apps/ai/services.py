from __future__ import annotations

from django.utils import timezone

from apps.ai.agents.registry import agent_registry
from apps.ai.config import get_ai_provider_settings
from apps.ai.models import AIAgentRun
from apps.ai.tools.context_builders import build_user_prompt_context


def create_agent_run(*, owner, workflow_key: str, input_payload: dict) -> AIAgentRun:
    return AIAgentRun.objects.create(
        owner=owner,
        workflow_key=workflow_key,
        input_payload=input_payload,
    )


def execute_agent_run(*, agent_run: AIAgentRun) -> AIAgentRun:
    workflow = agent_registry.get(agent_run.workflow_key)
    context_payload = build_user_prompt_context(agent_run.owner)
    context_payload["provider_settings"] = get_ai_provider_settings().__dict__

    agent_run.status = AIAgentRun.Status.RUNNING
    agent_run.context_payload = context_payload
    agent_run.started_at = timezone.now()
    agent_run.save(update_fields=["status", "context_payload", "started_at", "updated_at"])

    try:
        result_state = workflow.invoke(
            owner_id=agent_run.owner_id,
            input_payload=agent_run.input_payload,
            context_payload=context_payload,
        )
        agent_run.state_payload = result_state
        agent_run.result_payload = result_state.get("result_payload", {})
        agent_run.trace_id = agent_run.result_payload.get("trace_id", "")
        agent_run.status = AIAgentRun.Status.SUCCEEDED
        agent_run.error_message = ""
    except Exception as exc:  # pragma: no cover - future real workflow errors
        agent_run.status = AIAgentRun.Status.FAILED
        agent_run.error_message = str(exc)
    finally:
        agent_run.finished_at = timezone.now()
        agent_run.save(
            update_fields=[
                "state_payload",
                "result_payload",
                "trace_id",
                "status",
                "error_message",
                "finished_at",
                "updated_at",
            ]
        )
    return agent_run
