import { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Account, AuditEvent, FiscalPeriod, Journal, RecurringJournal, api } from "../api/client";
import { money, prettyDate } from "../lib/format";

export function JournalPage() {
  const queryClient = useQueryClient();
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: async () => (await api.get<{ results: Account[] }>("/accounts/")).data.results });
  const journals = useQuery({ queryKey: ["journals"], queryFn: async () => (await api.get<{ results: Journal[] }>("/journals/")).data.results });
  const periods = useQuery({ queryKey: ["periods"], queryFn: async () => (await api.get<{ results: FiscalPeriod[] }>("/periods/")).data.results });
  const recurring = useQuery({ queryKey: ["recurring"], queryFn: async () => (await api.get<{ results: RecurringJournal[] }>("/recurring/")).data.results });
  const audit = useQuery({ queryKey: ["audit"], queryFn: async () => (await api.get<{ results: AuditEvent[] }>("/audit/")).data.results });
  const refreshBooks = () => {
    queryClient.invalidateQueries({ queryKey: ["journals"] });
    queryClient.invalidateQueries({ queryKey: ["profit"] });
    queryClient.invalidateQueries({ queryKey: ["sheet"] });
    queryClient.invalidateQueries({ queryKey: ["audit"] });
  };
  const post = useMutation({
    mutationFn: async (body: unknown) => api.post("/journals/", body),
    onSuccess: refreshBooks,
  });
  const reverse = useMutation({
    mutationFn: async (id: number) => api.post(`/journals/${id}/reverse/`),
    onSuccess: refreshBooks,
  });
  const savePeriod = useMutation({
    mutationFn: async (body: unknown) => api.post("/periods/", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["periods"] }),
  });
  const lockPeriod = useMutation({
    mutationFn: async (id: number) => api.post(`/periods/${id}/lock/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["periods"] }),
  });
  const importCsv = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api.post("/journals/import-csv/", body);
    },
    onSuccess: refreshBooks,
  });
  const saveRecurring = useMutation({
    mutationFn: async (body: unknown) => api.post("/recurring/", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recurring"] }),
  });
  const generateRecurring = useMutation({
    mutationFn: async (id: number) => api.post(`/recurring/${id}/generate/`),
    onSuccess: () => {
      refreshBooks();
      queryClient.invalidateQueries({ queryKey: ["recurring"] });
    },
  });
  const stopRecurring = useMutation({
    mutationFn: async (id: number) => api.patch(`/recurring/${id}/`, { active: false }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recurring"] }),
  });
  const reversedIds = new Set(
    (journals.data ?? []).filter((entry) => entry.source_type === "reversal").map((entry) => entry.source_id),
  );

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
      <form className="card row" style={{ marginBottom: 14 }} onSubmit={(event) => {
        event.preventDefault();
        const file = new FormData(event.currentTarget).get("file");
        if (file instanceof File && file.size) importCsv.mutate(file);
      }}>
        <input name="file" type="file" accept=".csv,text/csv" required />
        <button className="btn quiet" type="submit">Import CSV</button>
      </form>
      <div className="card">
        <table>
          <thead><tr><th>Date</th><th>Memo</th><th>Lines</th><th className="num">Amount</th><th></th></tr></thead>
          <tbody>
            {(journals.data ?? []).map((entry) => (
              <tr key={entry.id}>
                <td>{prettyDate(entry.entry_date)}</td>
                <td>{entry.memo || entry.source_type || "Manual"}</td>
                <td>{entry.lines.map((line) => line.account_code).join(", ")}</td>
                <td className="num">{money(entry.lines.reduce((sum, line) => sum + Number(line.debit), 0))}</td>
                <td>
                  {entry.status === "posted" && !reversedIds.has(String(entry.id)) && (
                    <button className="btn quiet" type="button" onClick={() => reverse.mutate(entry.id)}>Reverse</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <section className="card" style={{ marginTop: 14 }}>
        <p className="tag">Fiscal periods</p>
        <form className="row" style={{ marginBottom: 12 }} onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          savePeriod.mutate({ name: data.get("name"), start_date: data.get("start_date"), end_date: data.get("end_date") });
          event.currentTarget.reset();
        }}>
          <input name="name" placeholder="March 2026" required />
          <input name="start_date" type="date" required />
          <input name="end_date" type="date" required />
          <button className="btn quiet" type="submit">Add period</button>
        </form>
        <table>
          <thead><tr><th>Name</th><th>Start</th><th>End</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {(periods.data ?? []).map((period) => (
              <tr key={period.id}>
                <td>{period.name}</td>
                <td>{prettyDate(period.start_date)}</td>
                <td>{prettyDate(period.end_date)}</td>
                <td>{period.locked ? "Locked" : "Open"}</td>
                <td>{!period.locked && <button className="btn quiet" type="button" onClick={() => lockPeriod.mutate(period.id)}>Lock</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="card" style={{ marginTop: 14 }}>
        <p className="tag">Recurring journals</p>
        <form className="row" style={{ marginBottom: 12 }} onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          const amount = String(data.get("amount"));
          saveRecurring.mutate({
            memo: data.get("memo"),
            next_date: data.get("next_date"),
            interval_months: Number(data.get("interval_months") || 1),
            lines: [
              { account: Number(data.get("debit_account")), debit: amount, credit: "0" },
              { account: Number(data.get("credit_account")), debit: "0", credit: amount },
            ],
          });
          event.currentTarget.reset();
        }}>
          <input name="memo" placeholder="Monthly rent" required />
          <input name="next_date" type="date" required />
          <input name="interval_months" type="number" min={1} defaultValue={1} />
          <select name="debit_account" required>{(accounts.data ?? []).map((account) => <option key={`rd-${account.id}`} value={account.id}>{account.code}</option>)}</select>
          <select name="credit_account" required>{(accounts.data ?? []).map((account) => <option key={`rc-${account.id}`} value={account.id}>{account.code}</option>)}</select>
          <input name="amount" placeholder="Amount" required />
          <button className="btn quiet" type="submit">Save template</button>
        </form>
        <table>
          <thead><tr><th>Memo</th><th>Next</th><th>Every</th><th></th></tr></thead>
          <tbody>
            {(recurring.data ?? []).filter((template) => template.active).map((template) => (
              <tr key={template.id}>
                <td>{template.memo}</td>
                <td>{prettyDate(template.next_date)}</td>
                <td>{template.interval_months} mo</td>
                <td>
                  <button className="btn quiet" type="button" onClick={() => generateRecurring.mutate(template.id)}>Post next</button>
                  <button className="btn quiet" type="button" onClick={() => stopRecurring.mutate(template.id)}>Stop</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="card" style={{ marginTop: 14 }}>
        <p className="tag">Audit log</p>
        <table>
          <thead><tr><th>When</th><th>Action</th><th>Memo</th></tr></thead>
          <tbody>
            {(audit.data ?? []).map((event) => (
              <tr key={event.id}>
                <td>{prettyDate(event.entry_date)}</td>
                <td>{event.action}</td>
                <td>{event.detail || event.journal_memo}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
