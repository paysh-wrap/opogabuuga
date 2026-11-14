import { lazy } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import Layout from "../components/Layout";
import Login from "../pages/Login";
import { LiveProvider } from "./live";

// Pages load on demand (one small file each) instead of one 650 kB bundle; Login stays in the main bundle so the
// first screen appears at once. The Suspense fallback lives in Layout, around the page area only.
const Connections = lazy(() => import("../pages/Connections"));
const NotFound = lazy(() => import("../pages/NotFound"));
const Automation = lazy(() => import("../pages/Automation"));
const Risk = lazy(() => import("../pages/Risk"));
const Dashboard = lazy(() => import("../pages/Dashboard"));
const Today = lazy(() => import("../pages/Today"));
const Payouts = lazy(() => import("../pages/Payouts"));
const Strategy = lazy(() => import("../pages/Strategy"));
const Backtest = lazy(() => import("../pages/Backtest"));
const Replay = lazy(() => import("../pages/Replay"));
const OrderFlow = lazy(() => import("../pages/OrderFlow"));
const Signals = lazy(() => import("../pages/Signals"));
const Journal = lazy(() => import("../pages/Journal"));
const Trade = lazy(() => import("../pages/Trade"));
const Accounts = lazy(() => import("../pages/Accounts"));
const Settings = lazy(() => import("../pages/Settings"));
const LabPage = lazy(() => import("../pages/Lab"));

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
        <Route path="/signals" element={<Signals />} />
        <Route path="/journal" element={<Journal />} />
        <Route path="/payouts" element={<Payouts />} />
        <Route path="/strategy" element={<Strategy />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/replay" element={<Replay />} />
        <Route path="/orderflow" element={<OrderFlow />} />
        <Route path="/lab" element={<LabPage />} />
        <Route path="/connections" element={<Connections />} />
        <Route path="/automation" element={<Automation />} />
        <Route path="/risk" element={<Risk />} />
        <Route path="/trade" element={<Trade />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
