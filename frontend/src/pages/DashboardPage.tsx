import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { money } from "../lib/format";

type SearchHit = {
  journals: { id: number; memo: string; entry_date: string }[];
  invoices: { id: number; number: string; customer_name: string }[];
  bills: { id: number; number: string; vendor_name: string }[];
};

export function DashboardPage() {
  const [query, setQuery] = useState("");
  const profit = useQuery({
    queryKey: ["profit"],
    queryFn: async () => (await api.get("/reports/profit-loss/")).data,
  });
  const sheet = useQuery({
    queryKey: ["sheet"],
    queryFn: async () => (await api.get("/reports/balance-sheet/")).data,
  });
  const search = useQuery({
    queryKey: ["search", query],
    enabled: query.trim().length > 0,
    queryFn: async () => (await api.get<SearchHit>("/search/", { params: { q: query } })).data,
  });
  const chart = (profit.data?.rows ?? []).map((row: { name: string; type: string; balance: string }) => ({
    name: row.name,
    amount: row.type === "expense" ? -Number(row.balance) : Number(row.balance),
  }));

  return (
    <>
      <div className="top">
        <h2>Desk</h2>
        <form onSubmit={(event: FormEvent) => event.preventDefault()}>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search memos, customers, vendors" />
        </form>
      </div>
      {query.trim() && (
        <section className="card" style={{ marginBottom: 14 }}>
          <p className="tag">Search</p>
          <ul>
            {(search.data?.journals ?? []).map((entry) => <li key={`j-${entry.id}`}>Journal · {entry.memo}</li>)}
            {(search.data?.invoices ?? []).map((invoice) => <li key={`i-${invoice.id}`}>{invoice.number} · {invoice.customer_name}</li>)}
            {(search.data?.bills ?? []).map((bill) => <li key={`b-${bill.id}`}>{bill.number} · {bill.vendor_name}</li>)}
          </ul>
        </section>
      )}
      <div className="grid stats">
        <div className="card"><span className="tag">Income</span><b>{money(profit.data?.income ?? 0)}</b></div>
        <div className="card"><span className="tag">Expense</span><b>{money(profit.data?.expense ?? 0)}</b></div>
        <div className="card"><span className="tag">Net</span><b className={Number(profit.data?.net) >= 0 ? "good" : "bad"}>{money(profit.data?.net ?? 0)}</b></div>
      </div>
      <section className="card">
        <p className="tag">Year to date</p>
        <div style={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart}>
              <XAxis dataKey="name" hide />
              <YAxis />
              <Tooltip />
              <Bar dataKey="amount" fill="#8a5a2b" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p>Cash and other assets stand at {money(sheet.data?.totals?.asset ?? 0)}. The sheet is {sheet.data?.balanced ? "balanced" : "still loading"}.</p>
      </section>
    </>
  );
}
