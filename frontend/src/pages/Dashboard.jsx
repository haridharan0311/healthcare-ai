import { useState, useEffect, useCallback } from 'react';
import {
  fetchPlatformStats,
  fetchPlatformTrends,
  fetchPlatformMedicines,
  getExportUrl,
  fetchSeasonality,
  fetchDoctorTrends,
  fetchSimulatorStatus,
  toggleSimulator
} from '../api';

import TrendChart       from '../components/TrendChart';
import SpikeAlerts      from '../components/SpikeAlerts';
import DistrictRestock  from '../components/DistrictRestock';
import SummaryCards     from '../components/SummaryCards';
import CsvPreviewModal  from '../components/CsvPreviewModal';

export default function Dashboard() {
  const [csvModal, setCsvModal]       = useState(null);

  const [summaryTrends, setSummaryTrends] = useState([]);
  const [summarySpikes, setSummarySpikes] = useState([]);
  const [summaryToday, setSummaryToday]   = useState(null);
  const [summaryLoaded, setSummaryLoaded] = useState(false);
  const [topMedicines, setTopMedicines]   = useState([]);
  const [lowStock, setLowStock]           = useState({});
  const [seasonality, setSeasonality]     = useState({});
  const [doctorTrends, setDoctorTrends]   = useState([]);
  const [doctorSummary, setDoctorSummary] = useState({});
  const [simStatus, setSimStatus]         = useState({ running: false, interval: 30 });
  const [medicinesLoaded, setMedicinesLoaded] = useState(false);
  const loadAllData = useCallback(() => {
    // 1. Fetch Fast Stats
    fetchPlatformStats(30).then(res => {
      const health = res.data || {};
      setSummaryToday({
         total_today: Math.round((health.total_appointments || 0) / 30),
         by_disease: [], // Filled by trends soon
         date: 'Daily Avg'
      });
      setSummaryLoaded(true);
    }).catch(err => console.error(err));

    // 2. Fetch Charts & Forecasts
    fetchPlatformTrends(30, 8).then(res => {
      const data = res.data || {};
      const diseases = data.top_diseases || [];
      setSummaryTrends(diseases.map(d => ({ ...d, total_cases: d.count })));
      setSummarySpikes(data.forecasts || []);
      
      // Update today summary with top disease
      if (diseases.length > 0) {
        setSummaryToday(prev => ({
          ...prev,
          by_disease: [{ disease: diseases[0].name, count: diseases[0].count / 30 }]
        }));
      }
    }).catch(err => console.error(err));

    // 3. Fetch Heavy Medicines (Non-blocking)
    setMedicinesLoaded(false);
    fetchPlatformMedicines(30).then(res => {
      const decisions = res.data || [];
      setLowStock({
         critical: decisions.filter(d => d.priority === 'High').length,
         out_of_stock: decisions.filter(d => d.current_stock === 0).length
      });
      setTopMedicines(decisions.map(d => ({
         drug_name: d.drug,
         generic_name: `Restock: ${d.recommended_restock} (${d.status})`,
         total_quantity: d.current_stock
      })));
      setMedicinesLoaded(true);
    }).catch(err => {
      console.error(err);
      setMedicinesLoaded(true);
    });

    fetchSeasonality(365).then(res => {
      setSeasonality({ seasons: res.data?.seasons || res.data?.seasonal_patterns || {} });
    }).catch(err => console.error(err));

    fetchDoctorTrends(30, 4).then(res => {
      const data = res.data?.data || res.data || [];
      setDoctorTrends(data);
      setDoctorSummary({
        total_rows: data.length,
        min_cases: data.length > 0 ? data[data.length - 1].case_count : 0
      });
    }).catch(err => console.error(err));

    fetchSimulatorStatus().then(res => {
      setSimStatus(res.data);
    }).catch(err => console.error(err));

  }, []);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  const handleCsvPreview = async (type, params = {}) => {
    const url = getExportUrl(type, { ...params });
    const res = await fetch(url);
    const text = await res.text();
    const rows = text.trim().split('\n').map(r => {
      const parts = [];
      let current = '';
      let inQuotes = false;
      for (let char of r) {
        if (char === '"') inQuotes = !inQuotes;
        else if (char === ',' && !inQuotes) { parts.push(current); current = ''; }
        else current += char;
      }
      parts.push(current);
      return parts.map(c => c.replace(/^"|"$/g, '').trim());
    });
    setCsvModal({ type, rows, url });
  };

  const handleToggleSimulator = () => {
    const action = simStatus.running ? 'stop' : 'start';
    toggleSimulator(action, simStatus.interval).then(res => {
      setSimStatus(res.data);
      if (res.data.running) {
         // Optionally refresh data soon after starting
         setTimeout(loadAllData, 2000);
      }
    });
  };

  const handleIntervalChange = (newVal) => {
    const val = parseInt(newVal);
    if (simStatus.running) {
        toggleSimulator('start', val).then(res => setSimStatus(res.data));
    } else {
        setSimStatus(prev => ({ ...prev, interval: val }));
    }
  };


  return (
    <div style={{
      minHeight: '100vh', 
      background: '#f8fafc',
      backgroundImage: 'radial-gradient(#e2e8f0 0.5px, transparent 0.5px)',
      backgroundSize: '24px 24px',
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
      color: '#0f172a'
    }}>
      {/* ── Premium Top Bar ── */}
      <header style={{
        background: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid #f1f5f9',
        padding: '0 40px', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        height: 72, position: 'sticky', top: 0, zIndex: 100,
        boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ 
            width: 32, height: 32, background: 'linear-gradient(135deg, #0f172a 0%, #2563eb 100%)',
            borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff',
            fontWeight: 800, fontSize: 16
          }}>H</div>
          <span style={{ fontWeight: 800, fontSize: 20, letterSpacing: '-0.5px' }}>Healthcare <span style={{ color: '#2563eb' }}>AI</span></span>
        </div>

        <nav style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            {/* ── Simulator Control Center ── */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, 
              background: '#f8fafc', padding: '6px 12px', borderRadius: 12,
              border: '1px solid #e2e8f0'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: simStatus.running ? '#22c55e' : '#94a3b8',
                  boxShadow: simStatus.running ? '0 0 8px #22c55e' : 'none',
                  animation: simStatus.running ? 'pulse 2s infinite' : 'none'
                }} />
                <span style={{ fontSize: 12, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  {simStatus.running ? 'Live Gen Active' : 'Simulator Off'}
                </span>
              </div>

              <div style={{ height: 20, width: 1, background: '#e2e8f0' }} />

              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <select 
                  value={simStatus.interval}
                  onChange={(e) => handleIntervalChange(e.target.value)}
                  style={{
                    background: 'transparent', border: 'none', fontSize: 12, fontWeight: 600,
                    color: '#1e293b', outline: 'none', cursor: 'pointer'
                  }}
                >
                  <option value={30}>30s</option>
                  <option value={60}>60s</option>
                  <option value={90}>90s</option>
                  <option value={120}>120s</option>
                </select>
                
                <button 
                  onClick={handleToggleSimulator}
                  style={{
                    background: simStatus.running ? '#ef4444' : '#2563eb',
                    color: '#fff', border: 'none', padding: '4px 12px', borderRadius: 6,
                    fontSize: 11, fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s',
                    textTransform: 'uppercase'
                  }}
                >
                  {simStatus.running ? 'Stop' : 'Start'}
                </button>
              </div>
            </div>

            <a href="/reports" style={{
              padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0',
              background: '#fff', fontSize: 13, fontWeight: 600, color: '#1e293b',
              textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6
            }}>📊 Reports</a>
            <a href="/admin-panel" style={{
              padding: '8px 16px', borderRadius: 8, border: 'none',
              background: '#1e293b', fontSize: 13, fontWeight: 600, color: '#fff',
              textDecoration: 'none'
            }}>Admin Portal</a>
          </nav>
      </header>

      {/* ── Main Content ── */}
      <main style={{ maxWidth: 1440, margin: '0 auto', padding: '40px' }}>
        
        {/* Welcome Section */}
        <div style={{ marginBottom: 40 }}>
          <h1 style={{ fontSize: 32, fontWeight: 800, margin: '0 0 8px 0', letterSpacing: '-0.75px', color: '#0f172a' }}>Intelligence Dashboard</h1>
          <p style={{ margin: 0, color: '#64748b', fontSize: 16, fontWeight: 500 }}>Real-time epidemiological monitoring & inventory analysis</p>
        </div>

        {/* Top 5 metrics */}
        <SummaryCards days={30} summary={{ loaded: summaryLoaded, trends: summaryTrends, spikes: summarySpikes, todaySummary: summaryToday, stockAlerts: lowStock }} />

        {/* Insight Gid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20, marginBottom: 32 }}>
          
          {/* Medicines */}
          <div style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)', position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Top Medicines</div>
              <span style={{ fontSize: 20 }}>💊</span>
            </div>
            {!medicinesLoaded ? (
               <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: 13, flexDirection: 'column', gap: 12 }}>
                 <div className="spinner" />
                 Analyzing 2.8M rows...
               </div>
            ) : topMedicines.slice(0, 4).map((m, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{m.drug_name}</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>{m.generic_name}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 800, color: '#2563eb' }}>{(m.total_quantity || 0).toLocaleString()}</div>
                  <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase' }}>Units</div>
                </div>
              </div>
            ))}
          </div>

          {/* Doctor Activity */}
          <div style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Doctor Load</div>
              <span style={{ fontSize: 20 }}>👨‍⚕️</span>
            </div>
            {doctorTrends.slice(0, 4).map((d, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{d.doctor_name}</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>Primary: {d.disease_name}</div>
                </div>
                <div style={{ background: '#f0fdf4', color: '#16a34a', padding: '4px 10px', borderRadius: 8, fontWeight: 700, fontSize: 13 }}>
                  {d.case_count}
                </div>
              </div>
            ))}
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #f1f5f9', fontSize: 11, color: '#64748b' }}>
              <strong>{doctorSummary.total_rows ?? 0}</strong> active specialists &bull; Min cases: {doctorSummary.min_cases ?? 0}
            </div>
          </div>

          {/* Seasonal Trends */}
          <div style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Seasonality</div>
              <span style={{ fontSize: 20 }}>🌍</span>
            </div>
            {Object.entries(seasonality.seasons || {}).slice(0, 3).map(([k, v]) => (
              <div key={k} style={{ marginBottom: 12, padding: '12px', background: '#f8fafc', borderRadius: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 700, fontSize: 13 }}>{k}</span>
                  <span style={{ color: '#7c3aed', fontWeight: 800 }}>{(v?.total_cases || 0).toLocaleString()}</span>
                </div>
                <div style={{ fontSize: 11, color: '#64748b' }}>Top: <span style={{ fontWeight: 600 }}>{v.top_disease}</span></div>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Sections */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: 32, minHeight: 800 }}>
          <SpikeAlerts onExport={(range) => handleCsvPreview('spike-alerts', { days: range })} />
          <TrendChart globalDays={30} onExport={(d) => handleCsvPreview('disease-trends', { days: d })} />
          <DistrictRestock days={30} onExport={() => handleCsvPreview('restock')} />
        </section>

      </main>

      {/* Preview Modal */}
      {csvModal && <CsvPreviewModal data={csvModal} onClose={() => setCsvModal(null)} />}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        * { box-sizing: border-box; }
        body { margin: 0; }
        button:hover { opacity: 0.8; }
        @keyframes pulse {
          0% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.2); opacity: 0.7; }
          100% { transform: scale(1); opacity: 1; }
        }
        .spinner {
          width: 24px;
          height: 24px;
          border: 3px solid #f1f5f9;
          border-top-color: #2563eb;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
