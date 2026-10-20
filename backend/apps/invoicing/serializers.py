from rest_framework import serializers

from apps.invoicing.models import Invoice, InvoiceLine
from apps.invoicing.services import invoice_totals


class InvoiceLineSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceLine
        fields = ("id", "description", "quantity", "unit_price", "amount")

    def get_amount(self, obj):
        return f"{(obj.quantity * obj.unit_price):.2f}"


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True)
    subtotal = serializers.SerializerMethodField()
    tax = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = (
            "id", "number", "customer_name", "issue_date", "due_date", "status",
            "tax_rate", "lines", "subtotal", "tax", "total",
        )
        read_only_fields = ("id", "number", "status")

    def _totals(self, obj):
        return invoice_totals(obj)

    def get_subtotal(self, obj):
        return f"{self._totals(obj)[0]:.2f}"

    def get_tax(self, obj):
        return f"{self._totals(obj)[1]:.2f}"

    def get_total(self, obj):
        return f"{self._totals(obj)[2]:.2f}"

    def create(self, validated_data):
        lines = validated_data.pop("lines")
        organization = self.context["organization"]
        count = organization.invoices.count() + 1
        invoice = Invoice.objects.create(organization=organization, number=f"INV-{count:04d}", **validated_data)
        for line in lines:
            InvoiceLine.objects.create(invoice=invoice, **line)
        return invoice
