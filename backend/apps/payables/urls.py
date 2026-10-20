from rest_framework.routers import DefaultRouter

from apps.payables.views import BillViewSet

router = DefaultRouter()
router.register("bills", BillViewSet, basename="bill")
urlpatterns = router.urls
