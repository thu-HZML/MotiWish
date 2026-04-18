from rest_framework import serializers

from apps.gacha.models import GachaDrawRecord, GachaPool


class GachaPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = GachaPool
        fields = "__all__"


class GachaDrawRecordSerializer(serializers.ModelSerializer):
    pool = GachaPoolSerializer(read_only=True)

    class Meta:
        model = GachaDrawRecord
        fields = "__all__"
