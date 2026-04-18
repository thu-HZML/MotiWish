from rest_framework import serializers

from apps.ai.models import AIReportJob


class AIReportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIReportJob
        fields = "__all__"
        read_only_fields = ("owner", "status", "summary", "result_payload")
