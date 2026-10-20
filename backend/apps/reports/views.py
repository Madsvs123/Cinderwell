from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.budgets.models import BudgetLine
from apps.invoicing.models import Invoice
from apps.ledger.models import Account, JournalEntry
from apps.ledger.services import account_ledger, account_totals, money, tax_summary, trial_balance
from apps.ledger.views import organization_of
from apps.payables.models import Bill


def _parse_date(value, fallback):
    if not value:
        return fallback
    year, month, day = [int(part) for part in value.split("-")]
    return date(year, month, day)


class TaxSummaryView(APIView):
    def get(self, request):
        today = date.today()
        start = _parse_date(request.query_params.get("start"), date(today.year, 1, 1))
        end = _parse_date(request.query_params.get("end"), today)
        try:
            report = tax_summary(organization_of(request), start, end)
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=400)
        return Response(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "account_code": report["account_code"],
                "account_name": report["account_name"],
                "collected": f"{report['collected']:.2f}",
                "settled": f"{report['settled']:.2f}",
                "net_payable": f"{report['net_payable']:.2f}",
            }
        )


class TrialBalanceView(APIView):
    def get(self, request):
        as_of = _parse_date(request.query_params.get("as_of"), date.today())
        report = trial_balance(organization_of(request), as_of)
        return Response(
            {
                "as_of": as_of.isoformat(),
                "rows": [{**row, "debit": f"{row['debit']:.2f}", "credit": f"{row['credit']:.2f}"} for row in report["rows"]],
                "debit_total": f"{report['debit_total']:.2f}",
                "credit_total": f"{report['credit_total']:.2f}",
                "balanced": report["balanced"],
            }
        )


class AccountLedgerView(APIView):
    def get(self, request):
        org = organization_of(request)
        account = get_object_or_404(Account, pk=request.query_params.get("account"), organization=org)
        start = _parse_date(request.query_params.get("start"), None)
        end = _parse_date(request.query_params.get("end"), None)
        report = account_ledger(org, account, start, end)
        return Response(
            {
                "account_id": account.id,
                "code": account.code,
                "name": account.name,
                "type": account.type,
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
                "opening_balance": f"{report['opening_balance']:.2f}",
                "closing_balance": f"{report['closing_balance']:.2f}",
                "lines": [
                    {
                        **row,
                        "entry_date": row["entry_date"].isoformat(),
                        "debit": f"{row['debit']:.2f}",
                        "credit": f"{row['credit']:.2f}",
                        "balance": f"{row['balance']:.2f}",
                    }
                    for row in report["lines"]
                ],
            }
        )


class SearchView(APIView):
    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        org = organization_of(request)
        if not query:
            return Response({"q": "", "journals": [], "invoices": [], "bills": []})
        journals = JournalEntry.objects.filter(organization=org, memo__icontains=query).order_by("-entry_date", "-id")[:25]
        invoices = Invoice.objects.filter(organization=org, customer_name__icontains=query).order_by("-issue_date", "-id")[:25]
        bills = Bill.objects.filter(organization=org, vendor_name__icontains=query).order_by("-bill_date", "-id")[:25]
        return Response(
            {
                "q": query,
                "journals": [
                    {"id": entry.id, "entry_date": entry.entry_date.isoformat(), "memo": entry.memo, "source_type": entry.source_type}
                    for entry in journals
                ],
                "invoices": [
                    {"id": invoice.id, "number": invoice.number, "customer_name": invoice.customer_name, "status": invoice.status}
                    for invoice in invoices
                ],
                "bills": [
                    {"id": bill.id, "number": bill.number, "vendor_name": bill.vendor_name, "status": bill.status}
                    for bill in bills
                ],
            }
        )


class ProfitAndLossView(APIView):
    def get(self, request):
        today = date.today()
        start = _parse_date(request.query_params.get("start"), date(today.year, 1, 1))
        end = _parse_date(request.query_params.get("end"), today)
        rows = [row for row in account_totals(organization_of(request), start, end) if row["type"] in ("income", "expense")]
        income = sum((row["balance"] for row in rows if row["type"] == "income"), Decimal("0"))
        expense = sum((row["balance"] for row in rows if row["type"] == "expense"), Decimal("0"))
        return Response(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "rows": [{**row, "debit": f"{row['debit']:.2f}", "credit": f"{row['credit']:.2f}", "balance": f"{row['balance']:.2f}"} for row in rows],
                "income": f"{money(income):.2f}",
                "expense": f"{money(expense):.2f}",
                "net": f"{money(income - expense):.2f}",
            }
        )


class BalanceSheetView(APIView):
    def get(self, request):
        as_of = _parse_date(request.query_params.get("as_of"), date.today())
        rows = account_totals(organization_of(request), end=as_of)
        grouped = {"asset": [], "liability": [], "equity": []}
        totals = {"asset": Decimal("0"), "liability": Decimal("0"), "equity": Decimal("0")}
        earnings = Decimal("0")
        for row in rows:
            if row["type"] in ("income", "expense"):
                earnings += row["balance"] if row["type"] == "income" else -row["balance"]
                continue
            grouped[row["type"]].append(row)
            totals[row["type"]] += row["balance"]
        totals["equity"] += earnings
        payload_rows = {
            kind: [{**row, "balance": f"{row['balance']:.2f}", "debit": f"{row['debit']:.2f}", "credit": f"{row['credit']:.2f}"} for row in items]
            for kind, items in grouped.items()
        }
        return Response(
            {
                "as_of": as_of.isoformat(),
                "sections": payload_rows,
                "current_earnings": f"{money(earnings):.2f}",
                "totals": {key: f"{money(value):.2f}" for key, value in totals.items()},
                "balanced": money(totals["asset"]) == money(totals["liability"] + totals["equity"]),
            }
        )


class BudgetCompareView(APIView):
    def get(self, request):
        today = date.today()
        year = int(request.query_params.get("year", today.year))
        month = int(request.query_params.get("month", today.month))
        org = organization_of(request)
        start = date(year, month, 1)
        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month + 1, 1).fromordinal(date(year, month + 1, 1).toordinal() - 1)
        actuals = {row["account_id"]: row for row in account_totals(org, start, end)}
        lines = []
        for budget in BudgetLine.objects.filter(organization=org, year=year, month=month).select_related("account"):
            actual = actuals.get(budget.account_id, {}).get("balance", Decimal("0"))
            lines.append(
                {
                    "account_id": budget.account_id,
                    "code": budget.account.code,
                    "name": budget.account.name,
                    "type": budget.account.type,
                    "budget": f"{budget.amount:.2f}",
                    "actual": f"{money(actual):.2f}",
                    "variance": f"{money(actual - budget.amount):.2f}",
                }
            )
        return Response({"year": year, "month": month, "lines": lines})
