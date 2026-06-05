from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api import api_response
from apps.common.openapi import api_envelope_serializer
from apps.daily.serializers import DailyMetricEvaluateSerializer, DailyMetricRewardSerializer
from apps.daily.services import evaluate_daily_metrics


class DailyMetricEvaluateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Daily"],
        summary="\u8bc4\u4f30\u4eca\u65e5\u65e5\u5e38\u6307\u6807",
        description=(
            "\u63d0\u4ea4\u8d77\u5e8a\u65f6\u95f4\u3001\u7761\u89c9\u65f6\u95f4\u3001\u624b\u673a\u4f7f\u7528\u65f6\u957f\u548c\u996e\u6c34\u676f\u6570\uff0c"
            "\u540e\u7aef Agent \u7ed3\u5408\u7528\u6237\u753b\u50cf\u548c\u8fd1\u671f\u65e5\u5e38\u5386\u53f2\u7ed9\u51fa\u53cd\u9988\u548c\u4e00\u7ea7\u8d27\u5e01\u5956\u52b1\u3002"
            "\u540c\u4e00\u7528\u6237\u540c\u4e00\u65e5\u671f\u53ea\u4f1a\u9996\u6b21\u53d1\u653e\u5956\u52b1\u3002"
        ),
        request=DailyMetricEvaluateSerializer,
        responses=api_envelope_serializer("DailyMetricEvaluateResponse", DailyMetricRewardSerializer()),
        examples=[
            OpenApiExample(
                "\u8bc4\u4f30\u4eca\u65e5\u65e5\u5e38",
                value={"wake_time": "07:30", "sleep_time": "23:40", "phone_minutes": 180, "water_cups": 5},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = DailyMetricEvaluateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record, created = evaluate_daily_metrics(user=request.user, **serializer.validated_data)
        message = "\u65e5\u5e38\u8bc4\u4f30\u5b8c\u6210" if created else "\u4eca\u65e5\u65e5\u5e38\u5df2\u8bc4\u4f30"
        return api_response(data=DailyMetricRewardSerializer(record).data, message=message)
