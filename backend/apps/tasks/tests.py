from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.tasks.models import PricingStatus, SettlementTrack, Task, TaskType
from apps.tasks.services import ensure_occurrences_for_date


class OneTimeTaskOccurrenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="task_tester",
            email="task_tester@example.com",
            password="Password123!",
        )

    def test_one_time_task_appears_every_day_before_due_date(self):
        task = Task.objects.create(
            owner=self.user,
            title="提交课程大作业",
            task_type=TaskType.ONE_TIME,
            due_at=datetime(2026, 5, 10, 23, 59, tzinfo=timezone.get_current_timezone()),
            starts_on=date(2026, 5, 7),
        )

        may_7 = ensure_occurrences_for_date(self.user, date(2026, 5, 7))
        may_8 = ensure_occurrences_for_date(self.user, date(2026, 5, 8))
        may_10 = ensure_occurrences_for_date(self.user, date(2026, 5, 10))
        may_11 = ensure_occurrences_for_date(self.user, date(2026, 5, 11))

        self.assertEqual(may_7.count(), 1)
        self.assertEqual(may_8.count(), 1)
        self.assertEqual(may_10.count(), 1)
        self.assertEqual(may_11.count(), 0)
        self.assertEqual(may_8.first().task_id, task.id)

    def test_one_time_task_without_starts_on_uses_creation_date_as_lower_bound(self):
        task = Task.objects.create(
            owner=self.user,
            title="准备答辩材料",
            task_type=TaskType.ONE_TIME,
            due_at=datetime(2026, 5, 10, 18, 0, tzinfo=timezone.get_current_timezone()),
        )

        created_day = timezone.localdate(task.created_at)
        day_before_creation = created_day.fromordinal(created_day.toordinal() - 1)

        before_queryset = ensure_occurrences_for_date(self.user, day_before_creation)
        created_day_queryset = ensure_occurrences_for_date(self.user, created_day)

        self.assertEqual(before_queryset.count(), 0)
        self.assertEqual(created_day_queryset.count(), 1)
        self.assertEqual(created_day_queryset.first().task_id, task.id)


class TaskPricingApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pricing_user",
            email="pricing@example.com",
            password="Password123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.task = Task.objects.create(
            owner=self.user,
            title="科研调试任务",
            task_type=TaskType.ONE_TIME,
            settlement_track=SettlementTrack.EXPLORATION,
            estimated_focus_minutes=180,
        )

    def test_pricing_preview_requires_focus_minutes_for_exploration(self):
        url = reverse("task-pricing-preview")
        response = self.client.post(
            url,
            {
                "task_type": "one_time",
                "settlement_track": "exploration",
                "difficulty_level": "high",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_pricing_request_marks_task_pending(self):
        url = reverse("task-pricing-request", kwargs={"pk": self.task.pk})
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.pricing_status, PricingStatus.PENDING)
        self.assertIn("formula", self.task.pricing_snapshot)

    def test_pricing_apply_updates_reward_and_penalty(self):
        url = reverse("task-pricing-apply", kwargs={"pk": self.task.pk})
        response = self.client.post(
            url,
            {
                "reward_primary": 120,
                "penalty_primary": 25,
                "pricing_payload": {"model": "mock-ai", "confidence": 0.8},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.reward_primary, 120)
        self.assertEqual(self.task.penalty_primary, 25)
        self.assertEqual(self.task.pricing_status, PricingStatus.APPLIED)
