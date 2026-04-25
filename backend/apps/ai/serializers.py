from rest_framework import serializers

from apps.ai.models import AIAgentRun, AIReportJob


class AIReportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIReportJob
        fields = "__all__"
        read_only_fields = ("owner", "status", "summary", "result_payload")


class AIAgentRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAgentRun
        fields = "__all__"
        read_only_fields = (
            "owner",
            "status",
            "context_payload",
            "state_payload",
            "result_payload",
            "error_message",
            "trace_id",
            "started_at",
            "finished_at",
        )


class AIAgentRunExecuteSerializer(serializers.Serializer):
    input_payload = serializers.JSONField(default=dict)


class AgentWorkflowDefinitionSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    version = serializers.CharField()
    entrypoint = serializers.CharField()
    supports_streaming = serializers.BooleanField()


class AIProviderConfigSerializer(serializers.Serializer):
    provider = serializers.CharField()
    model = serializers.CharField()
    base_url = serializers.CharField(allow_blank=True, allow_null=True)
    temperature = serializers.FloatField()
    timeout = serializers.IntegerField()
    max_retries = serializers.IntegerField()
