import os
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.ai.models import AITaskPricingSession
from apps.ai.services import accept_task_pricing_session, create_task_pricing_session, revise_task_pricing_session
from apps.tasks.models import PricingStatus, Task
from apps.users.models import DynamicProfile, StableProfile


MOCK_AI_ENV = {"AI_PROVIDER": "mock", "AI_API_KEY": ""}


class TaskPricingAssistantTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pricing_user",
            email="pricing@example.com",
            password="Password123!",
            nickname="定价测试用户",
        )
        StableProfile.objects.get_or_create(user=self.user)
        DynamicProfile.objects.get_or_create(user=self.user)

    def _create_session(self, task_payload):
        with patch.dict(os.environ, MOCK_AI_ENV, clear=False):
            return create_task_pricing_session(user=self.user, task_payload=task_payload)

    def assert_quote(self, task_payload, expected_reward, expected_penalty):
        session = self._create_session(task_payload)
        self.assertEqual(session.status, AITaskPricingSession.Status.WAITING_FEEDBACK)
        self.assertEqual(session.quote_payload["reward_primary"], expected_reward)
        self.assertEqual(session.quote_payload["penalty_primary"], expected_penalty)
        self.assertIn("pricing_bounds", session.quote_payload)
        self.assertIn("本次建议奖励", session.quote_payload["reasoning"])
        self.assertIn("任务定价标准", session.pricing_standard_excerpt)
        self.assertEqual(session.profile_snapshot["nickname"], "定价测试用户")
        return session

    def test_daily_task_pricing(self):
        self.assert_quote(
            {
                "title": "英语听力 30 分钟",
                "task_type": "daily",
                "recurrence": "daily",
                "settlement_track": "regular",
                "difficulty_level": "medium",
                "metric_key": "study_minutes",
                "target_value": 30,
                "progress_target": 100,
                "tags": ["english"],
            },
            expected_reward=30,
            expected_penalty=10,
        )

    def test_weekly_recurring_task_pricing(self):
        self.assert_quote(
            {
                "title": "每周健身 3 次",
                "task_type": "recurring",
                "recurrence": "weekly",
                "settlement_track": "regular",
                "difficulty_level": "medium",
                "weekdays": [1, 3, 5],
                "progress_target": 100,
                "tags": ["fitness"],
            },
            expected_reward=100,
            expected_penalty=20,
        )

    def test_monthly_recurring_task_pricing(self):
        self.assert_quote(
            {
                "title": "每月读完一本书",
                "task_type": "recurring",
                "recurrence": "monthly",
                "settlement_track": "regular",
                "difficulty_level": "low",
                "month_days": [28],
                "progress_target": 100,
                "tags": ["reading"],
            },
            expected_reward=200,
            expected_penalty=30,
        )

    def test_one_time_task_pricing(self):
        self.assert_quote(
            {
                "title": "完成数据库课程复习",
                "description": "整理索引、事务、范式相关笔记",
                "task_type": "one_time",
                "recurrence": "none",
                "settlement_track": "regular",
                "difficulty_level": "medium",
                "progress_target": 100,
                "tags": ["study", "database"],
            },
            expected_reward=160,
            expected_penalty=30,
        )

    def test_exploration_task_pricing(self):
        self.assert_quote(
            {
                "title": "排查训练脚本问题",
                "task_type": "one_time",
                "recurrence": "none",
                "settlement_track": "exploration",
                "difficulty_level": "high",
                "estimated_focus_minutes": 180,
                "progress_target": 100,
                "tags": ["coding", "research"],
            },
            expected_reward=120,
            expected_penalty=15,
        )

    def test_revise_task_pricing_session_uses_feedback(self):
        session = self._create_session(
            {
                "title": "完成数据库课程复习",
                "task_type": "one_time",
                "recurrence": "none",
                "settlement_track": "regular",
                "difficulty_level": "medium",
                "progress_target": 100,
            }
        )

        with patch.dict(os.environ, MOCK_AI_ENV, clear=False):
            revised = revise_task_pricing_session(
                session=session,
                feedback_direction="too_low",
                feedback_text="这个任务需要更多查漏补缺，奖励偏低。",
            )

        self.assertEqual(len(revised.feedback_history), 1)
        self.assertGreater(revised.quote_payload["reward_primary"], session.quote_payload["reward_primary"])
        self.assertIn("上一轮报价基础上上调", revised.quote_payload["reasoning"])

    def test_revise_task_pricing_can_reverse_after_reaching_lower_bound(self):
        session = self._create_session(
            {
                "title": "整理一页错题",
                "task_type": "one_time",
                "recurrence": "none",
                "settlement_track": "regular",
                "difficulty_level": "low",
                "progress_target": 100,
            }
        )

        with patch.dict(os.environ, MOCK_AI_ENV, clear=False):
            for _ in range(10):
                session = revise_task_pricing_session(
                    session=session,
                    feedback_direction="too_high",
                    feedback_text="偏高",
                )
            lower_bound_reward = session.quote_payload["reward_primary"]
            session = revise_task_pricing_session(
                session=session,
                feedback_direction="too_low",
                feedback_text="现在偏低了",
            )

        self.assertGreater(session.quote_payload["reward_primary"], lower_bound_reward)
        self.assertLessEqual(
            session.quote_payload["reward_primary"],
            session.quote_payload["pricing_bounds"]["reward_primary"]["max"],
        )

    def test_accept_task_pricing_session_creates_task_and_updates_dynamic_profile(self):
        session = self._create_session(
            {
                "title": "完成数据库课程复习",
                "description": "整理索引、事务、范式相关笔记",
                "task_type": "one_time",
                "recurrence": "none",
                "settlement_track": "regular",
                "difficulty_level": "medium",
                "progress_target": 100,
                "tags": ["study", "database"],
            }
        )

        accepted = accept_task_pricing_session(session=session)
        task = Task.objects.get(pk=accepted.created_task_id)
        dynamic_profile = DynamicProfile.objects.get(user=self.user)

        self.assertEqual(accepted.status, AITaskPricingSession.Status.ACCEPTED)
        self.assertEqual(task.reward_primary, accepted.quote_payload["reward_primary"])
        self.assertEqual(task.penalty_primary, accepted.quote_payload["penalty_primary"])
        self.assertEqual(task.pricing_status, PricingStatus.APPLIED)
        self.assertEqual(dynamic_profile.current_top_goal, "完成数据库课程复习")


class TaskPricingAssistantApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pricing_api_user",
            email="pricing_api@example.com",
            password="Password123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_frontend_can_create_revise_and_accept_task_pricing_session(self):
        with patch.dict(os.environ, MOCK_AI_ENV, clear=False):
            create_response = self.client.post(
                reverse("ai-task-pricing-session-list"),
                {
                    "task_payload": {
                        "title": "英语听力 30 分钟",
                        "task_type": "daily",
                        "recurrence": "daily",
                        "settlement_track": "regular",
                        "difficulty_level": "medium",
                        "metric_key": "study_minutes",
                        "target_value": 30,
                        "progress_target": 100,
                        "tags": ["english"],
                    }
                },
                format="json",
            )

        self.assertEqual(create_response.status_code, 200)
        session_data = create_response.data["data"]
        self.assertEqual(session_data["status"], AITaskPricingSession.Status.WAITING_FEEDBACK)
        self.assertEqual(session_data["quote_payload"]["reward_primary"], 30)
        self.assertEqual(session_data["quote_payload"]["penalty_primary"], 10)

        with patch.dict(os.environ, MOCK_AI_ENV, clear=False):
            revise_response = self.client.post(
                reverse("ai-task-pricing-session-feedback", kwargs={"pk": session_data["id"]}),
                {
                    "action": "revise",
                    "feedback_direction": "too_low",
                    "feedback_text": "最近这个任务对我有点挑战，奖励偏低。",
                },
                format="json",
            )

        self.assertEqual(revise_response.status_code, 200)
        revised_data = revise_response.data["data"]
        self.assertEqual(len(revised_data["feedback_history"]), 1)
        self.assertGreater(revised_data["quote_payload"]["reward_primary"], session_data["quote_payload"]["reward_primary"])

        accept_response = self.client.post(
            reverse("ai-task-pricing-session-feedback", kwargs={"pk": session_data["id"]}),
            {"action": "accept"},
            format="json",
        )

        self.assertEqual(accept_response.status_code, 200)
        accepted_data = accept_response.data["data"]
        self.assertEqual(accepted_data["status"], AITaskPricingSession.Status.ACCEPTED)
        self.assertIsNotNone(accepted_data["created_task"])
        self.assertEqual(Task.objects.filter(owner=self.user, title="英语听力 30 分钟").count(), 1)

    def test_create_api_validates_task_payload_shape(self):
        response = self.client.post(
            reverse("ai-task-pricing-session-list"),
            {
                "task_payload": {
                    "title": "缺少专注时长的探索任务",
                    "task_type": "one_time",
                    "recurrence": "none",
                    "settlement_track": "exploration",
                    "difficulty_level": "high",
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("estimated_focus_minutes", str(response.data))

    def test_revise_requires_direction_or_text(self):
        with patch.dict(os.environ, MOCK_AI_ENV, clear=False):
            session = create_task_pricing_session(
                user=self.user,
                task_payload={
                    "title": "一次性任务",
                    "task_type": "one_time",
                    "recurrence": "none",
                    "settlement_track": "regular",
                    "difficulty_level": "low",
                    "progress_target": 100,
                },
            )

        response = self.client.post(
            reverse("ai-task-pricing-session-feedback", kwargs={"pk": session.id}),
            {"action": "revise"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)


@skipUnless(
    os.getenv("AI_PROVIDER") in {"openai-compatible", "openai"} and bool(os.getenv("AI_API_KEY")),
    "需要在 backend/.env 中配置 AI_PROVIDER=openai-compatible 或 openai，并配置 AI_API_KEY 才运行真实模型 smoke test",
)
class TaskPricingLiveModelSmokeTest(TestCase):
    def test_task_pricing_uses_live_model(self):
        user = get_user_model().objects.create_user(
            username="live_pricing_user",
            email="live_pricing@example.com",
            password="Password123!",
        )
        session = create_task_pricing_session(
            user=user,
            task_payload={
                "title": "完成 30 分钟英语听力训练",
                "description": "听一段材料并整理 5 个生词",
                "task_type": "daily",
                "recurrence": "daily",
                "settlement_track": "regular",
                "difficulty_level": "medium",
                "progress_target": 100,
                "tags": ["english", "listening"],
            },
        )
        self.assertEqual(
            session.quote_payload.get("llm_style_payload", {}).get("provider"),
            "openai-compatible",
            session.quote_payload.get("risk_notes"),
        )
