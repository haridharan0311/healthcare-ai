import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard        from './pages/Dashboard';
import ReportsPage      from './pages/ReportsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"              element={<Dashboard />} />
        <Route path="/reports"       element={<ReportsPage />} />
      </Routes>
    </BrowserRouter>
  );
}