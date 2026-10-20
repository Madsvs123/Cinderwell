from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.ledger.models import Account, JournalEntry, JournalLine

ZERO = Decimal("0.00")
DEBIT_NORMAL = {Account.Type.ASSET, Account.Type.EXPENSE}


def money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def signed_balance(account_type, debit, credit):
    debit = money(debit)
    credit = money(credit)
    if account_type in DEBIT_NORMAL:
        return debit - credit
    return credit - debit


@transaction.atomic
def create_posted_entry(organization, entry_date, memo, lines, source_type="", source_id=""):
    if source_id and JournalEntry.objects.filter(
        organization=organization, source_type=source_type, source_id=source_id, status=JournalEntry.Status.POSTED
    ).exists():
        return JournalEntry.objects.get(
            organization=organization, source_type=source_type, source_id=source_id, status=JournalEntry.Status.POSTED
        )

    cleaned = []
    debit_total = ZERO
    credit_total = ZERO
    for line in lines:
        debit = money(line.get("debit"))
        credit = money(line.get("credit"))
        if debit < 0 or credit < 0 or (debit and credit) or (debit == 0 and credit == 0):
            raise ValidationError("Each line needs a single positive debit or credit.")
        account = line["account"]
        if account.organization_id != organization.id:
            raise ValidationError("Account is outside this set of books.")
        cleaned.append((account, line.get("description", ""), debit, credit))
        debit_total += debit
        credit_total += credit
    if len(cleaned) < 2 or debit_total != credit_total or debit_total == 0:
        raise ValidationError("A journal entry must balance and contain at least two lines.")

    entry = JournalEntry.objects.create(
        organization=organization,
        entry_date=entry_date,
        memo=memo,
        status=JournalEntry.Status.POSTED,
        source_type=source_type,
        source_id=str(source_id or ""),
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(entry=entry, account=account, description=description, debit=debit, credit=credit)
            for account, description, debit, credit in cleaned
        ]
    )
    return entry


def parse_optional_date(value):
    if not value:
        return None
    if hasattr(value, "year") and hasattr(value, "month"):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError("Use a YYYY-MM-DD date.") from exc


@transaction.atomic
def reverse_entry(entry, reversal_date=None, memo=""):
    if entry.status != JournalEntry.Status.POSTED:
        raise ValidationError("Only a posted journal can be reversed.")
    if JournalEntry.objects.filter(
        organization=entry.organization,
        source_type="reversal",
        source_id=str(entry.id),
        status=JournalEntry.Status.POSTED,
    ).exists():
        raise ValidationError("This journal has already been reversed.")
    lines = [
        {
            "account": line.account,
            "description": line.description,
            "debit": line.credit,
            "credit": line.debit,
        }
        for line in entry.lines.select_related("account")
    ]
    when = reversal_date or timezone.localdate()
    text = memo or f"Reversal of journal {entry.id}"
    return create_posted_entry(
        entry.organization,
        when,
        text,
        lines,
        source_type="reversal",
        source_id=str(entry.id),
    )


@transaction.atomic
def post_opening_balance(organization, entry_date, memo, lines):
    if JournalEntry.objects.filter(
        organization=organization, source_type="opening", status=JournalEntry.Status.POSTED
    ).exists():
        raise ValidationError("Opening balances have already been posted.")
    return create_posted_entry(
        organization,
        entry_date,
        memo or "Opening balances",
        lines,
        source_type="opening",
        source_id="opening",
    )


def account_totals(organization, start=None, end=None):
    lines = JournalLine.objects.filter(entry__organization=organization, entry__status=JournalEntry.Status.POSTED)
    if start:
        lines = lines.filter(entry__entry_date__gte=start)
    if end:
        lines = lines.filter(entry__entry_date__lte=end)
    grouped = lines.values("account_id", "account__code", "account__name", "account__type").annotate(
        debit=Sum("debit"), credit=Sum("credit")
    )
    rows = []
    for row in grouped:
        balance = signed_balance(row["account__type"], row["debit"], row["credit"])
        rows.append(
            {
                "account_id": row["account_id"],
                "code": row["account__code"],
                "name": row["account__name"],
                "type": row["account__type"],
                "debit": money(row["debit"]),
                "credit": money(row["credit"]),
                "balance": balance,
            }
        )
    return sorted(rows, key=lambda item: item["code"])


def account_ledger(organization, account, start=None, end=None):
    posted = JournalLine.objects.filter(
        account=account,
        entry__organization=organization,
        entry__status=JournalEntry.Status.POSTED,
    )
    opening = ZERO
    if start:
        prior = posted.filter(entry__entry_date__lt=start).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        opening = signed_balance(account.type, prior["debit"], prior["credit"])
    lines = posted.select_related("entry")
    if start:
        lines = lines.filter(entry__entry_date__gte=start)
    if end:
        lines = lines.filter(entry__entry_date__lte=end)
    running = opening
    rows = []
    for line in lines.order_by("entry__entry_date", "entry_id", "id"):
        running += signed_balance(account.type, line.debit, line.credit)
        rows.append(
            {
                "line_id": line.id,
                "journal_id": line.entry_id,
                "entry_date": line.entry.entry_date,
                "memo": line.entry.memo,
                "description": line.description,
                "debit": money(line.debit),
                "credit": money(line.credit),
                "balance": money(running),
            }
        )
    return {"opening_balance": money(opening), "closing_balance": money(running), "lines": rows}


def require_account(organization, code):
    try:
        return Account.objects.get(organization=organization, code=code, is_active=True)
    except Account.DoesNotExist as exc:
        raise ValidationError(f"Missing account {code}.") from exc
