import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { BookOpen, LayoutDashboard, Receipt, Scale, ScrollText, Wallet } from "lucide-react";
import { useAuth } from "../store/auth";

const links = [
  ["/app", "Desk", LayoutDashboard],
  ["/app/accounts", "Accounts", BookOpen],
  ["/app/journal", "Journal", ScrollText],
  ["/app/invoices", "Invoices", Receipt],
  ["/app/bills", "Bills", Wallet],
  ["/app/reports", "Reports", Scale],
] as const;

export function Shell() {
  const auth = useAuth();
  const navigate = useNavigate();
  return (
    <div className="shell">
      <aside className="side">
        <h1>Cinderwell</h1>
        <p>{auth.organization || "Your books"}</p>
        {links.map(([to, label, Icon]) => (
          <NavLink key={to} to={to} end={to === "/app"} className={({ isActive }) => (isActive ? "active" : undefined)}>
            <Icon size={16} style={{ verticalAlign: "text-bottom", marginRight: 8 }} />
            {label}
          </NavLink>
        ))}
        <button className="linkish" onClick={() => { auth.clear(); navigate("/"); }}>Sign out</button>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
