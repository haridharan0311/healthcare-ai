import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { crudApi } from '../api';

const MODEL_CONFIG = {
  clinics:             { label: 'Clinics',            display: ['id', 'clinic_name', 'clinic_address_1'] },
  doctors:             { label: 'Doctors',            display: ['id', 'first_name', 'last_name', 'qualification', 'clinic_name'] },
  patients:            { label: 'Patients',           display: ['id', 'first_name', 'last_name', 'gender', 'mobile_number', 'clinic_name'] },
  diseases:            { label: 'Diseases',           display: ['id', 'name', 'season', 'category', 'severity', 'is_active'] },
  appointments:        { label: 'Appointments',       display: ['id', 'op_number', 'patient_name', 'doctor_name', 'disease_name', 'appointment_status', 'appointment_datetime'] },
  drugs:               { label: 'Drug Master',        display: ['id', 'drug_name', 'generic_name', 'drug_strength', 'dosage_type', 'current_stock'] },
  prescriptions:       { label: 'Prescriptions',      display: ['id', 'prescription_date', 'patient_name', 'doctor_name', 'clinic_name'] },
  'prescription-lines':{ label: 'Prescription Lines', display: ['id', 'drug_name', 'disease_name', 'quantity', 'duration'] },
};

export default function ModelList() {
  const { model }   = useParams();
  const navigate    = useNavigate();
  const config      = MODEL_CONFIG[model] || { label: model, display: ['id'] };

  const [data, setData]       = useState([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [search, setSearch]   = useState('');
  const [loading, setLoading] = useState(true);

  const PAGE_SIZE = 20;

  useEffect(() => {
    setPage(1);
    setSearch('');
  }, [model]);

  useEffect(() => {
    setLoading(true);
    crudApi.list(model, page, search, PAGE_SIZE)
      .then(res => {
        setData(res.data.results || res.data);
        setTotal(res.data.count || 0);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [model, page, search]);

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this record?')) return;
    await crudApi.remove(model, id);
    crudApi.list(model, page, search, PAGE_SIZE).then(res => {
      setData(res.data.results || res.data);
      setTotal(res.data.count || 0);
    });
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }`}</style>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 32 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#2563eb', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 8 }}>Management Portal</div>
          <h1 style={{ margin: 0, fontSize: 32, fontWeight: 800, color: '#0f172a', letterSpacing: '-1px' }}>{config.label}</h1>
          <p style={{ margin: '8px 0 0', fontSize: 14, color: '#64748b', fontWeight: 500 }}>{total.toLocaleString()} total entries found in database</p>
        </div>
        <button
          onClick={() => navigate(`/admin-panel/${model}/new`)}
          style={{
            padding: '12px 24px', borderRadius: 10, border: 'none',
            background: '#1e293b', color: '#fff', fontWeight: 600,
            fontSize: 14, cursor: 'pointer', transition: 'all 0.2s',
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
            display: 'flex', alignItems: 'center', gap: 8
          }}
          onMouseOver={(e) => e.target.style.background = '#0f172a'}
          onMouseOut={(e) => e.target.style.background = '#1e293b'}
        >
          <span style={{ fontSize: 18 }}>+</span> Add {config.label.slice(0, -1)}
        </button>
      </div>

      {/* Control Bar */}
      <div style={{ 
        background: '#fff', padding: 16, borderRadius: 12, border: '1px solid #e2e8f0', 
        marginBottom: 24, boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        display: 'flex', alignItems: 'center', gap: 16
      }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <span style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }}>🔍</span>
          <input
            placeholder={`Search across all fields in ${config.label.toLowerCase()}...`}
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            style={{
              width: '100%', padding: '12px 14px 12px 40px', borderRadius: 8,
              border: '1px solid #e2e8f0', fontSize: 14, fontWeight: 500,
              boxSizing: 'border-box', outline: 'none', transition: 'all 0.2s',
              background: '#f8fafc'
            }}
            onFocus={(e) => { e.target.style.borderColor = '#2563eb'; e.target.style.background = '#fff'; }}
            onBlur={(e) => { e.target.style.borderColor = '#e2e8f0'; e.target.style.background = '#f8fafc'; }}
          />
        </div>
      </div>

      {/* Data Grid */}
      <div style={{ 
        background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', 
        overflow: 'hidden', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' 
      }}>
        {loading ? (
          <div style={{ padding: 80, textAlign: 'center', color: '#64748b' }}>
            <div style={{ width: 32, height: 32, border: '4px solid #f1f5f9', borderTopColor: '#2563eb', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }} />
            <div style={{ fontSize: 15, fontWeight: 600 }}>Loading repository...</div>
          </div>
        ) : data.length === 0 ? (
          <div style={{ padding: 80, textAlign: 'center' }}>
            <div style={{ fontSize: 40, marginBottom: 16 }}>📂</div>
            <div style={{ color: '#0f172a', fontWeight: 700, fontSize: 18, marginBottom: 8 }}>No results found</div>
            <p style={{ color: '#64748b', fontSize: 14, margin: 0 }}>Try adjusting your search or adding a new record.</p>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                {config.display.map(col => (
                  <th key={col} style={{ padding: '16px 20px', textAlign: 'left', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px', fontSize: 11 }}>
                    {col.replace(/_/g, ' ')}
                  </th>
                ))}
                <th style={{ padding: '16px 20px', textAlign: 'right', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px', fontSize: 11 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={row.id} style={{ borderBottom: '1px solid #f1f5f9', transition: 'background 0.2s' }} onMouseOver={(e) => e.currentTarget.style.background = '#fcfdfe'} onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}>
                  {config.display.map(col => (
                    <td key={col} style={{ padding: '14px 20px', color: '#334155', fontWeight: 500 }}>
                      {col === 'is_active'
                        ? <span style={{ 
                            background: row[col] ? '#dcfce7' : '#fee2e2', 
                            color: row[col] ? '#166534' : '#991b1b',
                            padding: '4px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 
                          }}>{row[col] ? 'ACTIVE' : 'INACTIVE'}</span>
                        : col === 'severity'
                        ? <span style={{ fontWeight: 700, color: row[col] >= 4 ? '#ef4444' : row[col] >= 3 ? '#f59e0b' : '#10b981' }}>{row[col]}</span>
                        : String(row[col] ?? '—')}
                    </td>
                  ))}
                  <td style={{ padding: '14px 20px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button
                      onClick={() => navigate(`/admin-panel/${model}/${row.id}`)}
                      style={{ 
                        padding: '6px 14px', borderRadius: 8, border: '1px solid #e2e8f0', 
                        background: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600, 
                        marginRight: 8, color: '#475569', transition: 'all 0.2s' 
                      }}
                      onMouseOver={(e) => e.target.style.borderColor = '#cbd5e1'}
                      onMouseOut={(e) => e.target.style.borderColor = '#e2e8f0'}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(row.id)}
                      style={{ 
                        padding: '6px 14px', borderRadius: 8, border: 'none', 
                        background: '#fee2e2', color: '#991b1b', cursor: 'pointer', 
                        fontSize: 12, fontWeight: 600, transition: 'all 0.2s' 
                      }}
                      onMouseOver={(e) => e.target.style.background = '#fecaca'}
                      onMouseOut={(e) => e.target.style.background = '#fee2e2'}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Container */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 32 }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            style={{ 
              padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0', 
              cursor: page === 1 ? 'not-allowed' : 'pointer', background: '#fff',
              fontSize: 13, fontWeight: 600, color: page === 1 ? '#cbd5e1' : '#475569'
            }}>
            Previous
          </button>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#64748b', background: '#f1f5f9', padding: '8px 16px', borderRadius: 8 }}>
            Page <span style={{ color: '#0f172a' }}>{page}</span> of {totalPages}
          </div>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            style={{ 
              padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0', 
              cursor: page === totalPages ? 'not-allowed' : 'pointer', background: '#fff',
              fontSize: 13, fontWeight: 600, color: page === totalPages ? '#cbd5e1' : '#475569'
            }}>
            Next
          </button>
        </div>
      )}
    </div>
  );
}
