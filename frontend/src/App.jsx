import { Link, Route, Routes } from "react-router-dom";
import TickerDetail from "./pages/TickerDetail";
import TickerList from "./pages/TickerList";

function NotFound() {
  return (
    <div className="card">
      <div className="state">
        <p>We couldn't find that page.</p>
        <Link to="/">Go back to the dashboard</Link>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <>
      <header className="app-header">
        <Link to="/">📈 Stock Dashboard</Link>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<TickerList />} />
          <Route path="/ticker/:symbol" element={<TickerDetail />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  );
}