from django.urls import path

from apps.reports.views import (
    AccountLedgerView,
    BalanceSheetView,
    BudgetCompareView,
    ProfitAndLossView,
    TaxSummaryView,
    TrialBalanceView,
)

urlpatterns = [
    path("reports/profit-loss/", ProfitAndLossView.as_view(), name="profit-loss"),
    path("reports/balance-sheet/", BalanceSheetView.as_view(), name="balance-sheet"),
    path("reports/budget/", BudgetCompareView.as_view(), name="budget-compare"),
    path("reports/account-ledger/", AccountLedgerView.as_view(), name="account-ledger"),
    path("reports/trial-balance/", TrialBalanceView.as_view(), name="trial-balance"),
    path("reports/tax-summary/", TaxSummaryView.as_view(), name="tax-summary"),
]
