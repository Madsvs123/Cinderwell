from django.core.management.base import BaseCommand

from apps.ledger.services import generate_due_recurring


class Command(BaseCommand):
    help = "Post recurring journals whose next date is today or earlier."

    def handle(self, *args, **options):
        posted = generate_due_recurring()
        self.stdout.write(self.style.SUCCESS(f"Posted {len(posted)} recurring journal(s)."))
