from django.urls import path

from apps.wallet.views import WalletDebtResetView, WalletDetailView, WalletTransactionListView

urlpatterns = [
    path("", WalletDetailView.as_view(), name="wallet-detail"),
    path("transactions/", WalletTransactionListView.as_view(), name="wallet-transactions"),
    path("debt-reset/", WalletDebtResetView.as_view(), name="wallet-debt-reset"),
]
