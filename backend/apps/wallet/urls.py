from django.urls import path

from apps.wallet.views import WalletDetailView, WalletTransactionListView

urlpatterns = [
    path("", WalletDetailView.as_view(), name="wallet-detail"),
    path("transactions/", WalletTransactionListView.as_view(), name="wallet-transactions"),
]
