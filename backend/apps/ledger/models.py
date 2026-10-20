from django.db import models

from apps.accounts.models import Organization


class Account(models.Model):
    class Type(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        EQUITY = "equity", "Equity"
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="accounts")
    code = models.CharField(max_length=12)
    name = models.CharField(max_length=160)
    type = models.CharField(max_length=16, choices=Type.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class JournalEntry(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="journal_entries")
    entry_date = models.DateField()
    memo = models.CharField(max_length=240, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    source_type = models.CharField(max_length=40, blank=True)
    source_id = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-entry_date", "-id"]


class FiscalPeriod(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="fiscal_periods")
    name = models.CharField(max_length=80)
    start_date = models.DateField()
    end_date = models.DateField()
    locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date", "-id"]

    def __str__(self):
        return self.name


class RecurringJournal(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="recurring_journals")
    memo = models.CharField(max_length=240)
    next_date = models.DateField()
    interval_months = models.PositiveSmallIntegerField(default=1)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["next_date", "id"]

    def __str__(self):
        return self.memo


class RecurringJournalLine(models.Model):
    template = models.ForeignKey(RecurringJournal, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="recurring_lines")
    description = models.CharField(max_length=240, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]


class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="lines")
    description = models.CharField(max_length=240, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]


class AuditEvent(models.Model):
    class Action(models.TextChoices):
        POSTED = "posted", "Posted"
        REVERSED = "reversed", "Reversed"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="audit_events")
    action = models.CharField(max_length=16, choices=Action.choices)
    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="audit_events")
    detail = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
