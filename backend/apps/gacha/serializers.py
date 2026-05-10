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
