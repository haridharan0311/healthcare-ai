import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard        from './pages/Dashboard';
import ReportsPage      from './pages/ReportsPage';
import AdminLayout      from './pages/AdminLayout';
import ModelList        from './pages/ModelList';
import ModelForm        from './pages/ModelForm';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"              element={<Dashboard />} />
        <Route path="/reports"       element={<ReportsPage />} />
        <Route path="/admin-panel"   element={<AdminLayout />}>
          <Route index               element={<Navigate to="/admin-panel/clinics" replace />} />
          <Route path=":model"       element={<ModelList />} />
          <Route path=":model/:id"   element={<ModelForm />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}