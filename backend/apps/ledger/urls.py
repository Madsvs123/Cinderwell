from rest_framework.routers import DefaultRouter

from apps.ledger.views import AccountViewSet, JournalEntryViewSet

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("journals", JournalEntryViewSet, basename="journal")
urlpatterns = router.urls
