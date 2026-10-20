import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Account, api } from "../api/client";

const helper = createColumnHelper<Account>();
const columns = [
  helper.accessor("code", { header: "Code" }),
  helper.accessor("name", { header: "Name" }),
  helper.accessor("type", { header: "Type" }),
];

export function AccountsPage() {
  const queryClient = useQueryClient();
  const accounts = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await api.get<{ results: Account[] }>("/accounts/")).data.results,
  });
  const table = useReactTable({ data: accounts.data ?? [], columns, getCoreRowModel: getCoreRowModel() });
  const create = useMutation({
    mutationFn: async (body: { code: string; name: string; type: string }) => api.post("/accounts/", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });
  const [error, setError] = useState("");

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError("");
    create.mutate(
      { code: String(data.get("code")), name: String(data.get("name")), type: String(data.get("type")) },
      { onSuccess: () => event.currentTarget.reset(), onError: () => setError("That code is already in the chart.") },
    );
  }

  return (
    <>
      <div className="top"><h2>Chart of accounts</h2></div>
      <form className="card row" onSubmit={onSubmit} style={{ marginBottom: 14 }}>
        <input name="code" placeholder="Code" required />
        <input name="name" placeholder="Name" required />
        <select name="type">
          <option value="asset">Asset</option>
          <option value="liability">Liability</option>
          <option value="equity">Equity</option>
          <option value="income">Income</option>
          <option value="expense">Expense</option>
        </select>
        <button className="btn" type="submit">Add account</button>
        {error && <span className="error">{error}</span>}
      </form>
      <div className="card">
        <table>
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>{group.headers.map((header) => <th key={header.id}>{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>{row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
