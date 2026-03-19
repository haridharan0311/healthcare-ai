import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AdminLayout  from './admin/AdminLayout';
import ModelList    from './admin/ModelList';
import ModelForm    from './admin/ModelForm';
import TrendChart   from './components/TrendChart';
import SpikeAlerts  from './components/SpikeAlerts';
import RestockTable from './components/RestockTable';
import ExportButton from './components/ExportButton';

function Dashboard() {
  return (
    <div style={{
      minHeight: '100vh', background: '#f7f7f5',
      padding: '32px 24px', fontFamily: 'system-ui, sans-serif'
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 500 }}>Healthcare analytics</h1>
            <p style={{ margin: '4px 0 0', color: '#888', fontSize: 14 }}>
              Disease trends · Spike detection · Medicine restock
            </p>
          </div>
          <a href="/admin-panel" style={{
            padding: '8px 18px', borderRadius: 8, border: '1px solid #ddd',
            background: '#fff', fontSize: 13, color: '#444',
            textDecoration: 'none', fontWeight: 500
          }}>
            Admin panel →
          </a>
        </div>
        <ExportButton />
        <SpikeAlerts />
        <TrendChart />
        <RestockTable />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/admin-panel" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin-panel/clinics" replace />} />
          <Route path=":model"        element={<ModelList />} />
          <Route path=":model/:id"    element={<ModelForm />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}