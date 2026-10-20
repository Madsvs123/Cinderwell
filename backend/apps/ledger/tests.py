from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
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
        preview = self.client.get(f"/api/invoices/{invoice.data['id']}/preview/")
        self.assertEqual(preview.status_code, 200)
        self.assertIn("text/html", preview["Content-Type"])
        self.assertIn(invoice.data["number"], preview.content.decode())
        self.assertIn("Sample Client", preview.content.decode())
        tax_report = self.client.get("/api/reports/tax-summary/?start=2026-03-01&end=2026-03-31")
        self.assertEqual(tax_report.status_code, 200, tax_report.data)
        self.assertEqual(tax_report.data["collected"], "20.00")
        self.assertEqual(tax_report.data["net_payable"], "20.00")
        found_customer = self.client.get("/api/search/?q=sample client")
        self.assertEqual(found_customer.status_code, 200, found_customer.data)
        self.assertEqual(found_customer.data["invoices"][0]["customer_name"], "Sample Client")
        self.assertEqual(found_customer.data["journals"], [])

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
        found_vendor = self.client.get("/api/search/?q=host")
        self.assertEqual(found_vendor.data["bills"][0]["vendor_name"], "Sample Host")
        found_memo = self.client.get("/api/search/?q=Issue")
        self.assertTrue(any(row["memo"].startswith("Issue") for row in found_memo.data["journals"]))
        outlook = self.client.get("/api/reports/cash-outlook/")
        self.assertEqual(outlook.status_code, 200, outlook.data)
        self.assertEqual(outlook.data["open_invoices"], "220.00")
        self.assertEqual(outlook.data["open_bills"], "50.00")
        self.assertEqual(outlook.data["net"], "170.00")
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
        audit = self.client.get("/api/audit/")
        self.assertEqual(audit.status_code, 200, audit.data)
        actions = [row["action"] for row in audit.data["results"]]
        self.assertEqual(actions.count("posted"), 1)
        self.assertEqual(actions.count("reversed"), 1)

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

    def test_account_ledger_keeps_a_running_balance(self):
        cash = Account.objects.get(organization=self.user.organization, code="1000")
        equity = Account.objects.get(organization=self.user.organization, code="3000")
        first = self.client.post(
            "/api/journals/",
            {
                "entry_date": "2026-02-01",
                "memo": "Seed cash",
                "lines": [
                    {"account": cash.id, "debit": "100.00", "credit": "0"},
                    {"account": equity.id, "debit": "0", "credit": "100.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(
            "/api/journals/",
            {
                "entry_date": "2026-02-10",
                "memo": "Owner draw",
                "lines": [
                    {"account": equity.id, "debit": "25.00", "credit": "0"},
                    {"account": cash.id, "debit": "0", "credit": "25.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(second.status_code, 201, second.data)
        ledger = self.client.get(f"/api/reports/account-ledger/?account={cash.id}&start=2026-02-01&end=2026-02-28")
        self.assertEqual(ledger.status_code, 200, ledger.data)
        self.assertEqual(ledger.data["opening_balance"], "0.00")
        self.assertEqual(ledger.data["closing_balance"], "75.00")
        self.assertEqual([line["balance"] for line in ledger.data["lines"]], ["100.00", "75.00"])

    def test_trial_balance_columns_match(self):
        cash = Account.objects.get(organization=self.user.organization, code="1000")
        income = Account.objects.get(organization=self.user.organization, code="4000")
        posted = self.client.post(
            "/api/journals/",
            {
                "entry_date": "2026-02-02",
                "memo": "Cash sale",
                "lines": [
                    {"account": cash.id, "debit": "60.00", "credit": "0"},
                    {"account": income.id, "debit": "0", "credit": "60.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(posted.status_code, 201, posted.data)
        report = self.client.get("/api/reports/trial-balance/?as_of=2026-02-28")
        self.assertEqual(report.status_code, 200, report.data)
        self.assertTrue(report.data["balanced"])
        self.assertEqual(report.data["debit_total"], report.data["credit_total"])
        self.assertEqual(report.data["debit_total"], "60.00")
        cash_row = next(row for row in report.data["rows"] if row["code"] == "1000")
        income_row = next(row for row in report.data["rows"] if row["code"] == "4000")
        self.assertEqual(cash_row["debit"], "60.00")
        self.assertEqual(income_row["credit"], "60.00")

    def test_fiscal_period_can_be_locked(self):
        created = self.client.post(
            "/api/periods/",
            {"name": "March 2026", "start_date": "2026-03-01", "end_date": "2026-03-31"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertFalse(created.data["locked"])
        overlap = self.client.post(
            "/api/periods/",
            {"name": "Mid March", "start_date": "2026-03-15", "end_date": "2026-04-15"},
            format="json",
        )
        self.assertEqual(overlap.status_code, 400)
        locked = self.client.post(f"/api/periods/{created.data['id']}/lock/")
        self.assertEqual(locked.status_code, 200, locked.data)
        self.assertTrue(locked.data["locked"])
        self.assertIsNotNone(locked.data["locked_at"])
        again = self.client.post(f"/api/periods/{created.data['id']}/lock/")
        self.assertEqual(again.status_code, 400)

    def test_locked_period_rejects_new_posts(self):
        cash = Account.objects.get(organization=self.user.organization, code="1000")
        equity = Account.objects.get(organization=self.user.organization, code="3000")
        period = self.client.post(
            "/api/periods/",
            {"name": "April 2026", "start_date": "2026-04-01", "end_date": "2026-04-30"},
            format="json",
        )
        self.assertEqual(period.status_code, 201, period.data)
        locked = self.client.post(f"/api/periods/{period.data['id']}/lock/")
        self.assertEqual(locked.status_code, 200, locked.data)
        lines = [
            {"account": cash.id, "debit": "15.00", "credit": "0"},
            {"account": equity.id, "debit": "0", "credit": "15.00"},
        ]
        rejected = self.client.post(
            "/api/journals/",
            {"entry_date": "2026-04-12", "memo": "Too late", "lines": lines},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400, rejected.data)
        self.assertIn("locked", " ".join(rejected.data["detail"]).lower())
        allowed = self.client.post(
            "/api/journals/",
            {"entry_date": "2026-05-02", "memo": "Next month", "lines": lines},
            format="json",
        )
        self.assertEqual(allowed.status_code, 201, allowed.data)

    def test_csv_import_posts_a_balanced_journal(self):
        csv_text = (
            "date,memo,account_code,description,debit,credit\n"
            "2026-05-01,Paper,5100,Ream,18.00,0\n"
            "2026-05-01,Paper,1000,Ream,0,18.00\n"
        )
        upload = SimpleUploadedFile("journals.csv", csv_text.encode(), content_type="text/csv")
        imported = self.client.post("/api/journals/import-csv/", {"file": upload}, format="multipart")
        self.assertEqual(imported.status_code, 201, imported.data)
        self.assertEqual(len(imported.data), 1)
        self.assertEqual(imported.data[0]["memo"], "Paper")
        self.assertEqual(imported.data[0]["source_type"], "csv")
        bad = (
            "date,memo,account_code,debit,credit\n"
            "2026-05-03,Broken,5100,9.00,0\n"
            "2026-05-03,Broken,1000,0,4.00\n"
        )
        rejected = self.client.post(
            "/api/journals/import-csv/",
            {"file": SimpleUploadedFile("bad.csv", bad.encode(), content_type="text/csv")},
            format="multipart",
        )
        self.assertEqual(rejected.status_code, 400)

    def test_recurring_template_posts_the_next_journal(self):
        expense = Account.objects.get(organization=self.user.organization, code="5100")
        cash = Account.objects.get(organization=self.user.organization, code="1000")
        future = date(date.today().year + 1, 6, 1)
        created = self.client.post(
            "/api/recurring/",
            {
                "memo": "Monthly hosting",
                "next_date": future.isoformat(),
                "interval_months": 1,
                "lines": [
                    {"account": expense.id, "debit": "12.00", "credit": "0", "description": "Host"},
                    {"account": cash.id, "debit": "0", "credit": "12.00", "description": "Host"},
                ],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        generated = self.client.post(f"/api/recurring/{created.data['id']}/generate/")
        self.assertEqual(generated.status_code, 201, generated.data)
        self.assertEqual(generated.data["memo"], "Monthly hosting")
        self.assertEqual(generated.data["source_type"], "recurring")
        listed = self.client.get("/api/recurring/")
        self.assertEqual(listed.data["results"][0]["next_date"], date(future.year, 7, 1).isoformat())

        due = (date.today() - timedelta(days=1)).isoformat()
        scheduled = self.client.post(
            "/api/recurring/",
            {
                "memo": "Due yesterday",
                "next_date": due,
                "interval_months": 1,
                "lines": [
                    {"account": expense.id, "debit": "3.00", "credit": "0"},
                    {"account": cash.id, "debit": "0", "credit": "3.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(scheduled.status_code, 201, scheduled.data)
        output = StringIO()
        call_command("generate_recurring", stdout=output)
        self.assertIn("Posted 1", output.getvalue())
