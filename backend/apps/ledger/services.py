import calendar
import csv
import hashlib
import io
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.ledger.models import Account, FiscalPeriod, JournalEntry, JournalLine, RecurringJournal

ZERO = Decimal("0.00")
DEBIT_NORMAL = {Account.Type.ASSET, Account.Type.EXPENSE}


def money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def period_is_locked(organization, entry_date):
    return FiscalPeriod.objects.filter(
        organization=organization,
        locked=True,
        start_date__lte=entry_date,
        end_date__gte=entry_date,
    ).exists()


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

    if period_is_locked(organization, entry_date):
        raise ValidationError("This date falls in a locked period.")

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


def source_token(value):
    text = str(value)
    if len(text) <= 40:
        return text
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:40]


@transaction.atomic
def import_journal_csv(organization, text):
    reader = csv.DictReader(io.StringIO(str(text).lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValidationError("CSV needs a header row.")
    fields = {(name or "").strip().lower() for name in reader.fieldnames}
    required = {"date", "account_code", "debit", "credit"}
    if not required <= fields:
        raise ValidationError("CSV must include date, account_code, debit, and credit columns.")
    groups = OrderedDict()
    for raw in reader:
        row = {(key or "").strip().lower(): (value or "").strip() for key, value in raw.items()}
        if not any(row.values()):
            continue
        if not row.get("date") or not row.get("account_code"):
            raise ValidationError("Each CSV row needs a date and an account code.")
        reference = row.get("reference") or f"{row['date']}|{row.get('memo', '')}"
        groups.setdefault(reference, []).append(row)
    if not groups:
        raise ValidationError("CSV did not contain any journal lines.")
    created = []
    for reference, rows in groups.items():
        try:
            entry_date = datetime.strptime(rows[0]["date"], "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError(f"Unreadable date {rows[0]['date']}.") from exc
        lines = [
            {
                "account": require_account(organization, row["account_code"]),
                "description": row.get("description", ""),
                "debit": row.get("debit") or 0,
                "credit": row.get("credit") or 0,
            }
            for row in rows
        ]
        created.append(
            create_posted_entry(
                organization,
                entry_date,
                rows[0].get("memo") or "Imported journal",
                lines,
                source_type="csv",
                source_id=source_token(reference),
            )
        )
    return created


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


def trial_balance(organization, as_of):
    totals = {row["account_id"]: row for row in account_totals(organization, end=as_of)}
    rows = []
    debit_total = ZERO
    credit_total = ZERO
    accounts = Account.objects.filter(organization=organization).order_by("code")
    for account in accounts:
        row = totals.get(account.id)
        if row is None and not account.is_active:
            continue
        balance = row["balance"] if row else ZERO
        if account.type in DEBIT_NORMAL:
            debit_col = balance if balance > 0 else ZERO
            credit_col = -balance if balance < 0 else ZERO
        else:
            credit_col = balance if balance > 0 else ZERO
            debit_col = -balance if balance < 0 else ZERO
        debit_col = money(debit_col)
        credit_col = money(credit_col)
        debit_total += debit_col
        credit_total += credit_col
        rows.append(
            {
                "account_id": account.id,
                "code": account.code,
                "name": account.name,
                "type": account.type,
                "debit": debit_col,
                "credit": credit_col,
            }
        )
    return {
        "rows": rows,
        "debit_total": money(debit_total),
        "credit_total": money(credit_total),
        "balanced": money(debit_total) == money(credit_total),
    }


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


def tax_summary(organization, start, end):
    account = Account.objects.filter(organization=organization, code="2100").first()
    if account is None:
        raise ValidationError("Tax payable account 2100 is missing.")
    totals = JournalLine.objects.filter(
        account=account,
        entry__organization=organization,
        entry__status=JournalEntry.Status.POSTED,
        entry__entry_date__gte=start,
        entry__entry_date__lte=end,
    ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
    collected = money(totals["credit"])
    settled = money(totals["debit"])
    return {
        "account_code": account.code,
        "account_name": account.name,
        "collected": collected,
        "settled": settled,
        "net_payable": money(collected - settled),
    }


def require_account(organization, code):
    try:
        return Account.objects.get(organization=organization, code=code, is_active=True)
    except Account.DoesNotExist as exc:
        raise ValidationError(f"Missing account {code}.") from exc


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


@transaction.atomic
def generate_next_recurring(template):
    template = RecurringJournal.objects.select_for_update().get(pk=template.pk)
    if not template.active:
        raise ValidationError("This recurring journal is inactive.")
    if template.interval_months < 1:
        raise ValidationError("Interval must be at least one month.")
    lines = [
        {
            "account": line.account,
            "description": line.description,
            "debit": line.debit,
            "credit": line.credit,
        }
        for line in template.lines.select_related("account")
    ]
    entry = create_posted_entry(
        template.organization,
        template.next_date,
        template.memo,
        lines,
        source_type="recurring",
        source_id=source_token(f"{template.id}:{template.next_date.isoformat()}"),
    )
    template.next_date = add_months(template.next_date, template.interval_months)
    template.save(update_fields=["next_date"])
    return entry


def generate_due_recurring(today=None):
    today = today or timezone.localdate()
    posted = []
    due = list(RecurringJournal.objects.filter(active=True, next_date__lte=today).order_by("id"))
    for template in due:
        catch_up = 0
        while template.next_date <= today and template.active and catch_up < 36:
            posted.append(generate_next_recurring(template))
            catch_up += 1
            template.refresh_from_db(fields=["next_date", "active"])
    return posted
