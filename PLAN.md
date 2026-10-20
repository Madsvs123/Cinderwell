# Cinderwell plan

Cinderwell keeps one set of books for the operator's own company. Amounts are decimal currency. Every posted document becomes a journal entry. Debits and credits on an entry must match, and each line is either a debit or a credit.

## Chart

Assets and expenses carry a debit balance. Liabilities, equity, and income carry a credit balance. A new ledger starts with cash, accounts receivable, accounts payable, tax payable, owner's equity, service income, and three expense accounts. The operator can add accounts later.

Opening balances are one posted journal. They can be entered once, and they use the same debit and credit rules as any other entry.

## Posting

Issuing an invoice debits accounts receivable and credits service income. Tax, when present, is credited to tax payable. Paying that invoice debits cash and credits accounts receivable. The stored invoice can be previewed as HTML.

Recording a bill debits the chosen expense account and credits accounts payable. Paying it debits accounts payable and credits cash.

A manual journal is posted immediately, from the journal screen or from `manage.py post_journal`. A CSV of balanced lines posts one entry per memo. A recurring template posts the next occurrence on demand or through `manage.py generate_recurring`.

Reversing a posted journal writes a new entry with every debit and credit swapped. The original stays in the books. Draft invoices stay off the books until they are issued. Source type and source id stop the same invoice, bill, import, or reversal from posting twice.

A fiscal period can be locked. A new journal whose date falls in a locked period is refused. Posting and reversing each leave an audit row.

## Reports

Profit and loss sums income and expense between two dates. The balance sheet reads assets, liabilities, and equity up to a date, and folds current earnings into equity so the sheet can prove it balances. The trial balance places each account balance in a debit or credit column and checks that the columns match. An account ledger lists every posted line for one account with a running balance.

A budget line is a monthly target on an income or expense account. The budget report compares that target with the posted balance for the same month. A month of budget lines can be copied into the next month.

The tax summary reads posted activity on tax payable. Cash outlook is the total of issued, unpaid invoices minus open bills.

Search looks through journal memos, invoice customer names, and bill vendor names.

## Still ahead

- Bank statement lines matched to cash journals, so a deposit or withdrawal can be tied to the entry that already moved cash.
- Multi-currency amounts with a stored rate on the journal line, converted into the books' base currency when the entry is posted.
- Attachments on journals, invoices, and bills, kept with the document they support.
