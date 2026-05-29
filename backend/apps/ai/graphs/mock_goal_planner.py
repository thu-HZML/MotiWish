from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from apps.ai.graphs.base import BaseAgentGraph
from apps.ai.prompts.goal_planner import GOAL_PLANNER_SYSTEM_PROMPT
from apps.ai.tools.context_builders import build_goal_planner_prompt_input
from apps.ai.types import AgentState
from apps.users.models import User


class MockGoalPlannerGraph(BaseAgentGraph):
    definition = {
        "key": "mock_goal_planner",
        "name": "Mock Goal Planner",
        "description": "用于长期目标拆解的 LangGraph 风格 mock 工作流。",
        "version": "0.1.0",
        "entrypoint": "plan_goal",
        "supports_streaming": False,
    }

    def configure_nodes(self, graph) -> None:
        if graph is None:
            return
        graph.add_node("plan_goal", lambda state: state)
        graph.add_edge("START", "plan_goal")
        graph.add_edge("plan_goal", "END")

    def invoke(self, *, owner_id: int, input_payload: dict, context_payload: dict | None = None) -> AgentState:
        context_payload = context_payload or {}
        goal = input_payload.get("goal", "未命名目标")
        user = User.objects.get(pk=owner_id)
        provider = self.model_provider
        provider_output = provider.generate_text(
            system_prompt=GOAL_PLANNER_SYSTEM_PROMPT,
            user_prompt=build_goal_planner_prompt_input(user=user, goal=goal),
            metadata={"goal": goal, "owner_id": owner_id},
        )
        return {
            "workflow_key": self.definition["key"],
            "owner_id": owner_id,
            "input_payload": input_payload,
            "context_payload": {
                **context_payload,
                "model_provider": provider.describe(),
            },
            "steps": [
                {
                    "node": "plan_goal",
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "note": f"workflow executed via provider {provider.provider_name}",
                }
            ],
            "result_payload": {
                "trace_id": uuid4().hex,
                "goal": goal,
                "summary": f"已为目标“{goal}”生成 mock 规划结果。",
                "provider_output": provider_output,
                "provider": provider.describe(),
                "task_drafts": [
                    {"title": "拆解阶段一", "description": "后续接入真实 LLM 逻辑后替换"},
                    {"title": "拆解阶段二", "description": "当前仅为结构占位"},
                ],
            },
            "status": "succeeded",
        }
