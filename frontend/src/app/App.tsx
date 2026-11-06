import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import Layout from "../components/Layout";
import Login from "../pages/Login";
import Connections from "../pages/Connections";
import NotFound from "../pages/NotFound";
import Automation from "../pages/Automation";
import Risk from "../pages/Risk";
import Dashboard from "../pages/Dashboard";
import Today from "../pages/Today";
import Payouts from "../pages/Payouts";
import Strategy from "../pages/Strategy";
import Backtest from "../pages/Backtest";
import LabPage from "../pages/Lab";
import { LiveProvider } from "./live";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api<{ username: string; csrf: string }>("/api/auth/me"),
    retry: false,
  });
}

function RequireAuth({ children }: { children: JSX.Element }) {
  const me = useMe();
  const loc = useLocation();
  if (me.isLoading) return <p className="p-6" role="status">Loading…</p>;
  if (me.error instanceof ApiError && me.error.status === 401) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  if (me.error) return <p className="p-6" role="alert">Cannot reach the Paytience server: {String(me.error.message)}</p>;
  return <LiveProvider>{children}</LiveProvider>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Navigate to="/today" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/today" element={<Today />} />
        <Route path="/payouts" element={<Payouts />} />
        <Route path="/strategy" element={<Strategy />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/lab" element={<LabPage />} />
        <Route path="/connections" element={<Connections />} />
        <Route path="/automation" element={<Automation />} />
        <Route path="/risk" element={<Risk />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
