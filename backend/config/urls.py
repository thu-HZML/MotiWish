from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

admin.site.site_header = "MotiWish 开发者后台"
admin.site.site_title = "MotiWish Admin"
admin.site.index_title = "业务管理"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/common/", include("apps.common.urls")),
    path("api/v1/users/", include("apps.users.urls")),
    path("api/v1/tasks/", include("apps.tasks.urls")),
    path("api/v1/daily/", include("apps.daily.urls")),
    path("api/v1/wallet/", include("apps.wallet.urls")),
    path("api/v1/gacha/", include("apps.gacha.urls")),
    path("api/v1/shop/", include("apps.shop.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
