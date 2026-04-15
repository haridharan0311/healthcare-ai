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
  getExportUrl,
  apiInstance
} from '../api';
import TopMedicines        from './Reports/TopMedicines';
import LowStockAlerts      from './Reports/LowStockAlerts';
import Seasonality         from './Reports/Seasonality';
import DoctorTrends        from './Reports/DoctorTrends';
import { WeeklyReport, MonthlyReport } from './Reports/WeeklyReport';
import MedicineDependency  from './Reports/MedicineDependency';
import { StockDepletionForecast, AdaptiveBuffers } from './Reports/StockForecast';
import CsvPreviewModal     from '../components/CsvPreviewModal';

// ── Constants ──────────────────────────────────────────────────────────────────

const TABS = [
  'Top Medicines', 'Low Stock Alerts', 'Seasonality',
  'Doctor Trends', 'Weekly', 'Monthly',
  'Medicine Dependencies', 'Stock Depletion Forecast', 'Adaptive Buffers',
];

const WEEKLY_RANGES  = [
  { label: 'WTD', days: 7, period: 'WTD' },
  { label: 'MTD', days: 30, period: 'MTD' },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
];
const MONTHLY_RANGES = [
  { label: 'MTD', days: 30, period: 'MTD' },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: '2Y', days: 730 },
];
const GENERAL_RANGES = [7, 14, 30, 90, 180, 365];
const DEFAULT_DAYS   = {
  'Top Medicines': 30, 'Low Stock Alerts': 30, 'Seasonality': 365,
  'Doctor Trends': 30, 'Weekly': 30, 'Monthly': 30,
  'Medicine Dependencies': 30, 'Stock Depletion Forecast': 90, 'Adaptive Buffers': 30,
};

// ── Main component ─────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const [tab,               setTab]               = useState('Top Medicines');
  const [data,              setData]              = useState(null);
  const [loading,           setLoading]           = useState(false);
  const [error,             setError]             = useState(null);
  const [days,              setDays]              = useState(DEFAULT_DAYS['Top Medicines']);
  const [period,            setPeriod]            = useState(null);
  const [threshold,         setThreshold]         = useState(50);
  const [medicineDeps,      setMedicineDeps]      = useState(null);
  const [stockForecast,     setStockForecast]     = useState(null);
  const [adaptiveBufferData,setAdaptiveBufferData]= useState(null);
  const [stockDrugOptions,  setStockDrugOptions]  = useState([]);
  const [stockDrugName,     setStockDrugName]     = useState('');
  const [csvModal,          setCsvModal]          = useState(null);

  // ── Fetch ──────────────────────────────────────────────────────────────────

  const fetchData = useCallback(() => {
    setData(null); setError(null); setLoading(true);

    const fetchers = {
      'Top Medicines':             () => fetchTopMedicines(days, 15),
      'Low Stock Alerts':          () => fetchLowStockAlerts(threshold),
      'Seasonality':               () => fetchSeasonality(days),
      'Doctor Trends':             () => fetchDoctorTrends(days, 30),
      'Weekly':                    () => fetchWeeklyReport(days, period),
      'Monthly':                   () => fetchMonthlyReport(days, period),
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
  }, [tab, days, threshold, stockDrugName, period]);

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
    setPeriod(newTab === 'Weekly' || newTab === 'Monthly' ? 'MTD' : null);
    setTab(newTab);
  };

  const handleExport = async () => {
    const exportTypeMap = {
      'Top Medicines': 'medicine-usage',
      'Low Stock Alerts': 'restock',
      'Seasonality': 'disease-trends',
      'Doctor Trends': 'doctor-trends',
      'Weekly': 'reports/weekly',
      'Monthly': 'reports/monthly',
    };
    const type = exportTypeMap[tab] || 'disease-trends';
    
    try {
      const url = getExportUrl(type, { days, period });
      const res = await apiInstance.get(url);
      const rows = res.data.trim().split('\n').map(r => {
        const parts = [];
        let current = ''; let inQuotes = false;
        for (let char of r) {
          if (char === '"') inQuotes = !inQuotes;
          else if (char === ',' && !inQuotes) { parts.push(current); current = ''; }
          else current += char;
        }
        parts.push(current);
        return parts.map(c => c.replace(/^"|"$/g, '').trim());
      });
      setCsvModal({ type, rows, url });
    } catch (err) {
      console.error('Export Preview failed:', err);
    }
  };

  // ── Range selector ────────────────────────────────────────────────────────
  const btnStyle = (active) => ({
    padding: '6px 14px', borderRadius: 8, border: '1px solid',
    borderColor: active ? '#1e293b' : '#e2e8f0',
    cursor: 'pointer',
    fontSize: 12, fontWeight: 700,
    background: active ? '#1e293b' : '#fff',
    color: active ? '#fff' : '#64748b', transition: 'all 0.2s',
  });

  const renderRangeSelector = () => {
    if (tab === 'Low Stock Alerts') return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <label style={{ fontSize: 13, color: '#64748b', fontWeight: 600 }}>Threshold (avg/clinic):</label>
        <input type="number" value={threshold} min={0}
          onChange={e => setThreshold(Number(e.target.value))}
          style={{ width: 100, padding: '8px 12px', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13, fontWeight: 600 }}
        />
      </div>
    );

    const rangeButtons = (ranges) => (
      <div style={{ display: 'flex', gap: 6 }}>
        {ranges.map(opt => (
          <button key={opt.label || opt} onClick={() => {
              if (typeof opt === 'number') {
                setDays(opt);
                setPeriod(null);
              } else {
                setDays(opt.days);
                setPeriod(opt.period || null);
              }
            }}
            style={btnStyle((typeof opt === 'number' ? days === opt : (period === opt.period && days === opt.days)))}>
            {typeof opt === 'number' ? `Last ${opt}d` : opt.label}
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
        style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13, fontWeight: 600, background: '#fff' }}>
        {GENERAL_RANGES.map(d => <option key={d} value={d}>Last {d} days</option>)}
      </select>
    );
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: '#f8fafc',
      backgroundImage: 'radial-gradient(#e2e8f0 0.5px, transparent 0.5px)',
      backgroundSize: '24px 24px',
      fontFamily: '"Inter", system-ui, sans-serif' 
    }}>

      {/* Glassmorphism Top bar */}
      <header style={{
        background: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid #f1f5f9',
        padding: '0 40px', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        height: 72, position: 'sticky', top: 0, zIndex: 100,
        boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <a href="/" style={{ 
            display: 'flex', alignItems: 'center', gap: 8,
            color: '#64748b', textDecoration: 'none', fontSize: 14, fontWeight: 700 
          }}>
            <span style={{ fontSize: 18 }}>←</span> Dashboard
          </a>
          <div style={{ width: 1, height: 24, background: '#e2e8f0' }} />
          <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0, letterSpacing: '-0.5px' }}>Reports & Intelligence</h1>
        </div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <button 
            onClick={handleExport}
            style={{
              padding: '10px 20px', background: '#0f172a', color: '#fff',
              borderRadius: 10, border: 'none', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 8, fontSize: 13
            }}
          >
            <span>📥</span> Export CSV
          </button>
          {renderRangeSelector()}
        </div>
      </header>

      <main style={{ maxWidth: 1440, margin: '0 auto', padding: '40px' }}>

        {/* Tab Navigation */}
        <div style={{
          display: 'flex', gap: 4, marginBottom: 32, flexWrap: 'wrap',
          background: '#fff', padding: 4, borderRadius: 12,
          border: '1px solid #e2e8f0', width: 'fit-content',
          boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)'
        }}>
          {TABS.map(t => (
            <button key={t} onClick={() => handleTabChange(t)} style={{
              padding: '10px 20px', borderRadius: 9, border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: tab === t ? 700 : 500,
              background: tab === t ? '#1e293b' : 'transparent',
              color: tab === t ? '#fff' : '#64748b', transition: 'all 0.2s',
            }}>
              {t}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div style={{ 
          background: '#fff', 
          borderRadius: 16, 
          padding: 32, 
          border: '1px solid #e2e8f0', 
          minHeight: 500,
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)'
        }}>

          {loading && (
            <div style={{ height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
              <div style={{ width: 32, height: 32, border: '4px solid #f1f5f9', borderTopColor: '#2563eb', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              <div style={{ marginTop: 16, fontSize: 15, fontWeight: 600 }}>Aggregating {tab}...</div>
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          )}

          {error && !loading && (
            <div style={{ height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ fontSize: 40, marginBottom: 16 }}>⚠️</div>
              <div style={{ color: '#0f172a', fontWeight: 700, fontSize: 18, marginBottom: 8 }}>{error}</div>
              <p style={{ color: '#64748b', marginBottom: 24 }}>The analytics engine encountered an issue processing this request.</p>
              <button onClick={fetchData} style={{
                padding: '12px 32px', borderRadius: 10, border: 'none',
                cursor: 'pointer', fontSize: 14, background: '#1e293b', color: '#fff', fontWeight: 600
              }}>
                Retry Analysis
              </button>
            </div>
          )}

          {!loading && !error && (
            <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
              <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }`}</style>
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
            </div>
          )}
        </div>
      </main>

      {csvModal && <CsvPreviewModal data={csvModal} onClose={() => setCsvModal(null)} />}
    </div>
  );
}
