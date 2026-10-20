from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.ledger.services import create_posted_entry, money, require_account


def invoice_totals(invoice):
    subtotal = sum((line.quantity * line.unit_price for line in invoice.lines.all()), Decimal("0"))
    subtotal = money(subtotal)
    tax = money(subtotal * (invoice.tax_rate / Decimal("100")))
    return subtotal, tax, subtotal + tax


@transaction.atomic
def issue_invoice(invoice):
    if invoice.status != invoice.Status.DRAFT:
        raise ValueError("Only a draft invoice can be issued.")
    subtotal, tax, total = invoice_totals(invoice)
    if total <= 0:
        raise ValueError("Invoice total must be positive.")
    org = invoice.organization
    lines = [
        {"account": require_account(org, "1100"), "debit": total, "credit": 0, "description": invoice.number},
        {"account": require_account(org, "4000"), "debit": 0, "credit": subtotal, "description": invoice.customer_name},
    ]
    if tax:
        lines.append({"account": require_account(org, "2100"), "debit": 0, "credit": tax, "description": "Tax"})
    create_posted_entry(
        org,
        invoice.issue_date,
        f"Issue {invoice.number}",
        lines,
        source_type="invoice-issue",
        source_id=invoice.id,
    )
    invoice.status = invoice.Status.ISSUED
    invoice.save(update_fields=["status"])
    return invoice


@transaction.atomic
def pay_invoice(invoice, paid_on=None):
    if invoice.status != invoice.Status.ISSUED:
        raise ValueError("Only an issued invoice can be paid.")
    _, _, total = invoice_totals(invoice)
    org = invoice.organization
    create_posted_entry(
        org,
        paid_on or timezone.now().date(),
        f"Payment for {invoice.number}",
        [
            {"account": require_account(org, "1000"), "debit": total, "credit": 0, "description": invoice.number},
            {"account": require_account(org, "1100"), "debit": 0, "credit": total, "description": invoice.customer_name},
        ],
        source_type="invoice-pay",
        source_id=invoice.id,
    )
    invoice.status = invoice.Status.PAID
    invoice.save(update_fields=["status"])
    return invoice
