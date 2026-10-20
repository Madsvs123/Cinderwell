from django.db import models

from apps.accounts.models import Organization


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PAID = "paid", "Paid"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invoices")
    number = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=160)
    issue_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "number")
        ordering = ["-issue_date", "-id"]


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=240)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def amount(self):
        return (self.quantity * self.unit_price).quantize(self.unit_price)
