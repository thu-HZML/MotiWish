from django.db import models

from apps.common.models import TimeStampedModel


class DailyRecordDetailLevel(models.TextChoices):
    DETAILED = "detailed", "Detailed"
    REDUCED = "reduced", "Reduced"


class DailySummaryWindow(models.TextChoices):
    RECENT_7D_30D = "recent_7d_30d", "Recent 7-30 days"
    MONTHLY_30D_1Y = "monthly_30d_1y", "Monthly 30 days to 1 year"


class DailyMetricRecord(TimeStampedModel):
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="daily_metric_records")
    record_date = models.DateField(db_index=True)
    wake_time = models.TimeField()
    sleep_time = models.TimeField()
    phone_minutes = models.PositiveIntegerField(default=0)
    water_cups = models.PositiveSmallIntegerField(default=0)
    score = models.PositiveSmallIntegerField(default=0)
    reward_primary = models.PositiveIntegerField(default=0)
    agent_feedback = models.TextField(blank=True)
    profile_snapshot = models.JSONField(default=dict, blank=True)
    history_snapshot = models.JSONField(default=dict, blank=True)
    agent_payload = models.JSONField(default=dict, blank=True)
    detail_level = models.CharField(
        max_length=16,
        choices=DailyRecordDetailLevel.choices,
        default=DailyRecordDetailLevel.DETAILED,
    )
    reward_transaction = models.ForeignKey(
        "wallet.WalletTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ("-record_date", "-id")
        unique_together = ("owner", "record_date")


class DailyMetricSummary(TimeStampedModel):
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="daily_metric_summaries")
    window_type = models.CharField(max_length=32, choices=DailySummaryWindow.choices)
    bucket_start = models.DateField(db_index=True)
    bucket_end = models.DateField(db_index=True)
    record_count = models.PositiveIntegerField(default=0)
    summary_text = models.TextField(blank=True)
    summary_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-bucket_end", "-id")
        unique_together = ("owner", "window_type", "bucket_start", "bucket_end")
