from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.api import ApiResponseMixin, api_response
from apps.gacha.models import GachaDrawRecord, GachaPool
from apps.gacha.serializers import GachaDrawRecordSerializer, GachaPoolSerializer
from apps.gacha.services import draw_once


class GachaPoolViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GachaPoolSerializer
    queryset = GachaPool.objects.filter(is_active=True)

    @action(detail=True, methods=["post"], url_path="draw")
    def draw(self, request, pk=None):
        record = draw_once(user=request.user, pool=self.get_object())
        return api_response(data=GachaDrawRecordSerializer(record).data, message="抽卡成功")


class GachaRecordViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GachaDrawRecordSerializer

    def get_queryset(self):
        return GachaDrawRecord.objects.filter(owner=self.request.user).select_related("pool")
