from typing import Any, TypedDict


class AgentWorkflowDefinition(TypedDict):
    key: str
    name: str
    description: str
    version: str
    entrypoint: str
    supports_streaming: bool


class AgentState(TypedDict, total=False):
    workflow_key: str
    owner_id: int
    input_payload: dict[str, Any]
    context_payload: dict[str, Any]
    steps: list[dict[str, Any]]
    result_payload: dict[str, Any]
    status: str
    error_message: str
