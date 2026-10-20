from django.db import transaction
from django.utils import timezone

from apps.ledger.services import create_posted_entry, require_account


@transaction.atomic
def open_bill(bill):
    org = bill.organization
    create_posted_entry(
        org,
        bill.bill_date,
        f"Bill {bill.number}",
        [
            {"account": bill.expense_account, "debit": bill.amount, "credit": 0, "description": bill.vendor_name},
            {"account": require_account(org, "2000"), "debit": 0, "credit": bill.amount, "description": bill.number},
        ],
        source_type="bill-open",
        source_id=bill.id,
    )
    return bill


@transaction.atomic
def pay_bill(bill, paid_on=None):
    if bill.status != bill.Status.OPEN:
        raise ValueError("Only an open bill can be paid.")
    org = bill.organization
    create_posted_entry(
        org,
        paid_on or timezone.now().date(),
        f"Pay {bill.number}",
        [
            {"account": require_account(org, "2000"), "debit": bill.amount, "credit": 0, "description": bill.number},
            {"account": require_account(org, "1000"), "debit": 0, "credit": bill.amount, "description": bill.vendor_name},
        ],
        source_type="bill-pay",
        source_id=bill.id,
    )
    bill.status = bill.Status.PAID
    bill.save(update_fields=["status"])
    return bill
