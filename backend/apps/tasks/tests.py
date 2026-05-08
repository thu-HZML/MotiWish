from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.tasks.models import Task, TaskType
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
