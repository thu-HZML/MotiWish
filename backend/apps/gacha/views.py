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
        # 获取前端传来的抽卡次数，默认为1
        times = int(request.data.get("times", 1))
        pool = self.get_object()
        
        # 限制单次最大抽卡次数，防止恶意请求
        if times < 1 or times > 10:
            return api_response(code=400, message="抽卡次数不合法，仅支持1-10次")

        records =[]
        try:
            # 开启事务，保证多次抽卡要么全成功，要么全失败（例如中途余额不足）
            with transaction.atomic():
                for _ in range(times):
                    record = draw_once(user=request.user, pool=pool)
                    records.append(record)
        except Exception as e:
            # 捕获 wallet.services 里抛出的余额不足等异常
            return api_response(code=400, message=str(e))

        return api_response(
            data=GachaDrawRecordSerializer(records, many=True).data, 
            message=f"成功抽卡 {times} 次"
        )


class GachaRecordViewSet(ApiResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GachaDrawRecordSerializer

    def get_queryset(self):
        return GachaDrawRecord.objects.filter(owner=self.request.user).select_related("pool")
