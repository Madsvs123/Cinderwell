from django.contrib import admin

from apps.accounts.models import Organization, User

admin.site.register(User)
admin.site.register(Organization)
