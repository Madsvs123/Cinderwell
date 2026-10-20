import axios from "axios";
import { useAuth } from "../store/auth";

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = useAuth.getState().access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export type Account = { id: number; code: string; name: string; type: string; is_active: boolean };
export type JournalLine = { id: number; account: number; account_code: string; account_name: string; description: string; debit: string; credit: string };
export type Journal = { id: number; entry_date: string; memo: string; status: string; source_type: string; source_id: string; lines: JournalLine[] };
export type Invoice = {
  id: number; number: string; customer_name: string; issue_date: string; due_date: string;
  status: string; tax_rate: string; subtotal: string; tax: string; total: string;
  lines: { description: string; quantity: string; unit_price: string; amount: string }[];
};
export type Bill = {
  id: number; number: string; vendor_name: string; bill_date: string; due_date: string;
  amount: string; expense_account: number; expense_account_code: string; memo: string; status: string;
};
export type Budget = { id: number; account: number; account_code: string; account_name: string; year: number; month: number; amount: string };
export type FiscalPeriod = { id: number; name: string; start_date: string; end_date: string; locked: boolean; locked_at: string | null };
export type AuditEvent = { id: number; action: string; journal: number; journal_memo: string; entry_date: string; detail: string; created_at: string };
export type RecurringJournal = {
  id: number; memo: string; next_date: string; interval_months: number; active: boolean;
  lines: { account: number; account_code: string; description: string; debit: string; credit: string }[];
};
export type Page<T> = { results: T[] };
