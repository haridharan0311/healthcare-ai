import { useState, useEffect, useCallback } from 'react';
import {
  fetchTopMedicines, fetchLowStockAlerts, fetchSeasonality,
  fetchDoctorTrends, fetchWeeklyReport, fetchMonthlyReport
} from '../api';

const TABS = [
  'Top Medicines', 'Low Stock Alerts', 'Seasonality',
  'Doctor Trends', 'Weekly', 'Monthly'
];

export default function ReportsPage() {
  const [tab,       setTab]       = useState('Top Medicines');
  const [data,      setData]      = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const [days,      setDays]      = useState(30);
  const [threshold, setThreshold] = useState(50);

  const fetchData = useCallback(() => {
    // Reset state BEFORE fetching — prevents stale-shape crash
    setData(null);
    setError(null);
    setLoading(true);

    const fetchers = {
      'Top Medicines':    () => fetchTopMedicines(days, 15),
      'Low Stock Alerts': () => fetchLowStockAlerts(threshold),   // threshold only, no days
      'Seasonality':      () => fetchSeasonality(days),           // uses local days now
      'Doctor Trends':    () => fetchDoctorTrends(days, 30),
      'Weekly':           () => fetchWeeklyReport(days),          // uses local days
      'Monthly':          () => fetchMonthlyReport(days),         // uses local days
    };

    fetchers[tab]()
      .then(res => {
        setData(res.data);
        setLoading(false);
      })
      .catch(err => {
        setError('Failed to load data. Please try again.');
        setLoading(false);
      });
  }, [tab, days, threshold]); // ← ALL three in deps

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleTabChange = (newTab) => {
    if (newTab === tab) {
      // Re-clicking same tab: force refresh
      fetchData();
      return;
    }
    setData(null);   // clear immediately before tab switches
    setError(null);
    setTab(newTab);
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f5f6fa', fontFamily: 'system-ui, sans-serif' }}>
      {/* Top bar */}
      <div style={{
        background: '#fff', borderBottom: '1px solid #eee',
        padding: '0 32px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', height: 60,
        position: 'sticky', top: 0, zIndex: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <a href="/" style={{ color: '#6b7280', textDecoration: 'none', fontSize: 13 }}>← Dashboard</a>
          <span style={{ fontWeight: 600, fontSize: 16 }}>Reports & Analytics</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Days selector — visible for all tabs except Low Stock Alerts */}
          {tab !== 'Low Stock Alerts' && (
            <select
              value={days}
              onChange={e => setDays(Number(e.target.value))}
              style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e5e7eb', fontSize: 13 }}
            >
              {[7, 14, 30, 90, 180, 365].map(d => (
                <option key={d} value={d}>Last {d} days</option>
              ))}
            </select>
          )}

          {/* Threshold input — only for Low Stock Alerts */}
          {tab === 'Low Stock Alerts' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <label style={{ fontSize: 12, color: '#6b7280' }}>Threshold:</label>
              <input
                type="number"
                value={threshold}
                onChange={e => setThreshold(Number(e.target.value))}
                min={0}
                style={{
                  width: 80, padding: '5px 10px', borderRadius: 6,
                  border: '1px solid #e5e7eb', fontSize: 13
                }}
              />
            </div>
          )}
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px' }}>
        {/* Tabs */}
        <div style={{
          display: 'flex', gap: 4, marginBottom: 20,
          background: '#fff', padding: 6, borderRadius: 10,
          border: '1px solid #eee', width: 'fit-content'
        }}>
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => handleTabChange(t)}
              style={{
                padding: '7px 16px', borderRadius: 7, border: 'none',
                cursor: 'pointer', fontSize: 13,
                fontWeight: tab === t ? 600 : 400,
                background: tab === t ? '#2563eb' : 'transparent',
                color: tab === t ? '#fff' : '#6b7280',
              }}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Content panel */}
        <div style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #eee', minHeight: 400 }}>
          {loading && (
            <div style={{ padding: 60, textAlign: 'center', color: '#9ca3af' }}>
              Loading {tab}...
            </div>
          )}

          {error && !loading && (
            <div style={{ padding: 40, textAlign: 'center', color: '#dc2626' }}>
              {error}
              <br />
              <button onClick={fetchData} style={{ marginTop: 12, padding: '6px 16px', borderRadius: 6, border: '1px solid #e5e7eb', cursor: 'pointer', fontSize: 13 }}>
                Retry
              </button>
            </div>
          )}

          {/* Top Medicines */}
          {!loading && !error && data && tab === 'Top Medicines' && Array.isArray(data) && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                Top {data.length} medicines by usage
              </h3>
              <p style={{ margin: '0 0 16px', fontSize: 12, color: '#9ca3af' }}>
                Based on prescription data · Last {days} days
              </p>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9fafb' }}>
                    {['#', 'Drug', 'Generic', 'Dosage', 'Current Stock', 'Prescriptions (period)', 'Variants'].map(h => (
                      <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f3f4f6', background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
                      <td style={{ padding: '9px 12px', fontWeight: 700, color: '#9ca3af' }}>#{i + 1}</td>
                      <td style={{ padding: '9px 12px', fontWeight: 600 }}>{row.drug_name}</td>
                      <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.generic_name}</td>
                      <td style={{ padding: '9px 12px' }}>{row.dosage_type}</td>
                      <td style={{ padding: '9px 12px', fontWeight: 700, color: '#2563eb' }}>
                        {(row.current_stock || 0).toLocaleString()}
                      </td>
                      <td style={{ padding: '9px 12px' }}>
                        {(row.prescription_count || 0).toLocaleString()}
                        <span style={{ fontSize: 11, color: '#9ca3af', marginLeft: 4 }}>
                          last {days}d
                        </span>
                      </td>
                      <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.variant_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Low Stock Alerts */}
          {!loading && !error && data && tab === 'Low Stock Alerts' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>Low stock alerts</h3>
              <p style={{ margin: '0 0 16px', fontSize: 12, color: '#9ca3af' }}>
                Medicines with total stock ≤ {threshold} units
              </p>
              <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                {[
                  { label: 'Out of stock', key: 'out_of_stock', color: '#dc2626' },
                  { label: 'Critical',     key: 'critical',     color: '#f97316' },
                  { label: 'Low',          key: 'low',          color: '#eab308' },
                  { label: 'Warning',      key: 'warning',      color: '#6b7280' },
                ].map(s => (
                  <div key={s.key} style={{
                    padding: '8px 16px', borderRadius: 8,
                    border: `1px solid ${s.color}30`,
                    background: `${s.color}10`, fontSize: 13
                  }}>
                    <span style={{ color: s.color, fontWeight: 700 }}>{data[s.key] ?? 0}</span>
                    <span style={{ color: '#6b7280', marginLeft: 6 }}>{s.label}</span>
                  </div>
                ))}
                <div style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#f9fafb', fontSize: 13 }}>
                  <span style={{ fontWeight: 700 }}>{data.total_alerts ?? 0}</span>
                  <span style={{ color: '#6b7280', marginLeft: 6 }}>total alerts</span>
                </div>
              </div>

              {(data.alerts || []).length === 0 ? (
                <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>
                  No medicines below threshold of {threshold}
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: '#f9fafb' }}>
                      {['Drug', 'Generic', 'Total Stock', 'Threshold', 'Level', 'Action'].map(h => (
                        <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(data.alerts || []).map((row, i) => {
                      const COLOR = { out_of_stock: '#dc2626', critical: '#f97316', low: '#eab308', warning: '#9ca3af' };
                      const c = COLOR[row.alert_level] || '#9ca3af';
                      return (
                        <tr key={i} style={{ borderBottom: '1px solid #f3f4f6', background: row.restock_now ? '#fff7ed' : i % 2 === 0 ? '#fff' : '#fafafa' }}>
                          <td style={{ padding: '9px 12px', fontWeight: 600 }}>{row.drug_name}</td>
                          <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.generic_name}</td>
                          // In the Low Stock Alerts table, change the stock column:
                          <td style={{ padding: '9px 12px', fontWeight: 700, color: c }}>
                            {row.avg_stock_per_clinic} avg/clinic
                            <span style={{ color: '#9ca3af', fontSize: 11, marginLeft: 4 }}>
                              ({(row.total_stock || 0).toLocaleString()} total)
                            </span>
                          </td>
                          <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.threshold}</td>
                          <td style={{ padding: '9px 12px' }}>
                            <span style={{ background: `${c}20`, color: c, padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>
                              {row.alert_level.replace('_', ' ')}
                            </span>
                          </td>
                          <td style={{ padding: '9px 12px' }}>
                            {row.restock_now && (
                              <span style={{ background: '#dc2626', color: '#fff', padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>
                                RESTOCK NOW
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* Seasonality */}
          {!loading && !error && data && tab === 'Seasonality' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>Disease occurrence by season</h3>
              <p style={{ margin: '0 0 16px', fontSize: 12, color: '#9ca3af' }}>
                {data.period} · Grouped by disease season field
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
                {Object.entries(data.seasons || {}).map(([season, info]) => (
                  <div key={season} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
                    <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 6 }}>{season}</div>
                    <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 10 }}>
                      <strong style={{ color: '#374151' }}>{info.top_disease}</strong> leads with{' '}
                      <strong>{info.top_disease_count}</strong> cases
                      &nbsp;·&nbsp; Total: <strong>{info.total_cases}</strong>
                    </div>
                    {(info.diseases || []).slice(0, 6).map((d, i) => {
                      const pct = info.total_cases > 0
                        ? Math.round((d.case_count / info.total_cases) * 100) : 0;
                      return (
                        <div key={d.disease_name} style={{ marginBottom: 6 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}>
                            <span>#{i+1} {d.disease_name}</span>
                            <span style={{ fontWeight: 600 }}>{d.case_count} ({pct}%)</span>
                          </div>
                          <div style={{ background: '#f3f4f6', borderRadius: 4, height: 4 }}>
                            <div style={{ background: '#2563eb', height: 4, borderRadius: 4, width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Doctor Trends */}
          {!loading && !error && data && tab === 'Doctor Trends' && Array.isArray(data) && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>Doctor-wise disease cases</h3>
              <p style={{ margin: '0 0 16px', fontSize: 12, color: '#9ca3af' }}>
                Last {days} days · Top 30 entries
              </p>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9fafb' }}>
                    {['Doctor', 'Disease', 'Season', 'Cases'].map(h => (
                      <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.slice(0, 30).map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f3f4f6', background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
                      <td style={{ padding: '9px 12px', fontWeight: 500 }}>{row.doctor_name}</td>
                      <td style={{ padding: '9px 12px' }}>{row.disease_name}</td>
                      <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.season}</td>
                      <td style={{ padding: '9px 12px', fontWeight: 700, color: '#2563eb' }}>{row.case_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Weekly / Monthly */}
          {!loading && !error && data && (tab === 'Weekly' || tab === 'Monthly') && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                {tab} disease case report
              </h3>
              <p style={{ margin: '0 0 16px', fontSize: 12, color: '#9ca3af' }}>
                {data.period} · Grouped by {tab === 'Weekly' ? 'week' : 'month'}
              </p>
              {(data.data || []).length === 0 ? (
                <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No data for selected range</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: '#f9fafb' }}>
                      {[tab === 'Weekly' ? 'Week start' : 'Month', 'Disease', 'Cases'].map(h => (
                        <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(data.data || []).map((row, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f3f4f6', background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
                        <td style={{ padding: '9px 12px', fontWeight: 500, fontFamily: 'monospace', fontSize: 12 }}>
                          {row.week || row.month}
                        </td>
                        <td style={{ padding: '9px 12px' }}>{row.disease_name}</td>
                        <td style={{ padding: '9px 12px', fontWeight: 700, color: '#2563eb' }}>{row.case_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
