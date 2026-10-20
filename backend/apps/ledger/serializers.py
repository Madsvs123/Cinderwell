from rest_framework import serializers

from apps.ledger.models import (
    Account,
    AuditEvent,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    RecurringJournal,
    RecurringJournalLine,
)
from apps.ledger.services import money


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


class RecurringLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)

    class Meta:
        model = RecurringJournalLine
        fields = ("id", "account", "account_code", "description", "debit", "credit")
        read_only_fields = ("id", "account_code")


class RecurringJournalSerializer(serializers.ModelSerializer):
    lines = RecurringLineSerializer(many=True)

    class Meta:
        model = RecurringJournal
        fields = ("id", "memo", "next_date", "interval_months", "active", "lines")
        read_only_fields = ("id",)

    def validate_interval_months(self, value):
        if value < 1:
            raise serializers.ValidationError("Interval must be at least one month.")
        return value

    def validate(self, attrs):
        lines = attrs.get("lines")
        if lines is None:
            return attrs
        if len(lines) < 2:
            raise serializers.ValidationError("A recurring journal needs at least two lines.")
        debit_total = sum((money(line.get("debit")) for line in lines), money(0))
        credit_total = sum((money(line.get("credit")) for line in lines), money(0))
        if debit_total != credit_total or debit_total == 0:
            raise serializers.ValidationError("Recurring lines must balance.")
        org = self.context["organization"]
        for line in lines:
            if line["account"].organization_id != org.id:
                raise serializers.ValidationError("Account is outside these books.")
        return attrs

    def create(self, validated_data):
        lines = validated_data.pop("lines")
        template = RecurringJournal.objects.create(organization=self.context["organization"], **validated_data)
        RecurringJournalLine.objects.bulk_create(
            [RecurringJournalLine(template=template, **line) for line in lines]
        )
        return template

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            RecurringJournalLine.objects.bulk_create(
                [RecurringJournalLine(template=instance, **line) for line in lines]
            )
        return instance


class AuditEventSerializer(serializers.ModelSerializer):
    journal_memo = serializers.CharField(source="journal.memo", read_only=True)
    entry_date = serializers.DateField(source="journal.entry_date", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ("id", "action", "journal", "journal_memo", "entry_date", "detail", "created_at")


class JournalEntryWriteSerializer(serializers.Serializer):
    entry_date = serializers.DateField()
    memo = serializers.CharField(required=False, allow_blank=True)
    lines = JournalLineWriteSerializer(many=True)
