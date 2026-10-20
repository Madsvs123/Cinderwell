import { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Account, Bill, Budget, Invoice, api } from "../api/client";
import { money, prettyDate } from "../lib/format";

export function InvoicesPage() {
  const queryClient = useQueryClient();
  const invoices = useQuery({ queryKey: ["invoices"], queryFn: async () => (await api.get<{ results: Invoice[] }>("/invoices/")).data.results });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["invoices"] });
    queryClient.invalidateQueries({ queryKey: ["journals"] });
    queryClient.invalidateQueries({ queryKey: ["profit"] });
    queryClient.invalidateQueries({ queryKey: ["sheet"] });
  };
  const create = useMutation({ mutationFn: (body: unknown) => api.post("/invoices/", body), onSuccess: refresh });
  const act = useMutation({ mutationFn: (url: string) => api.post(url), onSuccess: refresh });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    create.mutate({
      customer_name: data.get("customer_name"),
      issue_date: data.get("issue_date"),
      due_date: data.get("due_date"),
      tax_rate: data.get("tax_rate") || "0",
      lines: [{ description: data.get("description"), quantity: data.get("quantity"), unit_price: data.get("unit_price") }],
    });
    event.currentTarget.reset();
  }

  return (
    <>
      <div className="top"><h2>Invoices</h2></div>
      <form className="card row" onSubmit={onSubmit} style={{ marginBottom: 14 }}>
        <input name="customer_name" placeholder="Customer" required />
        <input name="description" placeholder="Work" required />
        <input name="quantity" placeholder="Qty" required />
        <input name="unit_price" placeholder="Price" required />
        <input name="tax_rate" placeholder="Tax %" />
        <input name="issue_date" type="date" required />
        <input name="due_date" type="date" required />
        <button className="btn">Save draft</button>
      </form>
      <div className="card">
        <table>
          <thead><tr><th>Number</th><th>Customer</th><th>Due</th><th>Status</th><th className="num">Total</th><th></th></tr></thead>
          <tbody>
            {(invoices.data ?? []).map((invoice) => (
              <tr key={invoice.id}>
                <td>{invoice.number}</td>
                <td>{invoice.customer_name}</td>
                <td>{prettyDate(invoice.due_date)}</td>
                <td>{invoice.status}</td>
                <td className="num">{money(invoice.total)}</td>
                <td>
                  {invoice.status === "draft" && <button className="btn quiet" onClick={() => act.mutate(`/invoices/${invoice.id}/issue/`)}>Issue</button>}
                  {invoice.status === "issued" && <button className="btn quiet" onClick={() => act.mutate(`/invoices/${invoice.id}/pay/`)}>Mark paid</button>}
                  <button className="btn quiet" type="button" onClick={async () => {
                    const response = await api.get(`/invoices/${invoice.id}/preview/`, { responseType: "text" });
                    const url = URL.createObjectURL(new Blob([response.data], { type: "text/html" }));
                    window.open(url, "_blank");
                  }}>Preview</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function BillsPage() {
  const queryClient = useQueryClient();
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: async () => (await api.get<{ results: Account[] }>("/accounts/")).data.results });
  const bills = useQuery({ queryKey: ["bills"], queryFn: async () => (await api.get<{ results: Bill[] }>("/bills/")).data.results });
  const budgets = useQuery({ queryKey: ["budgets"], queryFn: async () => (await api.get<{ results: Budget[] }>("/budgets/")).data.results });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["bills"] });
    queryClient.invalidateQueries({ queryKey: ["journals"] });
    queryClient.invalidateQueries({ queryKey: ["sheet"] });
    queryClient.invalidateQueries({ queryKey: ["profit"] });
  };
  const createBill = useMutation({ mutationFn: (body: unknown) => api.post("/bills/", body), onSuccess: refresh });
  const pay = useMutation({ mutationFn: (id: number) => api.post(`/bills/${id}/pay/`), onSuccess: refresh });
  const createBudget = useMutation({
    mutationFn: (body: unknown) => api.post("/budgets/", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["budgets"] }),
  });
  const copyBudget = useMutation({
    mutationFn: (body: unknown) => api.post("/budgets/copy/", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["budgets"] }),
  });
  const expenses = (accounts.data ?? []).filter((account) => account.type === "expense" || account.type === "income");

  return (
    <>
      <div className="top"><h2>Bills and budgets</h2></div>
      <form className="card row" style={{ marginBottom: 14 }} onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        createBill.mutate({
          vendor_name: data.get("vendor_name"),
          bill_date: data.get("bill_date"),
          due_date: data.get("due_date"),
          amount: data.get("amount"),
          expense_account: Number(data.get("expense_account")),
          memo: data.get("memo"),
        });
        event.currentTarget.reset();
      }}>
        <input name="vendor_name" placeholder="Vendor" required />
        <input name="amount" placeholder="Amount" required />
        <select name="expense_account" required>{expenses.filter((account) => account.type === "expense").map((account) => <option key={account.id} value={account.id}>{account.code} {account.name}</option>)}</select>
        <input name="bill_date" type="date" required />
        <input name="due_date" type="date" required />
        <input name="memo" placeholder="Memo" />
        <button className="btn">Record bill</button>
      </form>
      <div className="card" style={{ marginBottom: 14 }}>
        <table>
          <thead><tr><th>Number</th><th>Vendor</th><th>Due</th><th>Status</th><th className="num">Amount</th><th></th></tr></thead>
          <tbody>
            {(bills.data ?? []).map((bill) => (
              <tr key={bill.id}>
                <td>{bill.number}</td><td>{bill.vendor_name}</td><td>{prettyDate(bill.due_date)}</td><td>{bill.status}</td>
                <td className="num">{money(bill.amount)}</td>
                <td>{bill.status === "open" && <button className="btn quiet" onClick={() => pay.mutate(bill.id)}>Pay</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <form className="card row" onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        createBudget.mutate({ account: Number(data.get("account")), year: Number(data.get("year")), month: Number(data.get("month")), amount: data.get("amount") });
      }}>
        <select name="account">{expenses.map((account) => <option key={account.id} value={account.id}>{account.code} {account.name}</option>)}</select>
        <input name="year" type="number" defaultValue={new Date().getFullYear()} />
        <input name="month" type="number" min={1} max={12} defaultValue={new Date().getMonth() + 1} />
        <input name="amount" placeholder="Budget" required />
        <button className="btn quiet">Save budget</button>
      </form>
      <form className="card row" style={{ marginTop: 14 }} onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        copyBudget.mutate({ year: Number(data.get("year")), month: Number(data.get("month")) });
      }}>
        <input name="year" type="number" defaultValue={new Date().getFullYear()} />
        <input name="month" type="number" min={1} max={12} defaultValue={new Date().getMonth() + 1} />
        <button className="btn quiet" type="submit">Copy into next month</button>
      </form>
      <ul>{(budgets.data ?? []).map((line) => <li key={line.id}>{line.account_code} {line.year}-{line.month}: {money(line.amount)}</li>)}</ul>
    </>
  );
}
