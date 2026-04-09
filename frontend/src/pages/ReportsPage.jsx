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
import TopMedicines        from './Reports/TopMedicines';
import LowStockAlerts      from './Reports/LowStockAlerts';
import Seasonality         from './Reports/Seasonality';
import DoctorTrends        from './Reports/DoctorTrends';
import { WeeklyReport, MonthlyReport } from './Reports/WeeklyReport';
import MedicineDependency  from './Reports/MedicineDependency';
import { StockDepletionForecast, AdaptiveBuffers } from './Reports/StockForecast';

// ── Constants ──────────────────────────────────────────────────────────────────

const TABS = [
  'Top Medicines', 'Low Stock Alerts', 'Seasonality',
  'Doctor Trends', 'Weekly', 'Monthly',
  'Medicine Dependencies', 'Stock Depletion Forecast', 'Adaptive Buffers',
];

const WEEKLY_RANGES  = [30, 60, 90, 120, 180, 270, 365, 730].map(d => ({ label: d >= 365 ? `${d/365}Y` : `${d/30}M`, days: d }));
const MONTHLY_RANGES = [90, 180, 365, 730, 1095, 1460, 1825].map(d => ({ label: d >= 365 ? `${(d/365).toFixed(0)}Y` : `${d/30}M`, days: d }));
const GENERAL_RANGES = [7, 14, 30, 90, 180, 365];
const DEFAULT_DAYS   = {
  'Top Medicines': 30, 'Low Stock Alerts': 30, 'Seasonality': 365,
  'Doctor Trends': 30, 'Weekly': 60, 'Monthly': 365,
  'Medicine Dependencies': 30, 'Stock Depletion Forecast': 90, 'Adaptive Buffers': 30,
};

// ── Main component ─────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const [tab,               setTab]               = useState('Top Medicines');
  const [data,              setData]              = useState(null);
  const [loading,           setLoading]           = useState(false);
  const [error,             setError]             = useState(null);
  const [days,              setDays]              = useState(DEFAULT_DAYS['Top Medicines']);
  const [threshold,         setThreshold]         = useState(50);
  const [medicineDeps,      setMedicineDeps]      = useState(null);
  const [stockForecast,     setStockForecast]     = useState(null);
  const [adaptiveBufferData,setAdaptiveBufferData]= useState(null);
  const [stockDrugOptions,  setStockDrugOptions]  = useState([]);
  const [stockDrugName,     setStockDrugName]     = useState('');

  // ── Fetch ──────────────────────────────────────────────────────────────────

  const fetchData = useCallback(() => {
    setData(null); setError(null); setLoading(true);

    const fetchers = {
      'Top Medicines':             () => fetchTopMedicines(days, 15),
      'Low Stock Alerts':          () => fetchLowStockAlerts(threshold),
      'Seasonality':               () => fetchSeasonality(days),
      'Doctor Trends':             () => fetchDoctorTrends(days, 30),
      'Weekly':                    () => fetchWeeklyReport(days),
      'Monthly':                   () => fetchMonthlyReport(days),
      'Medicine Dependencies':     () => fetchMedicineDependency(null, days),
      'Stock Depletion Forecast':  () => stockDrugName
        ? fetchStockDepletionForecast(stockDrugName, days)
        : Promise.resolve({ data: null }),
      'Adaptive Buffers':          () => fetchAdaptiveBuffer(days),
    };

    (fetchers[tab] ? fetchers[tab]() : Promise.reject(new Error('Unknown tab')))
      .then(res => {
        if (tab === 'Medicine Dependencies')    setMedicineDeps(res.data);
        else if (tab === 'Stock Depletion Forecast') setStockForecast(res.data);
        else if (tab === 'Adaptive Buffers')    setAdaptiveBufferData(res.data);
        else setData(tab === 'Top Medicines' ? (res.data?.top_medicines || []) : res.data);
      })
      .catch(() => setError('Failed to load data. Please try again.'))
      .finally(() => setLoading(false));
  }, [tab, days, threshold, stockDrugName]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Pre-load drug options for Stock Depletion Forecast
  useEffect(() => {
    if (tab !== 'Stock Depletion Forecast' || stockDrugOptions.length > 0) return;
    fetchTopMedicines(365, 50).then(res => {
      const options = (res.data?.top_medicines || []).map(d => ({
        value: d.drug_name,
        label: `${d.drug_name}${d.generic_name ? ` (${d.generic_name})` : ''}`,
      }));
      setStockDrugOptions(options);
      if (options.length > 0 && !stockDrugName) setStockDrugName(options[0].value);
    }).catch(() => {});
  }, [tab, stockDrugName, stockDrugOptions.length]);

  // ── Tab switch ────────────────────────────────────────────────────────────

  const handleTabChange = (newTab) => {
    if (newTab === tab) { fetchData(); return; }
    setData(null); setError(null);
    setMedicineDeps(null); setStockForecast(null); setAdaptiveBufferData(null);
    setDays(DEFAULT_DAYS[newTab] || 30);
    setTab(newTab);
  };

  // ── Range selector ────────────────────────────────────────────────────────

  const btnStyle = (active) => ({
    padding: '4px 10px', borderRadius: 5, border: 'none', cursor: 'pointer',
    fontSize: 12, fontWeight: active ? 600 : 400,
    background: active ? '#2563eb' : '#f3f4f6',
    color: active ? '#fff' : '#555', transition: 'all 0.15s',
  });

  const renderRangeSelector = () => {
    if (tab === 'Low Stock Alerts') return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <label style={{ fontSize: 12, color: '#6b7280' }}>Threshold (avg/clinic):</label>
        <input type="number" value={threshold} min={0}
          onChange={e => setThreshold(Number(e.target.value))}
          style={{ width: 90, padding: '5px 10px', borderRadius: 6, border: '1px solid #e5e7eb', fontSize: 13 }}
        />
      </div>
    );

    const rangeButtons = (ranges) => (
      <div style={{ display: 'flex', gap: 4 }}>
        {ranges.map(opt => (
          <button key={opt.days ?? opt} onClick={() => setDays(opt.days ?? opt)}
            style={btnStyle(days === (opt.days ?? opt))}>
            {opt.label ?? `${opt}d`}
          </button>
        ))}
      </div>
    );

    if (tab === 'Weekly')  return rangeButtons(WEEKLY_RANGES);
    if (tab === 'Monthly') return rangeButtons(MONTHLY_RANGES);
    if (['Medicine Dependencies', 'Adaptive Buffers'].includes(tab)) return rangeButtons([7, 14, 30, 60, 90]);
    if (tab === 'Stock Depletion Forecast') return rangeButtons([30, 60, 90, 120, 180]);

    return (
      <select value={days} onChange={e => setDays(Number(e.target.value))}
        style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e5e7eb', fontSize: 13 }}>
        {GENERAL_RANGES.map(d => <option key={d} value={d}>Last {d} days</option>)}
      </select>
    );
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div style={{ minHeight: '100vh', background: '#f5f6fa', fontFamily: 'system-ui, sans-serif' }}>

      {/* Top bar */}
      <div style={{
        background: '#fff', borderBottom: '1px solid #eee',
        padding: '0 32px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', height: 60,
        position: 'sticky', top: 0, zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <a href="/" style={{ color: '#6b7280', textDecoration: 'none', fontSize: 13 }}>← Dashboard</a>
          <span style={{ fontWeight: 600, fontSize: 16 }}>Reports &amp; Analytics</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {renderRangeSelector()}
        </div>
      </div>

      <div style={{ maxWidth: 1300, margin: '0 auto', padding: '24px' }}>

        {/* Active tab label */}
        <div style={{ marginBottom: 8 }}>
          <span style={{ fontSize: 12, color: '#6b7280', marginRight: 8 }}>Active tab:</span>
          <strong style={{ fontSize: 14 }}>{tab}</strong>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex', gap: 4, marginBottom: 20, flexWrap: 'wrap',
          background: '#fff', padding: 6, borderRadius: 10,
          border: '1px solid #eee', width: 'fit-content',
        }}>
          {TABS.map(t => (
            <button key={t} onClick={() => handleTabChange(t)} style={{
              padding: '7px 16px', borderRadius: 7, border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: tab === t ? 600 : 400,
              background: tab === t ? '#2563eb' : 'transparent',
              color: tab === t ? '#fff' : '#6b7280', transition: 'all 0.15s',
            }}>
              {t}
            </button>
          ))}
        </div>

        {/* Content panel */}
        <div style={{ background: '#fff', borderRadius: 12, padding: 28, border: '1px solid #eee', minHeight: 420 }}>

          {loading && (
            <div style={{ padding: 60, textAlign: 'center', color: '#9ca3af', fontSize: 14 }}>
              Loading {tab}...
            </div>
          )}

          {error && !loading && (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <div style={{ color: '#dc2626', marginBottom: 12, fontSize: 14 }}>{error}</div>
              <button onClick={fetchData} style={{
                padding: '7px 20px', borderRadius: 6, border: '1px solid #e5e7eb',
                cursor: 'pointer', fontSize: 13, background: '#fff',
              }}>
                Retry
              </button>
            </div>
          )}

          {!loading && !error && (
            <>
              {data && tab === 'Top Medicines' && Array.isArray(data) && (
                <TopMedicines data={data} days={days} />
              )}
              {data && tab === 'Low Stock Alerts' && (
                <LowStockAlerts data={data} threshold={threshold} />
              )}
              {data && tab === 'Seasonality' && (
                <Seasonality data={data} />
              )}
              {data && tab === 'Doctor Trends' && (
                <DoctorTrends data={data} days={days} />
              )}
              {data && tab === 'Weekly' && (
                <WeeklyReport data={data} />
              )}
              {data && tab === 'Monthly' && (
                <MonthlyReport data={data} />
              )}
              {tab === 'Medicine Dependencies' && (
                <MedicineDependency data={medicineDeps} days={days} />
              )}
              {tab === 'Stock Depletion Forecast' && (
                <StockDepletionForecast
                  forecast={stockForecast}
                  drugName={stockDrugName}
                  drugOptions={stockDrugOptions}
                  days={days}
                  onDrugChange={setStockDrugName}
                />
              )}
              {tab === 'Adaptive Buffers' && (
                <AdaptiveBuffers data={adaptiveBufferData} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
