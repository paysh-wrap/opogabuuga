import { NavLink, Outlet } from "react-router-dom";
import Header from "./Header";
import SafetyBanners from "./SafetyBanners";
import { UpdateBanner } from "./UpdatePanel";
import MobileDock from "./MobileDock";
import { BuildFooter, StaleUiBanner } from "./BuildGuard";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/today", label: "Today" },
  { to: "/signals", label: "Signals" },
  { to: "/trade", label: "Trade" },
  { to: "/accounts", label: "Accounts" },
  { to: "/strategy", label: "Strategy" },
  { to: "/backtest", label: "Backtest" },
  { to: "/lab", label: "Lab" },
  { to: "/replay", label: "Replay" },
  { to: "/automation", label: "Automation" },
  { to: "/risk", label: "Risk" },
  { to: "/payouts", label: "Payouts" },
  { to: "/connections", label: "Connections" },
  { to: "/journal", label: "Journal & Logs" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  return (
    <div className="mission min-h-screen">
      <StaleUiBanner />
      <div className="app-chrome">
      <Header />
      <nav aria-label="Main" className="border-b border-border bg-card/40 px-4">
        <ul className="nav-strip mx-auto flex max-w-6xl py-2 text-sm">
          {NAV.map((n) => (
            <li key={n.to} className="shrink-0 whitespace-nowrap">
              <NavLink to={n.to} className={({ isActive }) => (isActive ? "font-semibold text-gold" : "text-blue")}>
                {n.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      </div>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <SafetyBanners />
        <UpdateBanner />
        <Outlet />
      </main>
      <BuildFooter />
      <MobileDock />
    </div>
  );
}
