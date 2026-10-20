from rest_framework import serializers, viewsets

from apps.budgets.models import BudgetLine
from apps.ledger.models import Account
from apps.ledger.views import organization_of


class BudgetLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = BudgetLine
        fields = ("id", "account", "account_code", "account_name", "year", "month", "amount")

    def validate(self, attrs):
        org = self.context["organization"]
        account = attrs["account"]
        if account.organization_id != org.id:
            raise serializers.ValidationError("Account is outside these books.")
        if not 1 <= attrs["month"] <= 12:
            raise serializers.ValidationError("Month must be 1 through 12.")
        if account.type not in (Account.Type.INCOME, Account.Type.EXPENSE):
            raise serializers.ValidationError("Budgets attach to income or expense accounts.")
        return attrs

    def create(self, validated_data):
        return BudgetLine.objects.create(organization=self.context["organization"], **validated_data)


class BudgetLineViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetLineSerializer

    def get_queryset(self):
        queryset = BudgetLine.objects.filter(organization=organization_of(self.request)).select_related("account")
        year = self.request.query_params.get("year")
        if year:
            queryset = queryset.filter(year=year)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = organization_of(self.request)
        return context
