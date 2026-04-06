import { useState, useEffect, useCallback } from 'react';
import {
  fetchTopMedicines,
  fetchLowStockAlerts,
  fetchSeasonality,
  fetchDoctorTrends,
  fetchWeeklyReport,
  fetchMonthlyReport,
  fetchMedicineDependency,
  fetchStockDepletionForecast,
  fetchAdaptiveBuffer,
} from '../api';

// ── Constants ─────────────────────────────────────────────────────────────────

const TABS = [
  'Top Medicines',
  'Low Stock Alerts',
  'Seasonality',
  'Doctor Trends',
  'Weekly',
  'Monthly',
  'Medicine Dependencies',
  'Stock Depletion Forecast',
  'Adaptive Buffers',
];

const WEEKLY_RANGES = [
  { label: '1M', days: 30  },
  { label: '2M', days: 60  },
  { label: '3M', days: 90  },
  { label: '4M', days: 120 },
  { label: '6M', days: 180 },
  { label: '9M', days: 270 },
  { label: '1Y', days: 365 },
  { label: '2Y', days: 730 },
];

const MONTHLY_RANGES = [
  { label: '3M', days: 90   },
  { label: '6M', days: 180  },
  { label: '1Y', days: 365  },
  { label: '2Y', days: 730  },
  { label: '3Y', days: 1095 },
  { label: '4Y', days: 1460 },
  { label: '5Y', days: 1825 },
];

const GENERAL_RANGES = [7, 14, 30, 90, 180, 365];

const DEFAULT_DAYS = {
  'Top Medicines':    30,
  'Low Stock Alerts': 30,
  'Seasonality':      365,
  'Doctor Trends':    30,
  'Weekly':           60,
  'Monthly':          365,
  'Medicine Dependencies': 30,
  'Stock Depletion Forecast': 90,
  'Adaptive Buffers': 30,
};

const SEASON_COLORS = {
  Summer:  '#f97316',
  Monsoon: '#2563eb',
  Winter:  '#7c3aed',
  All:     '#6b7280',
};

// ── Reusable: progress bar ────────────────────────────────────────────────────

function ProgressBar({ pct, color }) {
  return (
    <div style={{ background: '#f3f4f6', borderRadius: 4, height: 5, marginTop: 2 }}>
      <div style={{
        background: color || '#2563eb',
        height: 5,
        borderRadius: 4,
        width: `${Math.min(Math.max(pct, 0), 100)}%`,
        transition: 'width 0.3s ease',
      }} />
    </div>
  );
}

// ── Reusable: disease list with % bars ───────────────────────────────────────

function DiseaseList({ diseases, color }) {
  if (!diseases || diseases.length === 0) return null;
  return (
    <>
      {diseases.map((d, i) => (
        <div key={`${d.disease_name}-${i}`} style={{ marginBottom: 8 }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            fontSize: 12, marginBottom: 2,
          }}>
            <span style={{ color: '#374151' }}>
              <span style={{ color: '#9ca3af', marginRight: 4 }}>#{i + 1}</span>
              {d.disease_name}
            </span>
            <span style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
              {(d.case_count || 0).toLocaleString()}
              <span style={{ color: '#9ca3af', fontWeight: 400, marginLeft: 4 }}>
                ({d.percentage || 0}%)
              </span>
            </span>
          </div>
          <ProgressBar pct={d.percentage || 0} color={color} />
        </div>
      ))}
    </>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const [tab,       setTab]       = useState('Top Medicines');
  const [data,      setData]      = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const [days,      setDays]      = useState(DEFAULT_DAYS['Top Medicines']);
  const [threshold, setThreshold] = useState(50);
  const [medicineDeps, setMedicineDeps] = useState(null);
  const [stockForecast, setStockForecast] = useState(null);
  const [adaptiveBufferData, setAdaptiveBufferData] = useState(null);
  const [stockDrugOptions, setStockDrugOptions] = useState([]);
  const [stockDrugName, setStockDrugName] = useState('');

  // ── Data fetcher ────────────────────────────────────────────────────────────

  const fetchData = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(true);

    const fetchers = {
      'Top Medicines':    () => fetchTopMedicines(days, 15),
      'Low Stock Alerts': () => fetchLowStockAlerts(threshold),
      'Seasonality':      () => fetchSeasonality(days),
      'Doctor Trends':    () => fetchDoctorTrends(days, 30),
      'Weekly':           () => fetchWeeklyReport(days),
      'Monthly':          () => fetchMonthlyReport(days),
      'Medicine Dependencies': () => fetchMedicineDependency(null, days),
      'Stock Depletion Forecast': () => stockDrugName
        ? fetchStockDepletionForecast(stockDrugName, days)
        : Promise.resolve({ data: null }),
      'Adaptive Buffers': () => fetchAdaptiveBuffer(days),
    };

    const request = fetchers[tab]
      ? fetchers[tab]()
      : Promise.reject(new Error('Unknown report tab'));

    request
      .then(res => {
        if (tab === 'Medicine Dependencies') {
          setMedicineDeps(res.data);
        } else if (tab === 'Stock Depletion Forecast') {
          setStockForecast(res.data);
        } else if (tab === 'Adaptive Buffers') {
          setAdaptiveBufferData(res.data);
        } else {
          const payload = tab === 'Top Medicines'
            ? (res.data?.top_medicines || [])
            : res.data;
          setData(payload);
        }
      })
      .catch(() => {
        setError('Failed to load data. Please try again.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [tab, days, threshold, stockDrugName]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (tab !== 'Stock Depletion Forecast') return;
    if (stockDrugOptions.length > 0) return;

    fetchTopMedicines(365, 50)
      .then(res => {
        const options = (res.data?.top_medicines || []).map(drug => ({
          value: drug.drug_name,
          label: `${drug.drug_name}${drug.generic_name ? ` (${drug.generic_name})` : ''}`,
        }));
        setStockDrugOptions(options);
        if (options.length > 0 && !stockDrugName) {
          setStockDrugName(options[0].value);
        }
      })
      .catch(() => {
        // ignore load failure, user can still select a drug manually if needed
      });
  }, [tab, stockDrugName, stockDrugOptions.length]);

  useEffect(() => {
    if (tab === 'Stock Depletion Forecast' && stockDrugName) {
      fetchData();
    }
  }, [stockDrugName, tab, days, fetchData]);

  // ── Tab switch ──────────────────────────────────────────────────────────────

  const handleTabChange = (newTab) => {
    if (newTab === tab) {
      fetchData(); // refresh same tab
      return;
    }
    setData(null);
    setError(null);
    setMedicineDeps(null);
    setStockForecast(null);
    setAdaptiveBufferData(null);
    setDays(DEFAULT_DAYS[newTab] || 30);
    setTab(newTab);
  };

  // ── Range selector (varies per tab) ────────────────────────────────────────

  const renderRangeSelector = () => {
    if (tab === 'Low Stock Alerts') {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label style={{ fontSize: 12, color: '#6b7280' }}>Threshold (avg/clinic):</label>
          <input
            type="number"
            value={threshold}
            min={0}
            onChange={e => setThreshold(Number(e.target.value))}
            style={{
              width: 90, padding: '5px 10px', borderRadius: 6,
              border: '1px solid #e5e7eb', fontSize: 13,
            }}
          />
        </div>
      );
    }

    if (tab === 'Weekly') {
      return (
        <div style={{ display: 'flex', gap: 4 }}>
          {WEEKLY_RANGES.map(opt => (
            <button
              key={opt.label}
              onClick={() => setDays(opt.days)}
              style={{
                padding: '4px 10px', borderRadius: 5, border: 'none',
                cursor: 'pointer', fontSize: 12,
                fontWeight: days === opt.days ? 600 : 400,
                background: days === opt.days ? '#2563eb' : '#f3f4f6',
                color: days === opt.days ? '#fff' : '#555',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      );
    }

    if (tab === 'Monthly') {
      return (
        <div style={{ display: 'flex', gap: 4 }}>
          {MONTHLY_RANGES.map(opt => (
            <button
              key={opt.label}
              onClick={() => setDays(opt.days)}
              style={{
                padding: '4px 10px', borderRadius: 5, border: 'none',
                cursor: 'pointer', fontSize: 12,
                fontWeight: days === opt.days ? 600 : 400,
                background: days === opt.days ? '#2563eb' : '#f3f4f6',
                color: days === opt.days ? '#fff' : '#555',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      );
    }

    if (tab === 'Medicine Dependencies' || tab === 'Adaptive Buffers') {
      return (
        <div style={{ display: 'flex', gap: 4 }}>
          {[7, 14, 30, 60, 90].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={{
                padding: '4px 10px', borderRadius: 5, border: 'none',
                cursor: 'pointer', fontSize: 12,
                fontWeight: days === d ? 600 : 400,
                background: days === d ? '#2563eb' : '#f3f4f6',
                color: days === d ? '#fff' : '#555',
              }}
            >
              {d}d
            </button>
          ))}
        </div>
      );
    }

    if (tab === 'Stock Depletion Forecast') {
      return (
        <div style={{ display: 'flex', gap: 4 }}>
          {[30, 60, 90, 120, 180].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={{
                padding: '4px 10px', borderRadius: 5, border: 'none',
                cursor: 'pointer', fontSize: 12,
                fontWeight: days === d ? 600 : 400,
                background: days === d ? '#2563eb' : '#f3f4f6',
                color: days === d ? '#fff' : '#555',
              }}
            >
              {d}d
            </button>
          ))}
        </div>
      );
    }

    // General dropdown for all other tabs
    return (
      <select
        value={days}
        onChange={e => setDays(Number(e.target.value))}
        style={{
          padding: '5px 10px', borderRadius: 6,
          border: '1px solid #e5e7eb', fontSize: 13,
        }}
      >
        {GENERAL_RANGES.map(d => (
          <option key={d} value={d}>Last {d} days</option>
        ))}
      </select>
    );
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div style={{ minHeight: '100vh', background: '#f5f6fa', fontFamily: 'system-ui, sans-serif' }}>

      {/* ── Top bar ───────────────────────────────────────────────────────── */}
      <div style={{
        background: '#fff', borderBottom: '1px solid #eee',
        padding: '0 32px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', height: 60,
        position: 'sticky', top: 0, zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <a href="/" style={{ color: '#6b7280', textDecoration: 'none', fontSize: 13 }}>
            ← Dashboard
          </a>
          <span style={{ fontWeight: 600, fontSize: 16 }}>Reports & Analytics</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {renderRangeSelector()}
        </div>
      </div>

      <div style={{ maxWidth: 1300, margin: '0 auto', padding: '24px' }}>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div>
            <span style={{ fontSize: 12, color: '#6b7280', marginRight: 8 }}>Active tab:</span>
            <strong style={{ fontSize: 14 }}>{tab}</strong>
          </div>
        </div>

        {/* ── Tabs ──────────────────────────────────────────────────────────── */}
        <div style={{
          display: 'flex', gap: 4, marginBottom: 20, flexWrap: 'wrap',
          background: '#fff', padding: 6, borderRadius: 10,
          border: '1px solid #eee', width: 'fit-content',
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
                transition: 'all 0.15s',
              }}
            >
              {t}
            </button>
          ))}
        </div>

        {/* ── Content panel ─────────────────────────────────────────────────── */}
        <div style={{
          background: '#fff', borderRadius: 12, padding: 28,
          border: '1px solid #eee', minHeight: 420,
        }}>

          {/* Loading state */}
          {loading && (
            <div style={{ padding: 60, textAlign: 'center', color: '#9ca3af', fontSize: 14 }}>
              Loading {tab}...
            </div>
          )}

          {/* Error state */}
          {error && !loading && (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <div style={{ color: '#dc2626', marginBottom: 12, fontSize: 14 }}>{error}</div>
              <button
                onClick={fetchData}
                style={{
                  padding: '7px 20px', borderRadius: 6, border: '1px solid #e5e7eb',
                  cursor: 'pointer', fontSize: 13, background: '#fff',
                }}
              >
                Retry
              </button>
            </div>
          )}

          {/* ── 1. Top Medicines ──────────────────────────────────────────── */}
          {!loading && !error && data && tab === 'Top Medicines' && Array.isArray(data) && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                Top {data.length} medicines
              </h3>
              <p style={{ margin: '0 0 20px', fontSize: 12, color: '#9ca3af' }}>
                Current stock from DrugMaster inventory &nbsp;·&nbsp;
                Prescriptions written in last {days} days
              </p>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: '#f9fafb' }}>
                      {['#', 'Drug name', 'Generic name', 'Dosage type', 'Current stock', 'Prescriptions', 'Variants'].map(h => (
                        <th key={h} style={{
                          padding: '10px 14px', textAlign: 'left', fontWeight: 600,
                          color: '#374151', borderBottom: '2px solid #e5e7eb', whiteSpace: 'nowrap',
                        }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((row, i) => (
                      <tr key={i} style={{
                        borderBottom: '1px solid #f3f4f6',
                        background: i % 2 === 0 ? '#fff' : '#fafafa',
                      }}>
                        <td style={{ padding: '10px 14px', fontWeight: 700, color: '#9ca3af' }}>
                          #{i + 1}
                        </td>
                        <td style={{ padding: '10px 14px', fontWeight: 600 }}>{row.drug_name}</td>
                        <td style={{ padding: '10px 14px', color: '#6b7280' }}>{row.generic_name}</td>
                        <td style={{ padding: '10px 14px' }}>{row.dosage_type}</td>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{ fontWeight: 700, color: '#2563eb', fontSize: 14 }}>
                            {(row.current_stock || 0).toLocaleString()}
                          </span>
                          <span style={{ fontSize: 11, color: '#9ca3af', marginLeft: 4 }}>units</span>
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{ fontWeight: 600 }}>
                            {(row.prescription_count || 0).toLocaleString()}
                          </span>
                          <span style={{ fontSize: 11, color: '#9ca3af', marginLeft: 4 }}>
                            last {days}d
                          </span>
                        </td>
                        <td style={{ padding: '10px 14px', color: '#6b7280', textAlign: 'center' }}>
                          {row.variant_count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── 2. Low Stock Alerts ───────────────────────────────────────── */}
          {!loading && !error && data && tab === 'Low Stock Alerts' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>Low stock alerts</h3>
              <p style={{ margin: '0 0 6px', fontSize: 12, color: '#9ca3af' }}>
                Drugs where average stock per clinic ≤ {threshold} units
              </p>
              {data.note && (
                <p style={{
                  margin: '0 0 16px', fontSize: 11, color: '#374151',
                  background: '#f0f9ff', border: '1px solid #bae6fd',
                  padding: '8px 12px', borderRadius: 6,
                }}>
                  {data.note}
                </p>
              )}

              {/* Summary badges */}
              <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
                {[
                  { label: 'Out of stock', key: 'out_of_stock', color: '#dc2626' },
                  { label: 'Critical',     key: 'critical',     color: '#f97316' },
                  { label: 'Low',          key: 'low',          color: '#eab308' },
                  { label: 'Warning',      key: 'warning',      color: '#6b7280' },
                ].map(s => (
                  <div key={s.key} style={{
                    padding: '8px 18px', borderRadius: 8,
                    border: `1px solid ${s.color}40`,
                    background: `${s.color}10`, fontSize: 13,
                  }}>
                    <span style={{ color: s.color, fontWeight: 700, fontSize: 20, marginRight: 6 }}>
                      {data[s.key] ?? 0}
                    </span>
                    <span style={{ color: '#6b7280' }}>{s.label}</span>
                  </div>
                ))}
                <div style={{
                  padding: '8px 18px', borderRadius: 8,
                  border: '1px solid #e5e7eb', background: '#f9fafb', fontSize: 13,
                }}>
                  <span style={{ fontWeight: 700, fontSize: 20, marginRight: 6 }}>
                    {data.total_alerts ?? 0}
                  </span>
                  <span style={{ color: '#6b7280' }}>total alerts</span>
                </div>
              </div>

              {(data.alerts || []).length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af', fontSize: 14 }}>
                  No drugs with avg stock/clinic ≤ {threshold}
                  <br />
                  <span style={{ fontSize: 12 }}>Try increasing the threshold value above</span>
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#f9fafb' }}>
                        {['Drug', 'Generic', 'Avg/clinic', 'Total stock', 'Clinics', 'Threshold', 'Level', 'Action'].map(h => (
                          <th key={h} style={{
                            padding: '10px 12px', textAlign: 'left', fontWeight: 600,
                            color: '#374151', borderBottom: '2px solid #e5e7eb', whiteSpace: 'nowrap',
                          }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(data.alerts || []).map((row, i) => {
                        const ALERT_COLORS = {
                          out_of_stock: '#dc2626',
                          critical:     '#f97316',
                          low:          '#eab308',
                          warning:      '#9ca3af',
                        };
                        const c = ALERT_COLORS[row.alert_level] || '#9ca3af';
                        return (
                          <tr key={i} style={{
                            borderBottom: '1px solid #f3f4f6',
                            background: row.restock_now ? '#fff7ed' : i % 2 === 0 ? '#fff' : '#fafafa',
                          }}>
                            <td style={{ padding: '9px 12px', fontWeight: 600 }}>{row.drug_name}</td>
                            <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.generic_name}</td>
                            <td style={{ padding: '9px 12px', fontWeight: 700, color: c }}>
                              {row.avg_stock_per_clinic}
                            </td>
                            <td style={{ padding: '9px 12px', color: '#6b7280' }}>
                              {(row.total_stock || 0).toLocaleString()}
                            </td>
                            <td style={{ padding: '9px 12px', color: '#6b7280', textAlign: 'center' }}>
                              {row.clinic_count}
                            </td>
                            <td style={{ padding: '9px 12px', color: '#6b7280' }}>{row.threshold}</td>
                            <td style={{ padding: '9px 12px' }}>
                              <span style={{
                                background: `${c}20`, color: c,
                                padding: '2px 9px', borderRadius: 4, fontSize: 11, fontWeight: 700,
                              }}>
                                {row.alert_level.replace('_', ' ')}
                              </span>
                            </td>
                            <td style={{ padding: '9px 12px' }}>
                              {row.restock_now && (
                                <span style={{
                                  background: '#dc2626', color: '#fff',
                                  padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 700,
                                }}>
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
            </div>
          )}

          {/* ── 3. Seasonality ────────────────────────────────────────────── */}
          {!loading && !error && data && tab === 'Seasonality' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                Disease occurrence by season
              </h3>
              <p style={{ margin: '0 0 8px', fontSize: 12, color: '#9ca3af' }}>{data.period}</p>

              {/* Explanation */}
              <div style={{
                margin: '0 0 20px', fontSize: 12, color: '#374151',
                background: '#f0f9ff', border: '1px solid #bae6fd',
                padding: '10px 14px', borderRadius: 8, lineHeight: 1.7,
              }}>
                <strong>How to read this:</strong> Each card shows diseases grouped by their season
                in the database. <strong>Summer / Monsoon / Winter</strong> are season-specific diseases.
                <strong> All</strong> = year-round diseases (e.g. Hypertension, Diabetes).
                Each season is an independent group — they do not add up to each other.
                <br />
                Overall appointments in this period:{' '}
                <strong style={{ color: '#2563eb' }}>
                  {(data.overall_total || 0).toLocaleString()}
                </strong>
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: 16,
              }}>
                {Object.entries(data.seasons || {})
                  .sort((a, b) => {
                    const order = { Summer: 0, Monsoon: 1, Winter: 2, All: 3 };
                    return (order[a[0]] ?? 9) - (order[b[0]] ?? 9);
                  })
                  .map(([season, info]) => {
                    const color = SEASON_COLORS[season] || '#6b7280';
                    return (
                      <div key={season} style={{
                        border: '1px solid #e5e7eb', borderRadius: 10,
                        padding: 18, borderTop: `4px solid ${color}`,
                      }}>
                        {/* Season header */}
                        <div style={{
                          display: 'flex', justifyContent: 'space-between',
                          alignItems: 'center', marginBottom: 6,
                        }}>
                          <div style={{ fontWeight: 700, fontSize: 15, color }}>{season}</div>
                          <div style={{
                            background: `${color}15`, color,
                            padding: '3px 10px', borderRadius: 8,
                            fontWeight: 700, fontSize: 13,
                          }}>
                            {(info.total_cases || 0).toLocaleString()} cases
                          </div>
                        </div>
                        <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 12 }}>
                          Top: <strong style={{ color: '#374151' }}>{info.top_disease}</strong>
                          &nbsp;· {info.top_disease_count} cases
                        </div>

                        <DiseaseList diseases={info.diseases} color={color} />
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* ── 4. Doctor Trends ──────────────────────────────────────────── */}
          {!loading && !error && data && tab === 'Doctor Trends' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                Doctor-wise disease cases
              </h3>
              <p style={{ margin: '0 0 20px', fontSize: 12, color: '#9ca3af' }}>
                {data.period || `Last ${days} days`}
                &nbsp;· {data.total_rows || 0} entries with ≥ {data.min_cases || 10} cases
              </p>

              {(data.data || []).length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af', fontSize: 14 }}>
                  No doctors with {data.min_cases || 10}+ cases in this period
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#f9fafb' }}>
                        {['#', 'Doctor', 'Disease', 'Season', 'Cases'].map(h => (
                          <th key={h} style={{
                            padding: '10px 14px', textAlign: 'left', fontWeight: 600,
                            color: '#374151', borderBottom: '2px solid #e5e7eb',
                          }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(data.data || []).map((row, i) => {
                        const sc = SEASON_COLORS[row.season] || '#6b7280';
                        return (
                          <tr key={i} style={{
                            borderBottom: '1px solid #f3f4f6',
                            background: i % 2 === 0 ? '#fff' : '#fafafa',
                          }}>
                            <td style={{ padding: '9px 14px', color: '#9ca3af', fontWeight: 600 }}>
                              {i + 1}
                            </td>
                            <td style={{ padding: '9px 14px', fontWeight: 500 }}>{row.doctor_name}</td>
                            <td style={{ padding: '9px 14px' }}>{row.disease_name}</td>
                            <td style={{ padding: '9px 14px' }}>
                              <span style={{
                                background: `${sc}15`, color: sc,
                                padding: '2px 8px', borderRadius: 4,
                                fontSize: 11, fontWeight: 600,
                              }}>
                                {row.season}
                              </span>
                            </td>
                            <td style={{ padding: '9px 14px' }}>
                              <span style={{
                                background: '#eff6ff', color: '#2563eb',
                                padding: '3px 12px', borderRadius: 12,
                                fontWeight: 700, fontSize: 13,
                              }}>
                                {row.case_count}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ── 5. Weekly ─────────────────────────────────────────────────── */}
          {!loading && !error && data && tab === 'Weekly' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                Weekly disease case report
              </h3>
              <p style={{ margin: '0 0 20px', fontSize: 12, color: '#9ca3af' }}>
                {data.period}&nbsp;·&nbsp;
                {data.total_weeks} week{data.total_weeks !== 1 ? 's' : ''}
              </p>

              {(data.weeks || []).length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                  No data for selected range
                </div>
              ) : (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
                  gap: 16,
                }}>
                  {(data.weeks || []).map(week => (
                    <div key={week.week_start} style={{
                      border: '1px solid #e5e7eb', borderRadius: 10,
                      padding: 16, borderTop: '4px solid #2563eb',
                    }}>
                      {/* Week header */}
                      <div style={{
                        display: 'flex', justifyContent: 'space-between',
                        alignItems: 'flex-start', marginBottom: 10,
                      }}>
                        <div>
                          <div style={{ fontWeight: 700, fontSize: 13, color: '#1e40af' }}>
                            Week {week.week_number}
                          </div>
                          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
                            {week.week_start} – {week.week_end}
                          </div>
                        </div>
                        <div style={{
                          background: '#eff6ff', color: '#2563eb',
                          padding: '4px 10px', borderRadius: 8,
                          fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap',
                        }}>
                          {(week.total_cases || 0).toLocaleString()}
                        </div>
                      </div>

                      <DiseaseList diseases={week.diseases} color="#2563eb" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── 6. Monthly ────────────────────────────────────────────────── */}
          {!loading && !error && data && tab === 'Monthly' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                Monthly disease case report
              </h3>
              <p style={{ margin: '0 0 20px', fontSize: 12, color: '#9ca3af' }}>
                {data.period}&nbsp;·&nbsp;
                {data.total_months} month{data.total_months !== 1 ? 's' : ''}
              </p>

              {(data.months || []).length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                  No data for selected range
                </div>
              ) : (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                  gap: 16,
                }}>
                  {(data.months || []).map(month => (
                    <div key={month.month_key} style={{
                      border: '1px solid #e5e7eb', borderRadius: 10,
                      padding: 16, borderTop: '4px solid #7c3aed',
                    }}>
                      {/* Month header */}
                      <div style={{
                        display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginBottom: 10,
                      }}>
                        <div style={{ fontWeight: 700, fontSize: 14, color: '#5b21b6' }}>
                          {month.month_label}
                        </div>
                        <div style={{
                          background: '#f5f3ff', color: '#7c3aed',
                          padding: '4px 10px', borderRadius: 8,
                          fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap',
                        }}>
                          {(month.total_cases || 0).toLocaleString()}
                        </div>
                      </div>

                      <DiseaseList diseases={month.diseases} color="#7c3aed" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── 6. Medicine Dependencies ───────────────────────────────────── */}
          {!loading && !error && medicineDeps && tab === 'Medicine Dependencies' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                Medicine Dependencies & Co-occurrence
              </h3>
              <p style={{ margin: '0 0 20px', fontSize: 12, color: '#9ca3af' }}>
                Medicine usage patterns by disease over the last {days} days
              </p>

              {Array.isArray(medicineDeps) && medicineDeps.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                  No dependency data available
                </div>
              ) : (
                <div style={{ display: 'grid', gap: 18 }}>
                  {Array.isArray(medicineDeps) ? medicineDeps.slice(0, 6).map((disease, i) => (
                    <div key={i} style={{
                      border: '1px solid #e5e7eb', borderRadius: 10,
                      padding: 18, background: '#f8fafc'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                        <div>
                          <div style={{ fontWeight: 700, fontSize: 14 }}>{disease.disease_name}</div>
                          <div style={{ fontSize: 12, color: '#6b7280' }}>
                            {disease.unique_medicines} medicines · {disease.total_prescriptions.toLocaleString()} prescriptions
                          </div>
                        </div>
                        <div style={{
                          background: '#dbeafe', color: '#1d4ed8',
                          padding: '4px 10px', borderRadius: 12,
                          fontSize: 12, fontWeight: 600
                        }}>
                          Top medicines
                        </div>
                      </div>

                      {disease.medicines && disease.medicines.length > 0 ? (
                        <div style={{ display: 'grid', gap: 10 }}>
                          {disease.medicines.slice(0, 5).map((med, j) => (
                            <div key={j} style={{
                              display: 'flex', justifyContent: 'space-between',
                              padding: '8px 12px', borderRadius: 8,
                              background: '#fff', border: '1px solid #e5e7eb'
                            }}>
                              <div>
                                <div style={{ fontWeight: 600 }}>{med.drug_name}</div>
                                <div style={{ fontSize: 11, color: '#6b7280' }}>{med.generic_name}</div>
                              </div>
                              <div style={{ textAlign: 'right' }}>
                                <div style={{ fontWeight: 700 }}>{(med.prescriptions || 0).toLocaleString()}</div>
                                <div style={{ fontSize: 11, color: '#9ca3af' }}>prescriptions</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ fontSize: 12, color: '#9ca3af' }}>
                          No medicines found for this disease.
                        </div>
                      )}
                    </div>
                  )) : (
                    <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                      Unexpected dependency data format.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── 7. Stock Depletion Forecast ──────────────────────────────── */}
          {!loading && !error && tab === 'Stock Depletion Forecast' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                Stock Depletion Forecast
              </h3>
              <p style={{ margin: '0 0 12px', fontSize: 12, color: '#9ca3af' }}>
                Forecast stock depletion for a selected medicine using the last {days} days of history.
              </p>

              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>Select medicine</div>
                  <select
                    value={stockDrugName}
                    onChange={e => setStockDrugName(e.target.value)}
                    style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', minWidth: 260 }}
                  >
                    <option value="">Choose a medicine</option>
                    {stockDrugOptions.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div style={{ fontSize: 12, color: '#6b7280' }}>
                  Forecast horizon: {days} days
                </div>
              </div>

              {!stockDrugName ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                  Select a medicine to view its stock forecast.
                </div>
              ) : !stockForecast ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                  Loading forecast...
                </div>
              ) : stockForecast.error ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#dc2626' }}>
                  {stockForecast.error}
                </div>
              ) : (
                <div style={{ display: 'grid', gap: 12 }}>
                  <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 18, background: '#f8fafc' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 16 }}>{stockForecast.drug_name}</div>
                        <div style={{ fontSize: 12, color: '#6b7280' }}>{stockForecast.generic_name}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#2563eb' }}>
                          {stockForecast.urgency?.toUpperCase() || 'UNKNOWN'}
                        </div>
                        <div style={{ fontSize: 11, color: '#6b7280' }}>Urgency level</div>
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginTop: 16 }}>
                      <div style={{ background: '#fff', borderRadius: 10, padding: 14, border: '1px solid #e5e7eb' }}>
                        <div style={{ fontSize: 12, color: '#6b7280' }}>Current stock</div>
                        <div style={{ fontWeight: 700, fontSize: 18 }}>{stockForecast.current_stock.toLocaleString()} units</div>
                      </div>
                      <div style={{ background: '#fff', borderRadius: 10, padding: 14, border: '1px solid #e5e7eb' }}>
                        <div style={{ fontSize: 12, color: '#6b7280' }}>Avg. daily usage</div>
                        <div style={{ fontWeight: 700, fontSize: 18 }}>{stockForecast.avg_daily_usage.toFixed(2)} units</div>
                      </div>
                      <div style={{ background: '#fff', borderRadius: 10, padding: 14, border: '1px solid #e5e7eb' }}>
                        <div style={{ fontSize: 12, color: '#6b7280' }}>Days until depletion</div>
                        <div style={{ fontWeight: 700, fontSize: 18 }}>{stockForecast.days_until_depletion} days</div>
                      </div>
                    </div>

                    <div style={{ marginTop: 16, fontSize: 12, color: '#374151' }}>
                      Recommended reorder: <strong>{stockForecast.recommended_reorder.toLocaleString()} units</strong>
                    </div>
                    <div style={{ marginTop: 8, fontSize: 11, color: '#6b7280' }}>
                      Forecast period: {stockForecast.analysis_period}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── 8. Adaptive Buffers ───────────────────────────────────────── */}
          {!loading && !error && adaptiveBufferData && tab === 'Adaptive Buffers' && (
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600 }}>
                Adaptive Stock Buffers
              </h3>
              <p style={{ margin: '0 0 20px', fontSize: 12, color: '#9ca3af' }}>
                Recommended buffer multiplier based on recent demand and spike activity
              </p>

              {adaptiveBufferData.error ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#dc2626' }}>
                  {adaptiveBufferData.error}
                </div>
              ) : (
                <div style={{ display: 'grid', gap: 14 }}>
                  <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 18, background: '#f8fafc' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                      <div>
                        <div style={{ fontSize: 12, color: '#6b7280' }}>Adaptive buffer</div>
                        <div style={{ fontSize: 28, fontWeight: 700, color: '#1d4ed8' }}>
                          {adaptiveBufferData.adaptive_buffer}x
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 12, color: '#6b7280' }}>Interpretation</div>
                        <div style={{ fontWeight: 700, fontSize: 16, textTransform: 'capitalize' }}>
                          {adaptiveBufferData.interpretation || 'N/A'}
                        </div>
                      </div>
                    </div>
                    <div style={{ marginTop: 14, fontSize: 12, color: '#374151' }}>
                      Recommended ordering buffer is calculated from spike activity and disease risk.
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
                    {[
                      { label: 'Spike count', value: adaptiveBufferData.spike_count },
                      { label: 'Active diseases', value: adaptiveBufferData.total_diseases },
                      { label: 'Spike %', value: `${adaptiveBufferData.spike_percentage}%` },
                      { label: 'Base buffer', value: `${adaptiveBufferData.base_buffer}x` },
                      { label: 'Max buffer', value: `${adaptiveBufferData.max_buffer}x` },
                      { label: 'Buffer increase', value: `${adaptiveBufferData.buffer_increase}x` },
                    ].map((item, idx) => (
                      <div key={idx} style={{ background: '#fff', borderRadius: 10, padding: 14, border: '1px solid #e5e7eb' }}>
                        <div style={{ fontSize: 12, color: '#6b7280' }}>{item.label}</div>
                        <div style={{ fontWeight: 700, marginTop: 6 }}>{item.value ?? 'N/A'}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

