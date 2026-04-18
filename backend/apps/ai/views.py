from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.ai.models import AIReportJob
from apps.ai.serializers import AIReportJobSerializer
from apps.common.api import ApiResponseMixin


class AIReportJobViewSet(ApiResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AIReportJobSerializer

    def get_queryset(self):
        return AIReportJob.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
