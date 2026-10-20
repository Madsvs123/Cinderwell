import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Account, api } from "../api/client";
import { money, prettyDate } from "../lib/format";

type Profit = { income: string; expense: string; net: string; rows: { code: string; name: string; balance: string }[] };
type Sheet = { balanced: boolean; current_earnings: string; totals: Record<string, string>; sections: Record<string, { code: string; name: string; balance: string }[]> };
type Compare = { lines: { code: string; name: string; budget: string; actual: string; variance: string }[] };
type Trial = { balanced: boolean; debit_total: string; credit_total: string; rows: { code: string; name: string; debit: string; credit: string }[] };
type Ledger = { code: string; name: string; opening_balance: string; closing_balance: string; lines: { line_id: number; entry_date: string; memo: string; debit: string; credit: string; balance: string }[] };
type Outlook = {
  open_invoices: string; open_bills: string; net: string;
  invoices: { id: number; number: string; customer_name: string; total: string }[];
  bills: { id: number; number: string; vendor_name: string; amount: string }[];
};

export function ReportsPage() {
  const [accountId, setAccountId] = useState("");
  const profit = useQuery({ queryKey: ["profit"], queryFn: async () => (await api.get<Profit>("/reports/profit-loss/")).data });
  const sheet = useQuery({ queryKey: ["sheet"], queryFn: async () => (await api.get<Sheet>("/reports/balance-sheet/")).data });
  const budget = useQuery({ queryKey: ["budget-compare"], queryFn: async () => (await api.get<Compare>("/reports/budget/")).data });
  const trial = useQuery({ queryKey: ["trial-balance"], queryFn: async () => (await api.get<Trial>("/reports/trial-balance/")).data });
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: async () => (await api.get<{ results: Account[] }>("/accounts/")).data.results });
  const ledger = useQuery({
    queryKey: ["account-ledger", accountId],
    enabled: accountId !== "",
    queryFn: async () => (await api.get<Ledger>("/reports/account-ledger/", { params: { account: accountId } })).data,
  });
  const outlook = useQuery({ queryKey: ["cash-outlook"], queryFn: async () => (await api.get<Outlook>("/reports/cash-outlook/")).data });

  return (
    <>
      <div className="top"><h2>Reports</h2></div>
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <section className="card">
          <p className="tag">Profit and loss</p>
          <p>Net {money(profit.data?.net ?? 0)}</p>
          <table>
            <tbody>{(profit.data?.rows ?? []).map((row) => <tr key={row.code}><td>{row.code} {row.name}</td><td className="num">{money(row.balance)}</td></tr>)}</tbody>
          </table>
        </section>
        <section className="card">
          <p className="tag">Balance sheet {sheet.data?.balanced ? "· balanced" : ""}</p>
          {Object.entries(sheet.data?.sections ?? {}).map(([name, rows]) => (
            <div key={name}>
              <strong>{name}</strong>
              {rows.map((row) => <div key={row.code} className="row" style={{ justifyContent: "space-between" }}><span>{row.code} {row.name}</span><span>{money(row.balance)}</span></div>)}
            </div>
          ))}
          <p>Current earnings {money(sheet.data?.current_earnings ?? 0)}</p>
        </section>
      </div>
      <section className="card" style={{ marginTop: 14 }}>
        <p className="tag">Budget against actual</p>
        <table>
          <thead><tr><th>Account</th><th className="num">Budget</th><th className="num">Actual</th><th className="num">Variance</th></tr></thead>
          <tbody>
            {(budget.data?.lines ?? []).map((line) => (
              <tr key={line.code}><td>{line.code} {line.name}</td><td className="num">{money(line.budget)}</td><td className="num">{money(line.actual)}</td><td className="num">{money(line.variance)}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="card" style={{ marginTop: 14 }}>
        <p className="tag">Trial balance {trial.data?.balanced ? "· balanced" : ""}</p>
        <table>
          <thead><tr><th>Account</th><th className="num">Debit</th><th className="num">Credit</th></tr></thead>
          <tbody>
            {(trial.data?.rows ?? []).filter((row) => Number(row.debit) !== 0 || Number(row.credit) !== 0).map((row) => (
              <tr key={row.code}><td>{row.code} {row.name}</td><td className="num">{money(row.debit)}</td><td className="num">{money(row.credit)}</td></tr>
            ))}
            <tr><td>Total</td><td className="num">{money(trial.data?.debit_total ?? 0)}</td><td className="num">{money(trial.data?.credit_total ?? 0)}</td></tr>
          </tbody>
        </table>
      </section>
      <section className="card" style={{ marginTop: 14 }}>
        <p className="tag">Account ledger</p>
        <select value={accountId} onChange={(event) => setAccountId(event.target.value)}>
          <option value="">Choose an account</option>
          {(accounts.data ?? []).map((account) => <option key={account.id} value={account.id}>{account.code} {account.name}</option>)}
        </select>
        {ledger.data && (
          <>
            <p>{ledger.data.code} {ledger.data.name} · opening {money(ledger.data.opening_balance)} · closing {money(ledger.data.closing_balance)}</p>
            <table>
              <thead><tr><th>Date</th><th>Memo</th><th className="num">Debit</th><th className="num">Credit</th><th className="num">Balance</th></tr></thead>
              <tbody>
                {ledger.data.lines.map((line) => (
                  <tr key={line.line_id}>
                    <td>{prettyDate(line.entry_date)}</td>
                    <td>{line.memo}</td>
                    <td className="num">{money(line.debit)}</td>
                    <td className="num">{money(line.credit)}</td>
                    <td className="num">{money(line.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </section>
      <section className="card" style={{ marginTop: 14 }}>
        <p className="tag">Cash outlook</p>
        <div className="grid stats">
          <div><span className="tag">Open invoices</span><b>{money(outlook.data?.open_invoices ?? 0)}</b></div>
          <div><span className="tag">Open bills</span><b>{money(outlook.data?.open_bills ?? 0)}</b></div>
          <div><span className="tag">Net</span><b className={Number(outlook.data?.net) >= 0 ? "good" : "bad"}>{money(outlook.data?.net ?? 0)}</b></div>
        </div>
        <table>
          <tbody>
            {(outlook.data?.invoices ?? []).map((invoice) => <tr key={invoice.id}><td>{invoice.number} {invoice.customer_name}</td><td className="num">{money(invoice.total)}</td></tr>)}
            {(outlook.data?.bills ?? []).map((bill) => <tr key={bill.id}><td>{bill.number} {bill.vendor_name}</td><td className="num">{money(bill.amount)}</td></tr>)}
          </tbody>
        </table>
      </section>
    </>
  );
}
