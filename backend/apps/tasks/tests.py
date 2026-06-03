from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.tasks.models import PricingStatus, SettlementTrack, Task, TaskOccurrence, TaskType
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
        today = timezone.localdate()
        task = Task.objects.create(
            owner=self.user,
            title="准备答辩材料",
            task_type=TaskType.ONE_TIME,
            due_at=timezone.make_aware(
                datetime(today.year, today.month, today.day, 18, 0),
                timezone.get_current_timezone(),
            ),
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


class TaskListApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="task_list_user",
            email="task_list@example.com",
            password="Password123!",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other_task_list_user",
            email="other_task_list@example.com",
            password="Password123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        Task.objects.create(owner=self.user, title="我的任务", task_type=TaskType.ONE_TIME)
        Task.objects.create(owner=self.other_user, title="其他用户任务", task_type=TaskType.ONE_TIME)

    def test_task_list_returns_paginated_data_inside_api_envelope(self):
        response = self.client.get(reverse("task-list"), {"page": 1})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(len(response.data["data"]["results"]), 1)
        self.assertEqual(response.data["data"]["results"][0]["title"], "我的任务")


class TaskProgressApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="task_progress_user",
            email="task_progress@example.com",
            password="Password123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.task = Task.objects.create(
            owner=self.user,
            title="推进课程项目",
            task_type=TaskType.ONE_TIME,
            progress_target=100,
        )

    def test_progress_action_updates_today_occurrence_progress(self):
        response = self.client.patch(
            reverse("task-progress", kwargs={"pk": self.task.pk}),
            {"progress": 60},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        occurrence = TaskOccurrence.objects.get(task=self.task, occurrence_date=timezone.localdate())
        self.assertEqual(occurrence.progress, 60)
        self.assertEqual(response.data["data"]["progress"], 60)

    def test_partial_update_accepts_progress_without_changing_progress_target(self):
        response = self.client.patch(
            reverse("task-detail", kwargs={"pk": self.task.pk}),
            {"progress": 40},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        occurrence = TaskOccurrence.objects.get(task=self.task, occurrence_date=timezone.localdate())
        self.assertEqual(self.task.progress_target, 100)
        self.assertEqual(occurrence.progress, 40)

    def test_partial_update_rejects_progress_target(self):
        response = self.client.patch(
            reverse("task-detail", kwargs={"pk": self.task.pk}),
            {"progress_target": 20},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("progress_target", str(response.data))
