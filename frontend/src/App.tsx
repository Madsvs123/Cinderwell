import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { useAuth } from "./store/auth";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import { DashboardPage } from "./pages/DashboardPage";
import { AccountsPage } from "./pages/AccountsPage";
import { JournalPage } from "./pages/JournalPage";
import { BillsPage, InvoicesPage } from "./pages/DocumentsPage";
import { ReportsPage } from "./pages/ReportsPage";

function Private({ children }: { children: ReactElement }) {
  const access = useAuth((state) => state.access);
  if (!access) return <Navigate to="/" replace />;
  return children;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/app" element={<Private><Shell /></Private>}>
        <Route index element={<DashboardPage />} />
        <Route path="accounts" element={<AccountsPage />} />
        <Route path="journal" element={<JournalPage />} />
        <Route path="invoices" element={<InvoicesPage />} />
        <Route path="bills" element={<BillsPage />} />
        <Route path="reports" element={<ReportsPage />} />
      </Route>
    </Routes>
  );
}
