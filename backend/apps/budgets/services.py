from django.core.exceptions import ValidationError

from apps.budgets.models import BudgetLine


def copy_budget_forward(organization, year, month):
    if not 1 <= int(month) <= 12:
        raise ValidationError("Month must be 1 through 12.")
    if int(month) == 12:
        next_year, next_month = int(year) + 1, 1
    else:
        next_year, next_month = int(year), int(month) + 1
    source = BudgetLine.objects.filter(organization=organization, year=year, month=month)
    if not source.exists():
        raise ValidationError("That month has no budget lines to copy.")
    created = []
    for line in source:
        copy, was_created = BudgetLine.objects.get_or_create(
            organization=organization,
            account=line.account,
            year=next_year,
            month=next_month,
            defaults={"amount": line.amount},
        )
        if was_created:
            created.append(copy)
    return created, next_year, next_month
