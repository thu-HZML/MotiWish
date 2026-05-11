from rest_framework import serializers

from apps.gacha.models import GachaDrawRecord, GachaPool, GachaPoolUserState


class GachaPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = GachaPool
        fields = (
            "id",
            "name",
            "cost_primary",
            "common_reward",
            "rare_reward",
            "epic_reward",
            "legendary_reward",
            "common_rate",
            "rare_rate",
            "epic_rate",
            "legendary_rate",
            "rare_pity_threshold",
            "epic_pity_threshold",
            "legendary_pity_threshold",
            "is_active",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        values = {}
        for field in (
            "common_rate",
            "rare_rate",
            "epic_rate",
            "legendary_rate",
            "rare_pity_threshold",
            "epic_pity_threshold",
            "legendary_pity_threshold",
        ):
            values[field] = attrs.get(field, getattr(self.instance, field, None))

        rate_fields = ("common_rate", "rare_rate", "epic_rate", "legendary_rate")
        errors = {}
        for field in rate_fields:
            value = values[field]
            if value is not None and (value < 0 or value > 1):
                errors[field] = "概率必须在 0 到 1 之间。"

        if all(values[field] is not None for field in rate_fields):
            total_rate = sum(values[field] for field in rate_fields)
            if abs(total_rate - 1.0) > 1e-9:
                errors["common_rate"] = "四档概率总和必须等于 1。"

        thresholds = (
            values["rare_pity_threshold"],
            values["epic_pity_threshold"],
            values["legendary_pity_threshold"],
        )
        if any(value is not None and value < 1 for value in thresholds):
            errors["rare_pity_threshold"] = "保底阈值必须大于等于 1。"
        if all(value is not None for value in thresholds) and not (thresholds[0] < thresholds[1] < thresholds[2]):
            errors["rare_pity_threshold"] = "保底阈值必须满足 rare < epic < legendary。"

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class GachaPoolUserStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GachaPoolUserState
        fields = (
            "total_draws",
            "draws_since_rare",
            "draws_since_epic",
            "draws_since_legendary",
        )


class GachaDrawRecordSerializer(serializers.ModelSerializer):
    pool = GachaPoolSerializer(read_only=True)

    class Meta:
        model = GachaDrawRecord
        fields = (
            "id",
            "pool",
            "cost_primary",
            "reward_secondary",
            "reward_tier",
            "pity_tier",
            "created_at",
        )
