import { NavLink } from "react-router-dom";

/** D93: phone-only bottom dock (mission control look). The full scrolling nav strip stays above for every page. */
const DOCK = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/today", label: "Today" },
  { to: "/strategy", label: "Strategy" },
  { to: "/trade", label: "Trade" },
  { to: "/automation", label: "Safety" },
];

export default function MobileDock() {
  return (
    <nav aria-label="Quick" className="mission-dock">
      {DOCK.map((d) => (
        <NavLink key={d.to} to={d.to} className={({ isActive }) => (isActive ? "on" : "")}>{d.label}</NavLink>
      ))}
    </nav>
  );
}
