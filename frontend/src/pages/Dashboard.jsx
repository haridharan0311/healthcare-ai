import { useState, useEffect, useCallback } from 'react';
import {
  fetchPlatformDashboard,
  getExportUrl,
  fetchSeasonality,
  fetchDoctorTrends
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
  const loadAllData = useCallback(() => {
    fetchPlatformDashboard(30, 8)
      .then(res => {
        const payload = res.data?.data || {};
        const health  = payload.health_analytics || {};
        const topDiseases = payload.top_diseases || [];
        const forecasts = payload.forecasts || [];
        const decisions = payload.decisions || [];

        setSummaryTrends(topDiseases.map(d => ({ ...d, total_cases: d.count })));
        setSummarySpikes(forecasts);
        setSummaryToday({
           total_today: Math.round((health.total_appointments || 0) / 30),
           by_disease: topDiseases.length > 0 ? [{ disease: topDiseases[0].name, count: topDiseases[0].count }] : [],
           date: 'Daily Avg'
        });
        setLowStock({
           critical: decisions.filter(d => d.priority === 'High').length,
           out_of_stock: decisions.filter(d => d.current_stock === 0).length
        });
        setTopMedicines(decisions.map(d => ({
           drug_name: d.drug,
           generic_name: `Restock: ${d.recommended_restock} (${d.status})`,
           total_quantity: d.current_stock
        })));
        
        setSummaryLoaded(true);
      })
      .catch(err => {
        console.error("Dashboard data load error:", err);
        setSummaryLoaded(true);
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

        <nav style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
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
          <div style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Top Medicines</div>
              <span style={{ fontSize: 20 }}>💊</span>
            </div>
            {topMedicines.slice(0, 4).map((m, i) => (
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
      `}</style>
    </div>
  );
}
