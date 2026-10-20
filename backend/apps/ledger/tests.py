from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.ledger.models import Account


class BooksFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        response = self.client.post(
            "/api/auth/register/",
            {
                "name": "Ada North",
                "email": "ada@example.com",
                "password": "ledger-pass",
                "organization_name": "North Studio",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        token = self.client.post(
            "/api/auth/token/",
            {"email": "ada@example.com", "password": "ledger-pass"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['access']}")
        self.user = get_user_model().objects.get(email="ada@example.com")

    def test_invoice_bill_and_reports_stay_balanced(self):
        invoice = self.client.post(
            "/api/invoices/",
            {
                "customer_name": "Sample Client",
                "issue_date": "2026-03-01",
                "due_date": "2026-03-15",
                "tax_rate": "10.00",
                "lines": [{"description": "Design week", "quantity": "2", "unit_price": "100.00"}],
            },
            format="json",
        )
        self.assertEqual(invoice.status_code, 201, invoice.data)
        issued = self.client.post(f"/api/invoices/{invoice.data['id']}/issue/")
        self.assertEqual(issued.status_code, 200)
        self.assertEqual(issued.data["total"], "220.00")

        expense = Account.objects.get(organization=self.user.organization, code="5100")
        bill = self.client.post(
            "/api/bills/",
            {
                "vendor_name": "Sample Host",
                "bill_date": "2026-03-02",
                "due_date": "2026-03-20",
                "amount": "50.00",
                "expense_account": expense.id,
                "memo": "Hosting",
            },
            format="json",
        )
        self.assertEqual(bill.status_code, 201, bill.data)
        pay_invoice = self.client.post(f"/api/invoices/{invoice.data['id']}/pay/", {"paid_on": "2026-03-10"}, format="json")
        pay_bill_response = self.client.post(f"/api/bills/{bill.data['id']}/pay/", {"paid_on": "2026-03-12"}, format="json")
        self.assertEqual(pay_invoice.status_code, 200, pay_invoice.data)
        self.assertEqual(pay_bill_response.status_code, 200, pay_bill_response.data)

        sheet = self.client.get("/api/reports/balance-sheet/?as_of=2026-03-31")
        self.assertTrue(sheet.data["balanced"])
        self.assertEqual(sheet.data["totals"]["asset"], "170.00")
        profit = self.client.get("/api/reports/profit-loss/?start=2026-03-01&end=2026-03-31")
        self.assertEqual(profit.data["net"], "150.00")

        unbalanced = self.client.post(
            "/api/journals/",
            {"entry_date": "2026-03-04", "memo": "Bad", "lines": [
                {"account": expense.id, "debit": "5.00", "credit": "0"},
                {"account": expense.id, "debit": "1.00", "credit": "0"},
            ]},
            format="json",
        )
        self.assertEqual(unbalanced.status_code, 400)

    def test_budget_variance(self):
        income = Account.objects.get(organization=self.user.organization, code="4000")
        created = self.client.post(
            "/api/budgets/",
            {"account": income.id, "year": 2026, "month": 3, "amount": "500.00"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        report = self.client.get("/api/reports/budget/?year=2026&month=3")
        self.assertEqual(report.data["lines"][0]["budget"], "500.00")
        self.assertEqual(date(2026, 3, 1).year, 2026)
        self.assertIsInstance(Decimal("500.00"), Decimal)

    def test_reversal_posts_the_opposite_entry(self):
        expense = Account.objects.get(organization=self.user.organization, code="5100")
        cash = Account.objects.get(organization=self.user.organization, code="1000")
        created = self.client.post(
            "/api/journals/",
            {
                "entry_date": "2026-04-01",
                "memo": "Supplies",
                "lines": [
                    {"account": expense.id, "debit": "40.00", "credit": "0"},
                    {"account": cash.id, "debit": "0", "credit": "40.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        reversed_entry = self.client.post(
            f"/api/journals/{created.data['id']}/reverse/",
            {"reversal_date": "2026-04-02", "memo": "Undo supplies"},
            format="json",
        )
        self.assertEqual(reversed_entry.status_code, 201, reversed_entry.data)
        self.assertEqual(reversed_entry.data["source_type"], "reversal")
        by_account = {line["account"]: line for line in reversed_entry.data["lines"]}
        self.assertEqual(Decimal(by_account[expense.id]["credit"]), Decimal("40.00"))
        self.assertEqual(Decimal(by_account[cash.id]["debit"]), Decimal("40.00"))
        again = self.client.post(f"/api/journals/{created.data['id']}/reverse/", format="json")
        self.assertEqual(again.status_code, 400)
        profit = self.client.get("/api/reports/profit-loss/?start=2026-04-01&end=2026-04-30")
        self.assertEqual(profit.data["net"], "0.00")

    def test_opening_balance_posts_once(self):
        cash = Account.objects.get(organization=self.user.organization, code="1000")
        equity = Account.objects.get(organization=self.user.organization, code="3000")
        payload = {
            "entry_date": "2026-01-01",
            "memo": "Opening balances",
            "lines": [
                {"account": cash.id, "debit": "800.00", "credit": "0"},
                {"account": equity.id, "debit": "0", "credit": "800.00"},
            ],
        }
        first = self.client.post("/api/opening-balances/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["source_type"], "opening")
        second = self.client.post("/api/opening-balances/", payload, format="json")
        self.assertEqual(second.status_code, 400)
        sheet = self.client.get("/api/reports/balance-sheet/?as_of=2026-01-31")
        self.assertTrue(sheet.data["balanced"])
        self.assertEqual(sheet.data["totals"]["asset"], "800.00")
