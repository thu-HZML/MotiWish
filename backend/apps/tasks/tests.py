from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.tasks.models import DifficultyLevel, PricingStatus, RecurrenceType, SettlementTrack, Task, TaskOccurrence, TaskType
from apps.tasks.services import ensure_occurrences_for_date
from apps.wallet.models import Wallet


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

    def test_pricing_preview_estimates_difficulty_and_bounds(self):
        response = self.client.post(
            reverse("task-pricing-preview"),
            {
                "title": "调试复杂训练系统",
                "task_type": "one_time",
                "settlement_track": "exploration",
                "estimated_focus_minutes": 180,
                "tags": ["debug"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.data["data"]["normalized_payload"]
        self.assertEqual(payload["difficulty_level"], DifficultyLevel.HIGH)
        self.assertEqual(payload["pricing_bounds"]["reward_primary"]["recommended"], 120)

    def test_removed_task_pricing_mutation_endpoints_are_not_exposed(self):
        self.assertEqual(self.client.post(f"/api/v1/tasks/tasks/{self.task.pk}/pricing/request/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/tasks/tasks/{self.task.pk}/pricing/apply/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/tasks/tasks/pricing/meta/").status_code, 404)


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


class TaskSettlementFormulaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="settlement_user",
            email="settlement@example.com",
            password="Password123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_one_time_regular_task_uses_progress_formula(self):
        task = Task.objects.create(
            owner=self.user,
            title="课程项目",
            task_type=TaskType.ONE_TIME,
            reward_primary=200,
            penalty_primary=50,
            progress_target=100,
            due_at=timezone.now() + timezone.timedelta(days=1),
        )

        response = self.client.post(
            reverse("task-complete", kwargs={"pk": task.pk}),
            {"progress": 60},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        occurrence = TaskOccurrence.objects.get(task=task)
        self.assertEqual(occurrence.reward_transaction.delta, 85)
        self.assertAlmostEqual(response.data["data"]["settlement_details"]["progress_factor"], 0.42)

    def test_exploration_task_rewards_actual_focus_minutes_by_difficulty(self):
        task = Task.objects.create(
            owner=self.user,
            title="排查训练脚本 Bug",
            task_type=TaskType.ONE_TIME,
            settlement_track=SettlementTrack.EXPLORATION,
            difficulty_level=DifficultyLevel.HIGH,
            estimated_focus_minutes=300,
        )

        response = self.client.post(
            reverse("task-complete", kwargs={"pk": task.pk}),
            {"progress": 300},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        occurrence = TaskOccurrence.objects.get(task=task)
        self.assertEqual(occurrence.reward_transaction.delta, 200)
        self.assertEqual(response.data["data"]["settlement_details"]["difficulty_factor"], 40)

    def test_weekly_recurring_task_pays_incremental_cycle_reward(self):
        task = Task.objects.create(
            owner=self.user,
            title="每周健身 3 次",
            task_type=TaskType.RECURRING,
            recurrence=RecurrenceType.WEEKLY,
            difficulty_level=DifficultyLevel.MEDIUM,
            reward_primary=100,
            weekdays=[0, 2, 4],
            starts_on=date(2026, 6, 1),
        )

        rewards = []
        for day in [date(2026, 6, 1), date(2026, 6, 3), date(2026, 6, 5)]:
            response = self.client.post(
                reverse("task-complete", kwargs={"pk": task.pk}),
                {"occurrence_date": day.isoformat()},
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            rewards.append(TaskOccurrence.objects.get(task=task, occurrence_date=day).reward_transaction.delta)

        self.assertEqual(rewards, [25, 30, 45])
        self.assertEqual(sum(rewards), 100)


    def test_period_settlement_applies_recurring_penalty_and_returns_details(self):
        task = Task.objects.create(
            owner=self.user,
            title="Weekly workout 4 times",
            task_type=TaskType.RECURRING,
            recurrence=RecurrenceType.WEEKLY,
            difficulty_level=DifficultyLevel.HIGH,
            reward_primary=100,
            penalty_primary=30,
            weekdays=[0, 1, 2, 3],
            starts_on=date(2026, 6, 1),
        )
        self.client.post(
            reverse("task-complete", kwargs={"pk": task.pk}),
            {"occurrence_date": "2026-06-01"},
            format="json",
        )

        response = self.client.post(
            reverse("task-complete", kwargs={"pk": task.pk}),
            {"occurrence_date": "2026-06-04", "settle_period": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        details = response.data["data"]["settlement_details"]
        self.assertEqual(details["settlement_mode"], "period")
        self.assertEqual(details["completed_count"], 1)
        self.assertEqual(details["expected_count"], 4)
        self.assertEqual(details["missed_count"], 3)
        self.assertEqual(details["reward_primary"], 0)
        self.assertEqual(details["penalty_primary"], 20)
        occurrence = TaskOccurrence.objects.get(task=task, occurrence_date=date(2026, 6, 4))
        self.assertEqual(occurrence.status, "missed")
        self.assertEqual(occurrence.penalty_transaction.delta, -20)

    def test_overdue_penalty_respects_primary_debt_floor(self):
        Wallet.objects.create(owner=self.user, primary_balance=-80)
        task = Task.objects.create(
            owner=self.user,
            title="逾期大任务",
            task_type=TaskType.ONE_TIME,
            reward_primary=300,
            penalty_primary=70,
            progress_target=100,
            due_at=timezone.now() - timezone.timedelta(days=2),
        )

        response = self.client.post(
            reverse("task-complete", kwargs={"pk": task.pk}),
            {"progress": 0},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        wallet = Wallet.objects.get(owner=self.user)
        self.assertEqual(wallet.primary_balance, -100)
        occurrence = TaskOccurrence.objects.get(task=task)
        self.assertEqual(occurrence.penalty_transaction.delta, -20)
        self.assertEqual(occurrence.penalty_transaction.payload["calculated_penalty_primary"], 70)

