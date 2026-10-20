from django.urls import path

from apps.reports.views import BalanceSheetView, BudgetCompareView, ProfitAndLossView

urlpatterns = [
    path("reports/profit-loss/", ProfitAndLossView.as_view(), name="profit-loss"),
    path("reports/balance-sheet/", BalanceSheetView.as_view(), name="balance-sheet"),
    path("reports/budget/", BudgetCompareView.as_view(), name="budget-compare"),
]
