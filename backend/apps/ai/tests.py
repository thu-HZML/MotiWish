from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.ai.models import AIAgentRun
from apps.ai.services import create_agent_run, execute_agent_run


class AIAgentRunSmokeTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ai_tester",
            email="ai_tester@example.com",
            password="Password123",
        )

    def test_mock_goal_planner_chain(self):
        agent_run = create_agent_run(
            owner=self.user,
            workflow_key="mock_goal_planner",
            input_payload={"goal": "两个月内建立稳定晨间学习习惯"},
        )

        result = execute_agent_run(agent_run=agent_run)
        result.refresh_from_db()

        self.assertEqual(result.status, AIAgentRun.Status.SUCCEEDED)
        self.assertEqual(result.workflow_key, "mock_goal_planner")
        self.assertIn("summary", result.result_payload)
        self.assertIn("provider", result.result_payload)
        self.assertTrue(result.trace_id)
        self.assertEqual(result.result_payload["provider"]["provider"], "mock")
