import { useState, useEffect } from 'react';
import { fetchDistricts, fetchDistrictRestock } from '../api';

const STATUS_STYLE = {
  critical:   { background: '#FCEBEB', color: '#A32D2D', border: '1px solid #F09595' },
  low:        { background: '#FAEEDA', color: '#633806', border: '1px solid #FAC775' },
  sufficient: { background: '#EAF3DE', color: '#27500A', border: '1px solid #C0DD97' },
};

const DATE_OPTIONS = [
  { label: '1W', days: 7  },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180},
];

export default function DistrictRestock() {
  const [districts, setDistricts]         = useState([]);
  const [selectedDistrict, setDistrict]   = useState('');
  const [selectedDays, setDays]           = useState(30);
  const [data, setData]                   = useState(null);
  const [loading, setLoading]             = useState(false);
  const [districtLoading, setDLoading]    = useState(true);
  const [search, setSearch]               = useState('');
  const [statusFilter, setStatusFilter]   = useState('all');
  const [sortField, setSortField]         = useState('status');
  const [sortDir, setSortDir]             = useState('asc');

  // Load district list on mount
  useEffect(() => {
    fetchDistricts().then(res => {
      setDistricts(res.data.districts || []);
      setDLoading(false);
    });
  }, []);

  // Load restock data when district or days changes
  useEffect(() => {
    if (!selectedDistrict) return;
    setLoading(true);
    fetchDistrictRestock(selectedDistrict, selectedDays).then(res => {
      setData(res.data);
      setLoading(false);
    });
  }, [selectedDistrict, selectedDays]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <span style={{ color: '#ccc', marginLeft: 4 }}>↕</span>;
    return <span style={{ marginLeft: 4 }}>{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  const results = data?.results || [];

  const filtered = results
    .filter(r => statusFilter === 'all' || r.status === statusFilter)
    .filter(r =>
      !search ||
      r.drug_name.toLowerCase().includes(search.toLowerCase()) ||
      r.generic_name.toLowerCase().includes(search.toLowerCase()) ||
      r.drug_strength.toLowerCase().includes(search.toLowerCase()) ||
      r.dosage_type.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      const STATUS_ORDER = { critical: 0, low: 1, sufficient: 2 };
      let va, vb;
      if (sortField === 'status') {
        va = STATUS_ORDER[a.status] ?? 3;
        vb = STATUS_ORDER[b.status] ?? 3;
      } else if (sortField === 'current_stock') {
        va = a.current_stock; vb = b.current_stock;
      } else if (sortField === 'suggested_restock') {
        va = a.suggested_restock; vb = b.suggested_restock;
      } else if (sortField === 'predicted_demand') {
        va = a.predicted_demand; vb = b.predicted_demand;
      } else {
        va = (a[sortField] || '').toString().toLowerCase();
        vb = (b[sortField] || '').toString().toLowerCase();
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

  return (
    <div style={{
      background: '#fff', borderRadius: 12, padding: 24,
      marginBottom: 24, border: '1px solid #eee'
    }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 500 }}>Medicine restock</h2>
          {data && (
            <p style={{ margin: '4px 0 0', fontSize: 12, color: '#888' }}>
              {selectedDistrict} · {data.clinic_count} clinics · {data.period}
            </p>
          )}
        </div>

        {/* Period selector */}
        <div style={{ display: 'flex', gap: 4 }}>
          {DATE_OPTIONS.map(opt => (
            <button key={opt.label} onClick={() => setDays(opt.days)} style={{
              padding: '5px 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
              fontSize: 12, fontWeight: selectedDays === opt.days ? 500 : 400,
              background: selectedDays === opt.days ? '#378ADD' : '#f0f0f0',
              color: selectedDays === opt.days ? '#fff' : '#555',
            }}>{opt.label}</button>
          ))}
        </div>
      </div>

      {/* ── District selector + summary cards ── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <select
          value={selectedDistrict}
          onChange={e => setDistrict(e.target.value)}
          style={{
            padding: '8px 14px', borderRadius: 8, border: '1px solid #ddd',
            fontSize: 14, minWidth: 220, outline: 'none', cursor: 'pointer',
            background: '#fff'
          }}
        >
          <option value="">
            {districtLoading ? 'Loading districts...' : `— Select district (${districts.length}) —`}
          </option>
          {districts.map(d => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>

        {/* Summary badges */}
        {data?.summary && (
          <div style={{ display: 'flex', gap: 8 }}>
            {[
              { label: 'Critical', key: 'critical', style: STATUS_STYLE.critical },
              { label: 'Low',      key: 'low',      style: STATUS_STYLE.low      },
              { label: 'Sufficient',key:'sufficient',style: STATUS_STYLE.sufficient},
            ].map(({ label, key, style }) => (
              <button
                key={key}
                onClick={() => setStatusFilter(statusFilter === key ? 'all' : key)}
                style={{
                  ...style,
                  padding: '6px 14px', borderRadius: 6,
                  cursor: 'pointer', fontSize: 12, fontWeight: 500,
                  opacity: statusFilter !== 'all' && statusFilter !== key ? 0.4 : 1,
                  transition: 'opacity 0.15s',
                }}
              >
                {label}: {data.summary[key]}
              </button>
            ))}
            <button
              onClick={() => setStatusFilter('all')}
              style={{
                padding: '6px 14px', borderRadius: 6, border: '1px solid #ddd',
                background: '#f8f8f8', cursor: 'pointer', fontSize: 12,
                opacity: statusFilter === 'all' ? 1 : 0.5,
              }}
            >
              All: {data.summary.total_drugs}
            </button>
          </div>
        )}
      </div>

      {/* ── Search ── */}
      {selectedDistrict && (
        <input
          placeholder="Search by drug name, generic, strength, dosage..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            width: '100%', padding: '9px 14px', borderRadius: 8,
            border: '1px solid #ddd', fontSize: 14, marginBottom: 14,
            boxSizing: 'border-box', outline: 'none'
          }}
        />
      )}

      {/* ── States ── */}
      {!selectedDistrict && (
        <div style={{ padding: '40px 0', textAlign: 'center', color: '#aaa', fontSize: 14 }}>
          Select a district to view restock details
        </div>
      )}

      {selectedDistrict && loading && (
        <div style={{ padding: '40px 0', textAlign: 'center', color: '#aaa' }}>Loading...</div>
      )}

      {/* ── Table ── */}
      {selectedDistrict && !loading && filtered.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f8f8f8', borderBottom: '2px solid #eee' }}>
                {[
                  { label: 'Drug name',        field: 'drug_name'        },
                  { label: 'Generic name',      field: 'generic_name'     },
                  { label: 'Strength',          field: 'drug_strength'    },
                  { label: 'Dosage',            field: 'dosage_type'      },
                  { label: 'Clinics',           field: 'clinic_count'     },
                  { label: 'Current stock',     field: 'current_stock'    },
                  { label: 'Predicted demand',  field: 'predicted_demand' },
                  { label: 'Suggested restock', field: 'suggested_restock'},
                  { label: 'Status',            field: 'status'           },
                  { label: 'Diseases',          field: null               },
                ].map(col => (
                  <th
                    key={col.label}
                    onClick={() => col.field && handleSort(col.field)}
                    style={{
                      padding: '10px 12px', textAlign: 'left',
                      fontWeight: 500, color: '#555', whiteSpace: 'nowrap',
                      cursor: col.field ? 'pointer' : 'default',
                      userSelect: 'none',
                    }}
                  >
                    {col.label}
                    {col.field && <SortIcon field={col.field} />}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, i) => (
                <tr
                  key={i}
                  style={{
                    borderBottom: '1px solid #f5f5f5',
                    background: row.status === 'critical'
                      ? '#fffafa'
                      : row.status === 'low'
                      ? '#fffdf5'
                      : i % 2 === 0 ? '#fff' : '#fafafa'
                  }}
                >
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>{row.drug_name}</td>
                  <td style={{ padding: '10px 12px', color: '#666' }}>{row.generic_name}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{
                      background: '#f0f0f0', borderRadius: 4,
                      padding: '2px 8px', fontSize: 12, fontWeight: 500
                    }}>
                      {row.drug_strength}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', color: '#666' }}>{row.dosage_type}</td>
                  <td style={{ padding: '10px 12px', textAlign: 'center', color: '#888', fontSize: 12 }}>
                    {row.clinic_count}
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>
                    {row.current_stock.toLocaleString()}
                  </td>
                  <td style={{ padding: '10px 12px', color: '#555' }}>
                    {Number(row.predicted_demand).toFixed(1)}
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>
                    {row.suggested_restock.toLocaleString()}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{
                      ...STATUS_STYLE[row.status],
                      borderRadius: 6, padding: '3px 12px',
                      fontSize: 12, fontWeight: 500,
                      display: 'inline-block', whiteSpace: 'nowrap'
                    }}>
                      {row.status}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', color: '#888', fontSize: 11, maxWidth: 200 }}>
                    {row.contributing_diseases.join(', ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedDistrict && !loading && filtered.length === 0 && (
        <div style={{ padding: '40px 0', textAlign: 'center', color: '#aaa' }}>
          No results for current filters
        </div>
      )}
    </div>
  );
}

