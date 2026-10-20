from django.contrib import admin

from apps.ledger.models import Account, FiscalPeriod, JournalEntry, JournalLine, RecurringJournal

admin.site.register(Account)
admin.site.register(JournalEntry)
admin.site.register(JournalLine)
admin.site.register(FiscalPeriod)
admin.site.register(RecurringJournal)
