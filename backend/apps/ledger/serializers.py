from rest_framework import serializers

from apps.ledger.models import Account, FiscalPeriod, JournalEntry, JournalLine


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("id", "code", "name", "type", "is_active")
        read_only_fields = ("id",)


class JournalLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = JournalLine
        fields = ("id", "account", "account_code", "account_name", "description", "debit", "credit")


class JournalLineWriteSerializer(serializers.Serializer):
    account = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True)
    debit = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, default=0)
    credit = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, default=0)


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = ("id", "entry_date", "memo", "status", "source_type", "source_id", "lines", "created_at")


class FiscalPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalPeriod
        fields = ("id", "name", "start_date", "end_date", "locked", "locked_at")
        read_only_fields = ("id", "locked", "locked_at")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError("Period end is before the start.")
        org = self.context["organization"]
        overlap = FiscalPeriod.objects.filter(organization=org, start_date__lte=end, end_date__gte=start)
        if self.instance:
            overlap = overlap.exclude(pk=self.instance.pk)
        if overlap.exists():
            raise serializers.ValidationError("Periods cannot overlap.")
        return attrs

    def create(self, validated_data):
        return FiscalPeriod.objects.create(organization=self.context["organization"], **validated_data)


class JournalEntryWriteSerializer(serializers.Serializer):
    entry_date = serializers.DateField()
    memo = serializers.CharField(required=False, allow_blank=True)
    lines = JournalLineWriteSerializer(many=True)
