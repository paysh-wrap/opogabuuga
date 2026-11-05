import { Link } from "react-router-dom";
import { usePageTitle } from "../components/usePageTitle";

export default function NotFound() {
  usePageTitle("Not found");
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold text-gold">Page not found</h1>
      <Link to="/connections" className="mt-4 inline-block">Go to Connections</Link>
    </div>
  );
}
