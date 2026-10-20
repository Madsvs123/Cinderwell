DEFAULT_CHART = [
    ("1000", "Cash", "asset"),
    ("1100", "Accounts receivable", "asset"),
    ("2000", "Accounts payable", "liability"),
    ("2100", "Tax payable", "liability"),
    ("3000", "Owner's equity", "equity"),
    ("4000", "Service income", "income"),
    ("5000", "General expense", "expense"),
    ("5100", "Software", "expense"),
    ("5200", "Contractors", "expense"),
]


def seed_chart(organization):
    from apps.ledger.models import Account

    Account.objects.bulk_create(
        [
            Account(organization=organization, code=code, name=name, type=kind)
            for code, name, kind in DEFAULT_CHART
        ]
    )
