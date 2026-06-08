from rest_framework import serializers

from apps.daily.models import DailyMetricRecord


class DailyMetricEvaluateSerializer(serializers.Serializer):
    record_date = serializers.DateField(required=False, help_text="Record date. Defaults to today.")
    wake_time = serializers.RegexField(regex=r"^\d{2}:\d{2}$", help_text="Wake-up time in HH:MM format.")
    sleep_time = serializers.RegexField(regex=r"^\d{2}:\d{2}$", help_text="Sleep time in HH:MM format.")
    phone_minutes = serializers.IntegerField(min_value=0, help_text="Phone usage minutes today.")
    water_cups = serializers.IntegerField(min_value=0, help_text="Water cups today.")


class DailyMetricRewardSerializer(serializers.ModelSerializer):
    feedback = serializers.CharField(source="agent_feedback")
    reward_transaction_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = DailyMetricRecord
        fields = (
            "id",
            "record_date",
            "wake_time",
            "sleep_time",
            "phone_minutes",
            "water_cups",
            "score",
            "reward_primary",
            "feedback",
            "agent_payload",
            "reward_transaction_id",
            "created_at",
            "updated_at",
        )
