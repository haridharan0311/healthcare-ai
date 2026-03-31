import { useState, useEffect } from 'react';
import {
  fetchTopMedicines, fetchLowStockAlerts,
  fetchSeasonality, fetchDoctorTrends,
  fetchWeeklyReport, fetchMonthlyReport
} from '../api';

const TABS = ['Top Medicines', 'Low Stock Alerts', 'Seasonality', 'Doctor Trends', 'Weekly', 'Monthly'];

export default function ReportsPage() {
  const [tab, setTab]         = useState('Top Medicines');
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [days, setDays]       = useState(30);
  const [threshold, setThreshold] = useState(50);

  useEffect(() => {
    setLoading(true);
    setData(null);
    const fetchers = {
      'Top Medicines':   () => fetchTopMedicines(days, 15),
      'Low Stock Alerts': () => fetchLowStockAlerts(threshold),
      'Seasonality':     () => fetchSeasonality(365),
      'Doctor Trends':   () => fetchDoctorTrends(days, 30),
      'Weekly':          () => fetchWeeklyReport(90),
      'Monthly':         () => fetchMonthlyReport(365),
    };
    fetchers[tab]().then(res => {
      setData(res.data);
      setLoading(false);
    });
  }, [tab, days, threshold]);

  return (
    <div style={{ minHeight: '100vh', background: '#f5f6fa', fontFamily: 'system-ui, sans-serif' }}>
      {/* Top bar */}
      <div style={{
        background: '#fff', borderBottom: '1px solid #eee',
        padding: '0 32px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', height: 60
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <a href="/" style={{ color: '#6b7280', textDecoration: 'none', fontSize: 13 }}>← Dashboard</a>
          <span style={{ fontWeight: 600, fontSize: 16 }}>Reports & Analytics</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e5e7eb', fontSize: 13 }}>
            {[7, 14, 30, 90, 180, 365].map(d => (
              <option key={d} value={d}>Last {d} days</option>
            ))}
          </select>
          {tab === 'Low Stock Alerts' && (
            <input type="number" value={threshold}
              onChange={e => setThreshold(Number(e.target.value))}
              placeholder="Threshold"
              style={{ width: 100, padding: '5px 10px', borderRadius: 6, border: '1px solid #e5e7eb', fontSize: 13 }} />
          )}
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px' }}>
        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: '#fff', padding: 6, borderRadius: 10, border: '1px solid #eee', width: 'fit-content' }}>
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: '7px 16px', borderRadius: 7, border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: tab === t ? 600 : 400,
              background: tab === t ? '#2563eb' : 'transparent',
              color: tab === t ? '#fff' : '#6b7280',
            }}>{t}</button>
          ))}
        </div>

        {/* Content */}
        <div style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #eee' }}>
          {loading && <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>Loading...</div>}

          {!loading && data && tab === 'Top Medicines' && (
            <div>
              <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>Top {data.length} medicines by usage</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9fafb' }}>
                    {['Rank', 'Drug', 'Generic', 'Dosage', 'Total Qty', 'Prescriptions', 'Avg Qty/Rx'].map(h => (
                      <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '9px 12px', fontWeight: 600, color: '#6b7280' }}>#{i + 1}</td>
                      <td style={{ padding: '9px 12px', fontWeight: 600 }}>{row.drug_name}</td>
                      <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.generic_name}</td>
                      <td style={{ padding: '9px 12px' }}>{row.dosage_type}</td>
                      <td style={{ padding: '9px 12px', fontWeight: 600 }}>{row.total_quantity?.toLocaleString()}</td>
                      <td style={{ padding: '9px 12px' }}>{row.total_prescriptions?.toLocaleString()}</td>
                      <td style={{ padding: '9px 12px' }}>{row.avg_qty_per_rx}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!loading && data && tab === 'Low Stock Alerts' && (
            <div>
              <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
                {[
                  { label: 'Out of stock', key: 'out_of_stock', color: '#dc2626' },
                  { label: 'Critical',     key: 'critical',     color: '#f97316' },
                  { label: 'Low',          key: 'low',          color: '#eab308' },
                ].map(s => (
                  <div key={s.key} style={{
                    padding: '8px 16px', borderRadius: 8, border: `1px solid ${s.color}20`,
                    background: `${s.color}10`, fontSize: 13
                  }}>
                    <span style={{ color: s.color, fontWeight: 600 }}>{data[s.key] ?? 0}</span>
                    <span style={{ color: '#6b7280', marginLeft: 6 }}>{s.label}</span>
                  </div>
                ))}
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9fafb' }}>
                    {['Drug', 'Generic', 'Total Stock', 'Threshold', 'Alert Level', 'Action'].map(h => (
                      <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data.alerts || []).map((row, i) => {
                    const COLOR = { out_of_stock: '#dc2626', critical: '#f97316', low: '#eab308', warning: '#6b7280' };
                    const c = COLOR[row.alert_level] || '#6b7280';
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid #f3f4f6', background: row.restock_now ? '#fff7ed' : '#fff' }}>
                        <td style={{ padding: '9px 12px', fontWeight: 600 }}>{row.drug_name}</td>
                        <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.generic_name}</td>
                        <td style={{ padding: '9px 12px', fontWeight: 600, color: c }}>{row.total_stock}</td>
                        <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.threshold}</td>
                        <td style={{ padding: '9px 12px' }}>
                          <span style={{ background: `${c}15`, color: c, padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                            {row.alert_level.replace('_', ' ')}
                          </span>
                        </td>
                        <td style={{ padding: '9px 12px' }}>
                          {row.restock_now && (
                            <span style={{ background: '#dc2626', color: '#fff', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                              RESTOCK NOW
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {!loading && data && tab === 'Seasonality' && (
            <div>
              <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>Disease occurrence by season</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                {Object.entries(data.seasons || {}).map(([season, info]) => (
                  <div key={season} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>{season}</div>
                    <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 10 }}>
                      Top: <strong style={{ color: '#374151' }}>{info.top_disease}</strong> ({info.top_disease_count} cases)
                      &nbsp;|&nbsp; Total: <strong>{info.total_cases}</strong>
                    </div>
                    {info.diseases?.slice(0, 5).map((d, i) => (
                      <div key={d.disease_name} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid #f3f4f6', fontSize: 12 }}>
                        <span style={{ color: '#374151' }}>#{i+1} {d.disease_name}</span>
                        <span style={{ fontWeight: 600, color: '#2563eb' }}>{d.case_count}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {!loading && data && tab === 'Doctor Trends' && (
            <div>
              <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>Doctor-wise disease cases</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9fafb' }}>
                    {['Doctor', 'Disease', 'Season', 'Cases'].map(h => (
                      <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(Array.isArray(data) ? data : []).slice(0, 50).map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '9px 12px', fontWeight: 500 }}>{row.doctor_name}</td>
                      <td style={{ padding: '9px 12px' }}>{row.disease_name}</td>
                      <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.season}</td>
                      <td style={{ padding: '9px 12px', fontWeight: 600 }}>{row.case_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!loading && data && (tab === 'Weekly' || tab === 'Monthly') && (
            <div>
              <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>
                {tab} disease case report
              </h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9fafb' }}>
                    {[tab === 'Weekly' ? 'Week' : 'Month', 'Disease', 'Cases'].map(h => (
                      <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data.data || []).map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '9px 12px', fontWeight: 500 }}>{row.week || row.month}</td>
                      <td style={{ padding: '9px 12px' }}>{row.disease_name}</td>
                      <td style={{ padding: '9px 12px', fontWeight: 600 }}>{row.case_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
