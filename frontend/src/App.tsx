import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { FeedPage } from "./pages/FeedPage";
import { HomePage } from "./pages/HomePage";
import { InsightPage } from "./pages/InsightPage";
import { LoginPage } from "./pages/LoginPage";
import { useSession } from "./session";

export default function App() {
  const { me, loading } = useSession();
  if (loading) return <div className="p-8 text-slate-500">Загрузка…</div>;
  if (!me) return <LoginPage />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="news" element={<FeedPage />} />
        <Route path="news/:clientId/:eventId" element={<InsightPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
