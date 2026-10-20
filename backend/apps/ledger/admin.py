from django.contrib import admin

from apps.ledger.models import Account, FiscalPeriod, JournalEntry, JournalLine

admin.site.register(Account)
admin.site.register(JournalEntry)
admin.site.register(JournalLine)
admin.site.register(FiscalPeriod)
