import { NavLink, Outlet } from "react-router-dom";
import Header from "./Header";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/today", label: "Today" },
  { to: "/strategy", label: "Strategy" },
  { to: "/backtest", label: "Backtest" },
  { to: "/lab", label: "Lab" },
  { to: "/automation", label: "Automation" },
  { to: "/risk", label: "Risk" },
  { to: "/payouts", label: "Payouts" },
  { to: "/connections", label: "Connections" },
];

export default function Layout() {
  return (
    <div className="min-h-screen">
      <Header />
      <nav aria-label="Main" className="border-b border-border bg-card/40 px-4">
        <ul className="mx-auto flex max-w-6xl gap-4 overflow-x-auto py-2 text-sm">
          {NAV.map((n) => (
            <li key={n.to}>
              <NavLink to={n.to} className={({ isActive }) => (isActive ? "font-semibold text-gold" : "text-blue")}>
                {n.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
