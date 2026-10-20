import { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Account, Journal, api } from "../api/client";
import { money, prettyDate } from "../lib/format";

export function JournalPage() {
  const queryClient = useQueryClient();
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: async () => (await api.get<{ results: Account[] }>("/accounts/")).data.results });
  const journals = useQuery({ queryKey: ["journals"], queryFn: async () => (await api.get<{ results: Journal[] }>("/journals/")).data.results });
  const post = useMutation({
    mutationFn: async (body: unknown) => api.post("/journals/", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journals"] });
      queryClient.invalidateQueries({ queryKey: ["profit"] });
      queryClient.invalidateQueries({ queryKey: ["sheet"] });
    },
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const debit = String(data.get("amount"));
    post.mutate({
      entry_date: data.get("entry_date"),
      memo: data.get("memo"),
      lines: [
        { account: Number(data.get("debit_account")), debit, credit: "0" },
        { account: Number(data.get("credit_account")), debit: "0", credit: debit },
      ],
    });
    event.currentTarget.reset();
  }

  return (
    <>
      <div className="top"><h2>Journal</h2></div>
      <form className="card row" onSubmit={onSubmit} style={{ marginBottom: 14 }}>
        <input name="entry_date" type="date" required />
        <input name="memo" placeholder="Memo" />
        <select name="debit_account" required>{(accounts.data ?? []).map((account) => <option key={account.id} value={account.id}>{account.code} {account.name}</option>)}</select>
        <select name="credit_account" required>{(accounts.data ?? []).map((account) => <option key={account.id} value={account.id}>{account.code} {account.name}</option>)}</select>
        <input name="amount" placeholder="Amount" required />
        <button className="btn" type="submit">Post entry</button>
      </form>
      <div className="card">
        <table>
          <thead><tr><th>Date</th><th>Memo</th><th>Lines</th><th className="num">Amount</th></tr></thead>
          <tbody>
            {(journals.data ?? []).map((entry) => (
              <tr key={entry.id}>
                <td>{prettyDate(entry.entry_date)}</td>
                <td>{entry.memo || entry.source_type || "Manual"}</td>
                <td>{entry.lines.map((line) => line.account_code).join(", ")}</td>
                <td className="num">{money(entry.lines.reduce((sum, line) => sum + Number(line.debit), 0))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
