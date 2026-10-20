from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ledger.models import Account
from apps.ledger.views import organization_of
from apps.payables.models import Bill
from apps.payables.services import open_bill, pay_bill


class BillSerializer(serializers.ModelSerializer):
    expense_account_code = serializers.CharField(source="expense_account.code", read_only=True)

    class Meta:
        model = Bill
        fields = (
            "id", "number", "vendor_name", "bill_date", "due_date", "amount",
            "expense_account", "expense_account_code", "memo", "status",
        )
        read_only_fields = ("id", "number", "status")

    def validate_expense_account(self, account):
        org = self.context["organization"]
        if account.organization_id != org.id or account.type != Account.Type.EXPENSE:
            raise serializers.ValidationError("Choose an expense account in these books.")
        return account

    def create(self, validated_data):
        organization = self.context["organization"]
        count = organization.bills.count() + 1
        bill = Bill.objects.create(organization=organization, number=f"BILL-{count:04d}", **validated_data)
        open_bill(bill)
        return bill


class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Bill.objects.filter(organization=organization_of(self.request)).select_related("expense_account")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = organization_of(self.request)
        return context

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        try:
            bill = pay_bill(self.get_object(), request.data.get("paid_on") or None)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(bill).data)
