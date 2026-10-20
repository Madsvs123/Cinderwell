import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { money } from "../lib/format";

export function DashboardPage() {
  const profit = useQuery({
    queryKey: ["profit"],
    queryFn: async () => (await api.get("/reports/profit-loss/")).data,
  });
  const sheet = useQuery({
    queryKey: ["sheet"],
    queryFn: async () => (await api.get("/reports/balance-sheet/")).data,
  });
  const chart = (profit.data?.rows ?? []).map((row: { name: string; type: string; balance: string }) => ({
    name: row.name,
    amount: row.type === "expense" ? -Number(row.balance) : Number(row.balance),
  }));

  return (
    <>
      <div className="top"><h2>Desk</h2></div>
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
