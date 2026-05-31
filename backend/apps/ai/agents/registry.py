from apps.ai.graphs.mock_goal_planner import MockGoalPlannerGraph


class AgentRegistry:
    def __init__(self):
        self._graphs = {
            "mock_goal_planner": MockGoalPlannerGraph(),
        }

    def list_workflows(self):
        return [graph.get_definition() for graph in self._graphs.values()]

    def get(self, workflow_key: str):
        return self._graphs[workflow_key]


agent_registry = AgentRegistry()
