from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.response import Response

from apps.invoicing.models import Invoice
from apps.invoicing.serializers import InvoiceSerializer
from apps.invoicing.services import issue_invoice, pay_invoice, render_invoice_html
from apps.ledger.views import organization_of


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Invoice.objects.filter(organization=organization_of(self.request)).prefetch_related("lines")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = organization_of(self.request)
        return context

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        try:
            invoice = issue_invoice(self.get_object())
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        paid_on = request.data.get("paid_on")
        try:
            invoice = pay_invoice(self.get_object(), paid_on or None)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["get"], renderer_classes=[StaticHTMLRenderer])
    def preview(self, request, pk=None):
        return Response(render_invoice_html(self.get_object()))
