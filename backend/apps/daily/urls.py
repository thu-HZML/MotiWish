from django.urls import path

from apps.daily.views import DailyMetricEvaluateView

urlpatterns = [
    path("evaluate/", DailyMetricEvaluateView.as_view(), name="daily-metric-evaluate"),
]
