import { useState } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';

const MODELS = [
  { key: 'clinics',            label: 'Clinics',             icon: '🏥' },
  { key: 'doctors',            label: 'Doctors',             icon: '👨‍⚕️' },
  { key: 'patients',           label: 'Patients',            icon: '🧑' },
  { key: 'diseases',           label: 'Diseases',            icon: '🦠' },
  { key: 'appointments',       label: 'Appointments',        icon: '📅' },
  { key: 'drugs',              label: 'Drug Master',         icon: '💊' },
  { key: 'prescriptions',      label: 'Prescriptions',       icon: '📋' },
  { key: 'prescription-lines', label: 'Prescription Lines',  icon: '📝' },
];

export default function AdminLayout() {
  const navigate  = useNavigate();
  const location  = useLocation();

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>

      {/* Sidebar */}
      <div style={{
        width: 220, background: '#1e1e2e', color: '#cdd6f4',
        padding: '24px 0', flexShrink: 0, position: 'sticky',
        top: 0, height: '100vh', overflowY: 'auto'
      }}>
        <div style={{ padding: '0 20px 24px', borderBottom: '1px solid #313244' }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: '#89b4fa' }}>
            Healthcare AI
          </div>
          <div style={{ fontSize: 12, color: '#6c7086', marginTop: 2 }}>
            Admin Panel
          </div>
        </div>

        <div style={{ padding: '16px 0' }}>
          <div style={{ padding: '0 20px 8px', fontSize: 11, color: '#6c7086', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
            Models
          </div>
          {MODELS.map(m => {
            const active = location.pathname.includes(`/admin-panel/${m.key}`);
            return (
              <div
                key={m.key}
                onClick={() => navigate(`/admin-panel/${m.key}`)}
                style={{
                  padding: '10px 20px', cursor: 'pointer', fontSize: 13,
                  display: 'flex', alignItems: 'center', gap: 10,
                  background: active ? '#313244' : 'transparent',
                  color: active ? '#cdd6f4' : '#9399b2',
                  borderLeft: active ? '3px solid #89b4fa' : '3px solid transparent',
                  transition: 'all 0.15s',
                }}
              >
                <span style={{ fontSize: 14 }}>{m.icon}</span>
                {m.label}
              </div>
            );
          })}
        </div>

        <div style={{ padding: '16px 20px', borderTop: '1px solid #313244' }}>
          <div
            onClick={() => navigate('/')}
            style={{ fontSize: 12, color: '#6c7086', cursor: 'pointer' }}
          >
            ← Back to Dashboard
          </div>
        </div>
      </div>

      {/* Main content */}
      <div style={{ flex: 1, background: '#f7f7f5', overflowY: 'auto' }}>
        <Outlet />
      </div>
    </div>
  );
}