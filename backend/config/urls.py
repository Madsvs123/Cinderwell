from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.ledger.urls")),
    path("api/", include("apps.invoicing.urls")),
    path("api/", include("apps.payables.urls")),
    path("api/", include("apps.budgets.urls")),
    path("api/", include("apps.reports.urls")),
]
