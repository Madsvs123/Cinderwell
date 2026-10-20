# Cinderwell plan

Cinderwell keeps one set of books for the operator's own company. Amounts are decimal currency. Every posted document becomes a journal entry. Debits and credits on an entry must match, and each line is either a debit or a credit.

## Chart

Assets and expenses carry a debit balance. Liabilities, equity, and income carry a credit balance. A new ledger starts with cash, accounts receivable, accounts payable, tax payable, owner's equity, service income, and three expense accounts. The operator can add accounts later.

## Posting

Issuing an invoice debits accounts receivable and credits service income. Tax, when present, is credited to tax payable. Paying that invoice debits cash and credits accounts receivable.

Recording a bill debits the chosen expense account and credits accounts payable. Paying it debits accounts payable and credits cash.

A manual journal is posted immediately. Draft invoices stay off the books until they are issued. Source type and source id stop the same invoice or bill from posting twice.

## Reports

Profit and loss sums income and expense between two dates. The balance sheet reads assets, liabilities, and equity up to a date, and folds current earnings into equity so the sheet can prove it balances. A budget line is a monthly target on an income or expense account. The budget report compares that target with the posted balance for the same month.

## Still ahead

- A month-end close that locks posted periods.
- Bank statement lines matched to cash journals.
- Multi-currency amounts with a stored rate on the journal line.
- PDF invoice output from the invoice that is already stored.
