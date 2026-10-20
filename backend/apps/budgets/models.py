from django.db import models

from apps.accounts.models import Organization
from apps.ledger.models import Account


class BudgetLine(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="budget_lines")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="budget_lines")
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        unique_together = ("organization", "account", "year", "month")
        ordering = ["year", "month", "account__code"]
