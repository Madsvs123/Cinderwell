from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.ledger.services import create_posted_entry, require_account


class Command(BaseCommand):
    help = "Post a balanced manual journal for the operator who owns the books."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--date", required=True)
        parser.add_argument("--memo", default="")
        parser.add_argument(
            "--line",
            action="append",
            required=True,
            dest="lines",
            help="Account code, debit, and credit as code:debit:credit",
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email=options["email"])
        except user_model.DoesNotExist as exc:
            raise CommandError(f"No operator with email {options['email']}.") from exc
        try:
            entry_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError("Use a YYYY-MM-DD date.") from exc

        lines = []
        for raw in options["lines"]:
            parts = raw.split(":")
            if len(parts) != 3:
                raise CommandError("Each --line must look like 5100:25.00:0.")
            code, debit, credit = (part.strip() for part in parts)
            try:
                account = require_account(user.organization, code)
            except ValidationError as exc:
                raise CommandError(exc.messages[0]) from exc
            lines.append({"account": account, "description": options["memo"], "debit": debit, "credit": credit})
        try:
            entry = create_posted_entry(user.organization, entry_date, options["memo"], lines, source_type="cli")
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        self.stdout.write(self.style.SUCCESS(f"Posted journal {entry.id}."))
