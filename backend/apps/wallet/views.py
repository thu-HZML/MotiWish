from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api import api_response
from apps.wallet.models import Wallet, WalletTransaction
from apps.wallet.serializers import WalletSerializer, WalletTransactionSerializer


class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(owner=request.user)
        return api_response(data=WalletSerializer(wallet).data, message="获取钱包成功")


class WalletTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = WalletTransaction.objects.filter(owner=self.request.user)
        currency_type = request.query_params.get("currency_type")
        reason = request.query_params.get("reason")
        if currency_type:
            queryset = queryset.filter(currency_type=currency_type)
        if reason:
            queryset = queryset.filter(reason=reason)
        data = WalletTransactionSerializer(queryset[:100], many=True).data
        return api_response(data=data, message="获取钱包流水成功")
