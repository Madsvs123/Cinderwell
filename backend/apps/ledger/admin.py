from django.contrib import admin

from apps.ledger.models import Account, AuditEvent, FiscalPeriod, JournalEntry, JournalLine, RecurringJournal

admin.site.register(Account)
admin.site.register(JournalEntry)
admin.site.register(JournalLine)
admin.site.register(FiscalPeriod)
admin.site.register(RecurringJournal)
admin.site.register(AuditEvent)
