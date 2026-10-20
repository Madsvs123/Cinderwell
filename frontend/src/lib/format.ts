import { format, parseISO } from "date-fns";
import clsx from "clsx";

export function money(value: string | number) {
  const amount = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount || 0);
}

export function prettyDate(value: string) {
  return format(parseISO(value), "d MMM yyyy");
}

export function cx(...parts: Array<string | false | undefined>) {
  return clsx(parts);
}
