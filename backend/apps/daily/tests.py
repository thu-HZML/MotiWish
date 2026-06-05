from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.daily.models import DailyMetricRecord, DailyMetricSummary, DailyRecordDetailLevel, DailySummaryWindow
from apps.users.models import StableProfile
from apps.wallet.models import CurrencyType, WalletTransaction


class DailyMetricApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="daily_user",
            email="daily@example.com",
            password="Password123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_evaluate_daily_metrics_returns_reward_and_creates_transaction(self):
        response = self.client.post(
            reverse("daily-metric-evaluate"),
            {
                "record_date": "2026-06-05",
                "wake_time": "07:30",
                "sleep_time": "23:30",
                "phone_minutes": 120,
                "water_cups": 6,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.data["data"]
        self.assertGreaterEqual(payload["reward_primary"], 0)
        self.assertLessEqual(payload["reward_primary"], 40)
        self.assertTrue(payload["feedback"])
        record = DailyMetricRecord.objects.get(owner=self.user, record_date=date(2026, 6, 5))
        self.assertEqual(record.reward_primary, payload["reward_primary"])
        self.assertEqual(record.reward_transaction.currency_type, CurrencyType.PRIMARY)
        self.assertEqual(record.reward_transaction.reference_type, "daily_metric_record")

    def test_same_day_evaluation_is_idempotent(self):
        request_payload = {
            "record_date": "2026-06-05",
            "wake_time": "07:30",
            "sleep_time": "23:30",
            "phone_minutes": 120,
            "water_cups": 6,
        }
        first = self.client.post(reverse("daily-metric-evaluate"), request_payload, format="json")
        second = self.client.post(reverse("daily-metric-evaluate"), request_payload, format="json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(DailyMetricRecord.objects.filter(owner=self.user, record_date=date(2026, 6, 5)).count(), 1)
        self.assertEqual(WalletTransaction.objects.filter(owner=self.user, reference_type="daily_metric_record").count(), 1)
        self.assertEqual(first.data["data"]["reward_primary"], second.data["data"]["reward_primary"])

    def test_chronotype_changes_sleep_target_context(self):
        stable, _ = StableProfile.objects.get_or_create(user=self.user)
        stable.chronotype = StableProfile.Chronotype.NIGHT
        stable.save()

        response = self.client.post(
            reverse("daily-metric-evaluate"),
            {
                "record_date": "2026-06-05",
                "wake_time": "09:30",
                "sleep_time": "01:30",
                "phone_minutes": 150,
                "water_cups": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["agent_payload"]["targets"]["chronotype"], "night")
        self.assertGreater(response.data["data"]["reward_primary"], 0)

    def test_history_compression_keeps_7d_reduces_30d_summarizes_1y_and_deletes_old(self):
        today = date(2026, 6, 5)
        detailed = DailyMetricRecord.objects.create(
            owner=self.user,
            record_date=today - timedelta(days=3),
            wake_time=time(7, 30),
            sleep_time=time(23, 30),
            phone_minutes=120,
            water_cups=6,
            score=90,
            reward_primary=35,
            agent_feedback="detail",
            profile_snapshot={"x": 1},
            agent_payload={"x": 1},
        )
        reducible = DailyMetricRecord.objects.create(
            owner=self.user,
            record_date=today - timedelta(days=12),
            wake_time=time(8, 0),
            sleep_time=time(0, 0),
            phone_minutes=180,
            water_cups=4,
            score=70,
            reward_primary=25,
            agent_feedback="detail",
            profile_snapshot={"x": 1},
            agent_payload={"x": 1},
        )
        monthly = DailyMetricRecord.objects.create(
            owner=self.user,
            record_date=today - timedelta(days=45),
            wake_time=time(8, 0),
            sleep_time=time(0, 0),
            phone_minutes=180,
            water_cups=4,
            score=60,
            reward_primary=20,
        )
        too_old = DailyMetricRecord.objects.create(
            owner=self.user,
            record_date=today - timedelta(days=400),
            wake_time=time(8, 0),
            sleep_time=time(0, 0),
            phone_minutes=180,
            water_cups=4,
            score=60,
            reward_primary=20,
        )

        response = self.client.post(
            reverse("daily-metric-evaluate"),
            {
                "record_date": today.isoformat(),
                "wake_time": "07:30",
                "sleep_time": "23:30",
                "phone_minutes": 120,
                "water_cups": 6,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        detailed.refresh_from_db()
        reducible.refresh_from_db()
        self.assertEqual(detailed.detail_level, DailyRecordDetailLevel.DETAILED)
        self.assertEqual(reducible.detail_level, DailyRecordDetailLevel.REDUCED)
        self.assertEqual(reducible.agent_payload, {})
        self.assertFalse(DailyMetricRecord.objects.filter(pk=monthly.pk).exists())
        self.assertFalse(DailyMetricRecord.objects.filter(pk=too_old.pk).exists())
        self.assertTrue(
            DailyMetricSummary.objects.filter(owner=self.user, window_type=DailySummaryWindow.MONTHLY_30D_1Y).exists()
        )
        self.assertTrue(
            DailyMetricSummary.objects.filter(owner=self.user, window_type=DailySummaryWindow.RECENT_7D_30D).exists()
        )
