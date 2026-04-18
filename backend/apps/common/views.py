from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.api import api_response


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return api_response(
            data={"service": "motiwish-backend", "status": "ok"},
            message="服务运行正常",
        )
