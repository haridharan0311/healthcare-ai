import { useState, useEffect } from 'react';
import { useDistricts, useDistrictRestock } from '../hooks/useDashboardData';

const STATUS_STYLE = {
  critical:   { background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca' },
  low:        { background: '#fffbeb', color: '#92400e', border: '1px solid #fef3c7' },
  sufficient: { background: '#f0fdf4', color: '#15803d', border: '1px solid #bbf7d0' },
};

export default function DistrictRestock({ days, onExport }) {
  const { data: districts = [], isLoading: districtsLoading } = useDistricts();
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const { data: restockData, isLoading: restockLoading } = useDistrictRestock(selectedDistrict, days);
  
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortField, setSortField] = useState('status');
  const [sortDir, setSortDir] = useState('asc');

  // Auto-select first district when list loads
  useEffect(() => {
    if (districts.length > 0 && !selectedDistrict) {
      setSelectedDistrict(districts[0]);
    }
  }, [districts, selectedDistrict]);

  const handleSort = (field) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const results = restockData?.results || [];
  const filtered = results
    .filter(r => statusFilter === 'all' || r.status === statusFilter)
    .filter(r => !search || r.drug_name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const STATUS_ORDER = { critical: 0, low: 1, sufficient: 2 };
      let va = sortField === 'status' ? (STATUS_ORDER[a.status] ?? 3) : a[sortField];
      let vb = sortField === 'status' ? (STATUS_ORDER[b.status] ?? 3) : b[sortField];
      return sortDir === 'asc' ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });

  return (
    <div style={{
      background: '#fff', borderRadius: 16, padding: 24,
      marginBottom: 32, border: '1px solid #f1f5f9', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#1e293b' }}>Supply Chain Forecast</h2>
          <div style={{ fontSize: 13, color: '#64748b' }}>Strategic Pharmacy Replenishment Suggestions</div>
        </div>
        <button
          onClick={() => onExport({ district: selectedDistrict })}
          style={{
            padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0',
            background: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600, color: '#444'
          }}
        >
          Export
        </button>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <select
          value={selectedDistrict}
          onChange={e => setSelectedDistrict(e.target.value)}
          style={{
            padding: '10px 16px', borderRadius: 10, border: '1px solid #e2e8f0',
            fontSize: 14, fontWeight: 600, background: '#f8fafc', minWidth: 200, outline: 'none'
          }}
        >
          <option value="">{districtsLoading ? 'Loading Clinics...' : 'Select Clinic'}</option>
          {districts.map(d => <option key={d} value={d}>{d}</option>)}
        </select>

        <div style={{ display: 'flex', gap: 8, flex: 1 }}>
          <input
            placeholder="Search medicine..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              flex: 1, padding: '10px 16px', borderRadius: 10, border: '1px solid #e2e8f0',
              fontSize: 14, outline: 'none'
            }}
          />
        </div>
      </div>

      {restockData?.summary && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 24 }}>
          {['critical', 'low', 'sufficient'].map(k => (
            <button
              key={k}
              onClick={() => setStatusFilter(statusFilter === k ? 'all' : k)}
              style={{
                ...STATUS_STYLE[k], padding: '8px 16px', borderRadius: 10,
                fontSize: 12, fontWeight: 700, cursor: 'pointer', textTransform: 'uppercase',
                opacity: statusFilter === 'all' || statusFilter === k ? 1 : 0.4
              }}
            >
              {k}: {restockData.summary[k]}
            </button>
          ))}
        </div>
      )}

      {restockLoading ? (
        <div style={{ padding: 60, textAlign: 'center', color: '#94a3b8' }}>Forecasting demand...</div>
      ) : filtered.length === 0 ? (
        <div style={{ padding: 60, textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: 12 }}>
          No restock data found for this selection.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f1f5f9', fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>
                <th onClick={() => handleSort('drug_name')} style={{ padding: 12, cursor: 'pointer' }}>Medicine</th>
                <th style={{ padding: 12 }}>Distribution</th>
                <th onClick={() => handleSort('current_stock')} style={{ padding: 12, textAlign: 'right', cursor: 'pointer' }}>Stock</th>
                <th onClick={() => handleSort('predicted_demand')} style={{ padding: 12, textAlign: 'right', cursor: 'pointer' }}>Demand</th>
                <th onClick={() => handleSort('suggested_restock')} style={{ padding: 12, textAlign: 'right', cursor: 'pointer' }}>Suggestion</th>
                <th style={{ padding: 12, textAlign: 'right' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #f8fafc', background: row.status === 'critical' ? '#fffafb' : 'transparent' }}>
                  <td style={{ padding: 14 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: '#1e293b' }}>{row.drug_name}</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>{row.generic_name} · {row.drug_strength}</div>
                  </td>
                  <td style={{ padding: 14, color: '#64748b', fontSize: 13 }}>{row.clinic_count}</td>
                  <td style={{ padding: 14, textAlign: 'right', color: '#1e293b', fontWeight: 600 }}>{row.current_stock.toLocaleString()}</td>
                  <td style={{ padding: 14, textAlign: 'right', color: '#64748b' }}>{Number(row.predicted_demand).toFixed(1)}</td>
                  <td style={{ padding: 14, textAlign: 'right', color: '#2563eb', fontWeight: 700 }}>{row.suggested_restock.toLocaleString()}</td>
                  <td style={{ padding: 14, textAlign: 'right' }}>
                    <span style={{
                      ...STATUS_STYLE[row.status], padding: '4px 10px', borderRadius: 6,
                      fontSize: 11, fontWeight: 700, textTransform: 'uppercase'
                    }}>{row.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
