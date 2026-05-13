import os

from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest import skipUnless

from apps.ai.models import AITaskPricingSession
from apps.ai.services import (
    accept_task_pricing_session,
    create_task_pricing_session,
    revise_task_pricing_session,
)
from apps.tasks.models import PricingStatus, Task
from apps.users.models import DynamicProfile, StableProfile


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

    def test_create_task_pricing_session_generates_quote(self):
        session = create_task_pricing_session(
            user=self.user,
            task_payload={
                "title": "完成数据库课程复习",
                "description": "整理索引、事务、范式相关笔记",
                "task_type": "one_time",
                "recurrence": "none",
                "settlement_track": "regular",
                "difficulty_level": "medium",
                "progress_target": 100,
                "tags": ["study", "database"],
            },
        )

        self.assertEqual(session.status, AITaskPricingSession.Status.WAITING_FEEDBACK)
        self.assertEqual(session.quote_payload["reward_primary"], 160)
        self.assertEqual(session.quote_payload["penalty_primary"], 30)
        self.assertIn("任务定价标准", session.pricing_standard_excerpt)
        self.assertEqual(session.profile_snapshot["nickname"], "定价测试用户")

    def test_revise_task_pricing_session_uses_feedback(self):
        session = create_task_pricing_session(
            user=self.user,
            task_payload={
                "title": "完成数据库课程复习",
                "task_type": "one_time",
                "recurrence": "none",
                "settlement_track": "regular",
                "difficulty_level": "medium",
                "progress_target": 100,
            },
        )

        revised = revise_task_pricing_session(
            session=session,
            feedback_direction="too_low",
            feedback_text="这个任务需要更多查漏补缺，奖励偏低。",
        )

        self.assertEqual(len(revised.feedback_history), 1)
        self.assertGreater(
            revised.quote_payload["reward_primary"],
            session.quote_payload["reward_primary"],
        )

    def test_accept_task_pricing_session_creates_task_and_updates_dynamic_profile(self):
        session = create_task_pricing_session(
            user=self.user,
            task_payload={
                "title": "完成数据库课程复习",
                "description": "整理索引、事务、范式相关笔记",
                "task_type": "one_time",
                "recurrence": "none",
                "settlement_track": "regular",
                "difficulty_level": "medium",
                "progress_target": 100,
                "tags": ["study", "database"],
            },
        )

        accepted = accept_task_pricing_session(session=session)
        task = Task.objects.get(pk=accepted.created_task_id)
        dynamic_profile = DynamicProfile.objects.get(user=self.user)

        self.assertEqual(accepted.status, AITaskPricingSession.Status.ACCEPTED)
        self.assertEqual(task.reward_primary, accepted.quote_payload["reward_primary"])
        self.assertEqual(
            task.penalty_primary, accepted.quote_payload["penalty_primary"]
        )
        self.assertEqual(task.pricing_status, PricingStatus.APPLIED)
        self.assertEqual(dynamic_profile.current_top_goal, "完成数据库课程复习")


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
