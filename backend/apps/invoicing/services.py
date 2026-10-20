from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.html import escape

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


def render_invoice_html(invoice):
    subtotal, tax, total = invoice_totals(invoice)
    rows = []
    for line in invoice.lines.all():
        amount = money(line.quantity * line.unit_price)
        rows.append(
            "<tr>"
            f"<td>{escape(line.description)}</td>"
            f"<td class=\"num\">{line.quantity:.2f}</td>"
            f"<td class=\"num\">{line.unit_price:.2f}</td>"
            f"<td class=\"num\">{amount:.2f}</td>"
            "</tr>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(invoice.number)}</title>
<style>
  body {{ margin: 40px; color: #241c16; background: #fff; font-family: Georgia, "Iowan Old Style", Palatino, "Palatino Linotype", serif; }}
  h1 {{ font-size: 28px; margin: 0 0 4px; }}
  p {{ margin: 0 0 8px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
  th, td {{ text-align: left; padding: 8px 4px; border-bottom: 1px solid #ddcfbb; }}
  .num {{ text-align: right; }}
  .totals {{ margin-top: 16px; width: 240px; margin-left: auto; }}
  .muted {{ color: #8a5a2b; letter-spacing: 0.04em; text-transform: uppercase; font-size: 12px; }}
</style>
</head>
<body>
  <p class="muted">Invoice</p>
  <h1>{escape(invoice.number)}</h1>
  <p>{escape(invoice.organization.name)}</p>
  <p>Bill to {escape(invoice.customer_name)}</p>
  <p>Issued {invoice.issue_date.isoformat()} · Due {invoice.due_date.isoformat()}</p>
  <table>
    <thead><tr><th>Description</th><th class="num">Qty</th><th class="num">Price</th><th class="num">Amount</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <table class="totals">
    <tr><td>Subtotal</td><td class="num">{subtotal:.2f}</td></tr>
    <tr><td>Tax {invoice.tax_rate:.2f}%</td><td class="num">{tax:.2f}</td></tr>
    <tr><td>Total</td><td class="num">{total:.2f}</td></tr>
  </table>
</body>
</html>
"""
