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
    <div style={{ 
      display: 'flex', 
      minHeight: '100vh', 
      fontFamily: '"Inter", system-ui, sans-serif',
      color: '#0f172a'
    }}>

      {/* Sidebar - Deep Slate Theme */}
      <div style={{
        width: 260, background: '#0f172a', color: '#94a3b8',
        padding: '32px 0', flexShrink: 0, position: 'sticky',
        top: 0, height: '100vh', overflowY: 'auto',
        boxShadow: '4px 0 10px -2px rgb(0 0 0 / 0.1)'
      }}>
        <div style={{ padding: '0 24px 32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{ 
              width: 32, height: 32, background: 'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)',
              borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff',
              fontWeight: 800, fontSize: 16
            }}>A</div>
            <span style={{ fontWeight: 800, fontSize: 18, color: '#fff', letterSpacing: '-0.5px' }}>Admin Portal</span>
          </div>
          <p style={{ margin: 0, fontSize: 12, fontWeight: 500, color: '#475569' }}>Healthcare AI Platform v2.0</p>
        </div>

        <div style={{ padding: '0 12px' }}>
          <div style={{ padding: '0 12px 12px', fontSize: 11, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '1px' }}>
            Core Inventory
          </div>
          {MODELS.map(m => {
            const active = location.pathname.includes(`/admin-panel/${m.key}`);
            return (
              <div
                key={m.key}
                onClick={() => navigate(`/admin-panel/${m.key}`)}
                style={{
                  padding: '12px 16px', cursor: 'pointer', fontSize: 13, fontWeight: active ? 700 : 500,
                  display: 'flex', alignItems: 'center', gap: 12, borderRadius: 8,
                  marginBottom: 4,
                  background: active ? '#1e293b' : 'transparent',
                  color: active ? '#fff' : '#94a3b8',
                  transition: 'all 0.2s',
                }}
              >
                <span style={{ fontSize: 18, filter: active ? 'none' : 'grayscale(1)' }}>{m.icon}</span>
                {m.label}
              </div>
            );
          })}
        </div>

        <div style={{ marginTop: 24, padding: '24px 12px 0', borderTop: '1px solid #1e293b' }}>
          <div
            onClick={() => navigate('/')}
            style={{ 
              padding: '12px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: 10, borderRadius: 8,
              color: '#64748b', transition: 'all 0.2s'
            }}
          >
            <span>←</span> Back to Dashboard
          </div>
        </div>
      </div>

      {/* Main content - Matching Dashboard canvas */}
      <div style={{ 
        flex: 1, 
        background: '#f8fafc', 
        backgroundImage: 'radial-gradient(#e2e8f0 0.5px, transparent 0.5px)',
        backgroundSize: '24px 24px',
        overflowY: 'auto' 
      }}>
        <div style={{ padding: '40px' }}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}