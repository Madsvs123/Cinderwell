from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ledger.views import AccountViewSet, JournalEntryViewSet, OpeningBalanceView

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("journals", JournalEntryViewSet, basename="journal")
urlpatterns = [
    path("opening-balances/", OpeningBalanceView.as_view(), name="opening-balances"),
] + router.urls
