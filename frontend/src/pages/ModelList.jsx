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
    <div style={{ padding: 32 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 500 }}>{config.label}</h1>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: '#888' }}>{total} records</p>
        </div>
        <button
          onClick={() => navigate(`/admin-panel/${model}/new`)}
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none',
            background: '#89b4fa', color: '#1e1e2e', fontWeight: 500,
            fontSize: 14, cursor: 'pointer'
          }}
        >
          + Add new
        </button>
      </div>

      {/* Search */}
      <input
        placeholder={`Search ${config.label.toLowerCase()}...`}
        value={search}
        onChange={e => { setSearch(e.target.value); setPage(1); }}
        style={{
          width: '100%', padding: '10px 14px', borderRadius: 8,
          border: '1px solid #ddd', fontSize: 14, marginBottom: 16,
          boxSizing: 'border-box', outline: 'none'
        }}
      />

      {/* Table */}
      <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #eee', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#aaa' }}>Loading...</div>
        ) : data.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#aaa' }}>No records found</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f8f8f8', borderBottom: '1px solid #eee' }}>
                {config.display.map(col => (
                  <th key={col} style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 500, color: '#555', whiteSpace: 'nowrap' }}>
                    {col.replace(/_/g, ' ')}
                  </th>
                ))}
                <th style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 500, color: '#555' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={row.id} style={{ borderBottom: '1px solid #f5f5f5', background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
                  {config.display.map(col => (
                    <td key={col} style={{ padding: '10px 16px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {col === 'is_active'
                        ? <span style={{ color: row[col] ? '#1D9E75' : '#E24B4A', fontWeight: 500 }}>{row[col] ? 'Active' : 'Inactive'}</span>
                        : String(row[col] ?? '—')}
                    </td>
                  ))}
                  <td style={{ padding: '10px 16px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button
                      onClick={() => navigate(`/admin-panel/${model}/${row.id}`)}
                      style={{ padding: '5px 12px', borderRadius: 6, border: '1px solid #ddd', background: '#fff', cursor: 'pointer', fontSize: 12, marginRight: 6 }}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(row.id)}
                      style={{ padding: '5px 12px', borderRadius: 6, border: '1px solid #F09595', background: '#FCEBEB', color: '#A32D2D', cursor: 'pointer', fontSize: 12 }}
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 20 }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #ddd', cursor: 'pointer', background: '#fff' }}>
            Prev
          </button>
          <span style={{ padding: '6px 14px', fontSize: 13, color: '#666' }}>
            Page {page} of {totalPages}
          </span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #ddd', cursor: 'pointer', background: '#fff' }}>
            Next
          </button>
        </div>
      )}
    </div>
  );
}
