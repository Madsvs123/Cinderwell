from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.ledger.models import Account


CSV_TEXT = """date,memo,account_code,description,debit,credit
2026-05-04,Toner,5100,Black,30.00,0
2026-05-04,Toner,1000,Black,0,30.00
2026-05-18,Stamps,5000,Postage,12.00,0
2026-05-18,Stamps,1000,Postage,0,12.00
"""


class LedgerControlTests(TestCase):
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
        self.org = self.user.organization

    def _account(self, code):
        return Account.objects.get(organization=self.org, code=code)

    def test_csv_import_posts_each_balanced_memo(self):
        upload = SimpleUploadedFile("may.csv", CSV_TEXT.encode(), content_type="text/csv")
        imported = self.client.post("/api/journals/import-csv/", {"file": upload}, format="multipart")
        self.assertEqual(imported.status_code, 201, imported.data)
        memos = sorted(entry["memo"] for entry in imported.data)
        self.assertEqual(memos, ["Stamps", "Toner"])
        for entry in imported.data:
            debits = sum((Decimal(line["debit"]) for line in entry["lines"]), Decimal("0"))
            credits = sum((Decimal(line["credit"]) for line in entry["lines"]), Decimal("0"))
            self.assertEqual(debits, credits)
            self.assertGreater(debits, 0)

    def test_reversal_of_imported_journal_clears_the_account(self):
        upload = SimpleUploadedFile("may.csv", CSV_TEXT.encode(), content_type="text/csv")
        imported = self.client.post("/api/journals/import-csv/", {"file": upload}, format="multipart")
        self.assertEqual(imported.status_code, 201, imported.data)
        toner = next(entry for entry in imported.data if entry["memo"] == "Toner")
        reversed_entry = self.client.post(
            f"/api/journals/{toner['id']}/reverse/",
            {"reversal_date": "2026-05-05", "memo": "Undo toner"},
            format="json",
        )
        self.assertEqual(reversed_entry.status_code, 201, reversed_entry.data)
        self.assertEqual(reversed_entry.data["source_type"], "reversal")
        software = self._account("5100")
        ledger = self.client.get(f"/api/reports/account-ledger/?account={software.id}&end=2026-05-31")
        self.assertEqual(ledger.data["closing_balance"], "0.00")
        repeat = self.client.post(f"/api/journals/{toner['id']}/reverse/", format="json")
        self.assertEqual(repeat.status_code, 400)

    def test_locked_period_blocks_a_post_after_import(self):
        upload = SimpleUploadedFile("may.csv", CSV_TEXT.encode(), content_type="text/csv")
        imported = self.client.post("/api/journals/import-csv/", {"file": upload}, format="multipart")
        self.assertEqual(imported.status_code, 201, imported.data)
        period = self.client.post(
            "/api/periods/",
            {"name": "May 2026", "start_date": "2026-05-01", "end_date": "2026-05-31"},
            format="json",
        )
        self.assertEqual(period.status_code, 201, period.data)
        locked = self.client.post(f"/api/periods/{period.data['id']}/lock/")
        self.assertEqual(locked.status_code, 200, locked.data)
        cash = self._account("1000")
        expense = self._account("5000")
        lines = [
            {"account": expense.id, "debit": "4.00", "credit": "0"},
            {"account": cash.id, "debit": "0", "credit": "4.00"},
        ]
        rejected = self.client.post(
            "/api/journals/",
            {"entry_date": "2026-05-20", "memo": "After close", "lines": lines},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("locked", " ".join(rejected.data["detail"]).lower())
        allowed = self.client.post(
            "/api/journals/",
            {"entry_date": "2026-06-02", "memo": "After close", "lines": lines},
            format="json",
        )
        self.assertEqual(allowed.status_code, 201, allowed.data)
