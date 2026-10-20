from django.db import models

from apps.accounts.models import Organization
from apps.ledger.models import Account


class Bill(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PAID = "paid", "Paid"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="bills")
    number = models.CharField(max_length=20)
    vendor_name = models.CharField(max_length=160)
    bill_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    expense_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="bills")
    memo = models.CharField(max_length=240, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-bill_date", "-id"]
