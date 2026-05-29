from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from apps.ai.providers.factory import get_model_provider
from apps.ai.types import AgentState, AgentWorkflowDefinition

try:
    from langgraph.graph import END, START, StateGraph  # type: ignore
except ImportError:  # pragma: no cover - skeleton fallback
    END = "END"
    START = "START"
    StateGraph = None


class BaseAgentGraph(ABC):
    definition: AgentWorkflowDefinition

    def get_definition(self) -> AgentWorkflowDefinition:
        return self.definition

    @property
    def model_provider(self):
        return get_model_provider()

    def build_graph(self):
        if StateGraph is None:
            return None
        graph = StateGraph(AgentState)
        self.configure_nodes(graph)
        return graph.compile()

    @abstractmethod
    def configure_nodes(self, graph: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def invoke(self, *, owner_id: int, input_payload: dict, context_payload: dict | None = None) -> AgentState:
        raise NotImplementedError
