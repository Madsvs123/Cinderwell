import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { money } from "../lib/format";

type Profit = { income: string; expense: string; net: string; rows: { code: string; name: string; balance: string }[] };
type Sheet = { balanced: boolean; current_earnings: string; totals: Record<string, string>; sections: Record<string, { code: string; name: string; balance: string }[]> };
type Compare = { lines: { code: string; name: string; budget: string; actual: string; variance: string }[] };

export function ReportsPage() {
  const profit = useQuery({ queryKey: ["profit"], queryFn: async () => (await api.get<Profit>("/reports/profit-loss/")).data });
  const sheet = useQuery({ queryKey: ["sheet"], queryFn: async () => (await api.get<Sheet>("/reports/balance-sheet/")).data });
  const budget = useQuery({ queryKey: ["budget-compare"], queryFn: async () => (await api.get<Compare>("/reports/budget/")).data });

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
    </>
  );
}
