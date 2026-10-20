from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ledger.models import Account, FiscalPeriod, JournalEntry
from apps.ledger.serializers import (
    AccountSerializer,
    FiscalPeriodSerializer,
    JournalEntrySerializer,
    JournalEntryWriteSerializer,
)
from apps.ledger.services import create_posted_entry, parse_optional_date, post_opening_balance, reverse_entry


def organization_of(request):
    return request.user.organization


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(organization=organization_of(self.request))

    def perform_create(self, serializer):
        serializer.save(organization=organization_of(self.request))


class JournalEntryViewSet(viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return JournalEntry.objects.filter(organization=organization_of(self.request)).prefetch_related("lines__account")

    def create(self, request):
        serializer = JournalEntryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = organization_of(request)
        payload = serializer.validated_data
        lines = []
        for line in payload["lines"]:
            account = get_object_or_404(Account, pk=line["account"], organization=org)
            lines.append({**line, "account": account})
        try:
            entry = create_posted_entry(org, payload["entry_date"], payload.get("memo", ""), lines, source_type="manual")
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(JournalEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        entry = self.get_object()
        try:
            reversal_date = parse_optional_date(request.data.get("reversal_date"))
            reversed_entry = reverse_entry(entry, reversal_date, request.data.get("memo") or "")
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(JournalEntrySerializer(reversed_entry).data, status=status.HTTP_201_CREATED)


class FiscalPeriodViewSet(viewsets.ModelViewSet):
    serializer_class = FiscalPeriodSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return FiscalPeriod.objects.filter(organization=organization_of(self.request))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = organization_of(self.request)
        return context

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        period = self.get_object()
        if period.locked:
            return Response({"detail": "This period is already locked."}, status=status.HTTP_400_BAD_REQUEST)
        period.locked = True
        period.locked_at = timezone.now()
        period.save(update_fields=["locked", "locked_at"])
        return Response(self.get_serializer(period).data)


class OpeningBalanceView(APIView):
    def post(self, request):
        serializer = JournalEntryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = organization_of(request)
        payload = serializer.validated_data
        lines = []
        for line in payload["lines"]:
            account = get_object_or_404(Account, pk=line["account"], organization=org)
            lines.append({**line, "account": account})
        try:
            entry = post_opening_balance(org, payload["entry_date"], payload.get("memo", ""), lines)
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(JournalEntrySerializer(entry).data, status=status.HTTP_201_CREATED)
