from rest_framework.routers import DefaultRouter

from apps.invoicing.views import InvoiceViewSet

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
urlpatterns = router.urls
