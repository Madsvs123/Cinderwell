from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ledger.views import (
    AccountViewSet,
    FiscalPeriodViewSet,
    JournalEntryViewSet,
    OpeningBalanceView,
    RecurringJournalViewSet,
)

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("journals", JournalEntryViewSet, basename="journal")
router.register("periods", FiscalPeriodViewSet, basename="period")
router.register("recurring", RecurringJournalViewSet, basename="recurring")
urlpatterns = [
    path("opening-balances/", OpeningBalanceView.as_view(), name="opening-balances"),
] + router.urls
