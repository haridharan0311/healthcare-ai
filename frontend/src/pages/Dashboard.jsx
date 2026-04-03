import { useState, useEffect, useCallback } from 'react';
import {
  fetchTrends, fetchSpikes,
  fetchTrendComparison,
  fetchTopMedicines, fetchLowStockAlerts,
  fetchSeasonality, fetchDoctorTrends,
  fetchWeeklyReport, fetchMonthlyReport,
  getExportUrl
} from '../api';
import TrendChart       from '../components/TrendChart';
import SpikeAlerts      from '../components/SpikeAlerts';
import DistrictRestock  from '../components/DistrictRestock';
import SummaryCards     from '../components/SummaryCards';
import CsvPreviewModal  from '../components/CsvPreviewModal';

export default function Dashboard() {
  const [days]                        = useState(30);
  const [csvModal, setCsvModal]       = useState(null);
  const [refreshing, setRefreshing]   = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [refreshKey, setRefreshKey]   = useState(0);  // Force re-render of child components
  const [currentTime, setCurrentTime] = useState(new Date());  // Live timer

  const [topMedicines, setTopMedicines] = useState([]);
  const [lowStock, setLowStock] = useState({});
  const [seasonality, setSeasonality] = useState({});
  const [doctorTrends, setDoctorTrends] = useState([]);
  const [doctorSummary, setDoctorSummary] = useState({});
  const [weeklySummary, setWeeklySummary] = useState({});
  const [monthlySummary, setMonthlySummary] = useState({});

  const loadAll = useCallback(() => {
    setRefreshing(true);
    Promise.all([
      fetchTrends(days),
      fetchSpikes(Math.max(days, 8), true),
      fetchTrendComparison(days),
      fetchTopMedicines(days, 5),
      fetchLowStockAlerts(50),
      fetchSeasonality(365),
      fetchDoctorTrends(days, 10),
      fetchWeeklyReport(60),
      fetchMonthlyReport(365),
    ]).then(([trendsRes, spikesRes, trendCompRes, topMedRes, lowStockRes, seasonRes, doctorRes, weeklyRes, monthlyRes]) => {
      setTopMedicines(topMedRes.data || []);
      setLowStock(lowStockRes.data || {});
      setSeasonality(seasonRes.data || {});
      setDoctorSummary(doctorRes.data || {});
      setDoctorTrends((doctorRes.data && doctorRes.data.data) || []);
      setWeeklySummary(weeklyRes.data || {});
      setMonthlySummary(monthlyRes.data || {});
      setLastRefresh(new Date());
      setRefreshKey(k => k + 1);
      setRefreshing(false);
    }).catch(() => {
      setRefreshing(false);
    });
  }, [days]);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Auto-refresh every 30 seconds (matches live data generation interval)
  useEffect(() => {
    const interval = setInterval(loadAll, 30000);
    return () => clearInterval(interval);
  }, [loadAll]);

  // Live timer - update every second to show fresh time
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleCsvPreview = async (type, params = {}) => {
    const url = getExportUrl(type, { ...params });
    const res = await fetch(url);
    const text = await res.text();
    const rows = text.trim().split('\n').map(r =>
      r.split(',').map(c => c.replace(/^"|"$/g, '').trim())
    );
    setCsvModal({ type, rows, url });
  };

  const handleRefresh = () => {
    loadAll();
  };

  const formatRefreshTime = () => {
    const now = currentTime;  // Uses live updated time
    const diff = Math.round((now - lastRefresh) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return lastRefresh.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div style={{
      minHeight: '100vh', background: '#f5f6fa',
      fontFamily: 'system-ui, sans-serif'
    }}>
      {/* ── Top bar ── */}
      <div style={{
        background: '#fff', borderBottom: '1px solid #eee',
        padding: '0 32px', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        height: 60, position: 'sticky', top: 0, zIndex: 10
      }}>
        <span style={{ fontWeight: 600, fontSize: 18 }}>Healthcare AI</span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Auto-refresh indicator */}
          <div style={{
            fontSize: 12, color: '#9ca3af',
            display: 'flex', alignItems: 'center', gap: 6,
            paddingRight: 16, borderRight: '1px solid #e5e7eb'
          }}>
            <span style={{
              display: 'inline-block', width: 6, height: 6,
              borderRadius: '50%', background: refreshing ? '#fbbf24' : '#10b981'
            }} />
            {refreshing ? 'Updating...' : `Updated ${formatRefreshTime()}`}
          </div>

          {/* Manual refresh button */}
          <button
            onClick={() => handleRefresh()}
            disabled={refreshing}
            style={{
              padding: '6px 12px', borderRadius: 6, border: '1px solid #ddd',
              background: refreshing ? '#f3f4f6' : '#fff', fontSize: 13, color: '#444',
              cursor: refreshing ? 'not-allowed' : 'pointer',
              opacity: refreshing ? 0.6 : 1,
              display: 'flex', alignItems: 'center', gap: 4,
              transition: 'all 0.2s'
            }}
            title="Refresh and reload page"
          >
            <span style={{
              display: 'inline-block',
              animation: refreshing ? 'spin 1s linear infinite' : 'none'
            }}>
              ⟳
            </span>
            Refresh
          </button>

          <a href="/reports" style={{
            padding: '6px 16px', borderRadius: 6, border: '1px solid #ddd',
            background: '#fff', fontSize: 13, color: '#444',
            textDecoration: 'none', marginLeft: 8
          }}>
            Reports →
          </a>
          <a href="/admin-panel" style={{
            padding: '6px 16px', borderRadius: 6, border: '1px solid #ddd',
            background: '#fff', fontSize: 13, color: '#444',
            textDecoration: 'none'
          }}>
            Admin →
          </a>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ maxWidth: 1300, margin: '0 auto', padding: '28px 24px' }}>

        {/* Summary cards */}
        <SummaryCards key={refreshKey} days={days} />

        {/* Immediate insights from new analytics endpoints */}
        <section style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 12, marginBottom: 24
        }}>
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 16 }}>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>Top Medicines</div>
            {topMedicines.length === 0 ? (
              <div style={{ color: '#9ca3af', fontSize: 12 }}>No top medicine data yet.</div>
            ) : (
              topMedicines.slice(0, 4).map((m, i) => (
                <div key={`${m.drug_name}-${i}`} style={{ marginBottom: 6 }}>
                  <strong>{m.drug_name}</strong> ({m.generic_name || 'Generic'})
                  <span style={{ float: 'right', color: '#2563eb' }}>{(m.total_quantity || 0).toLocaleString()}</span>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>
                    {m.total_prescriptions} prescriptions · avg {m.avg_qty_per_rx}/rx
                  </div>
                </div>
              ))
            )}
          </div>
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 16 }}>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>Low Stock Snapshot</div>
            <div style={{ fontSize: 20, fontWeight: 650, color: '#dc2626' }}>
              {lowStock?.out_of_stock ?? 0}
            </div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>Drugs with critical stock levels</div>
          </div>
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 16 }}>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>Doctor Load (Top)</div>
            {doctorTrends.length === 0 ? (
              <div style={{ color: '#9ca3af', fontSize: 12 }}>No doctor trend data yet.</div>
            ) : (
              doctorTrends.slice(0, 4).map((d, i) => (
                <div key={`${d.doctor_id}-${i}`} style={{ marginBottom: 6 }}>
                  <strong>{d.doctor_name}</strong>
                  <span style={{ float: 'right', color: '#16a34a' }}>{d.case_count || 0}</span>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>{d.disease_name}</div>
                </div>
              ))
            )}

            <div style={{ marginTop: 10, fontSize: 11, color: '#6b7280' }}>
              <strong>{doctorSummary.total_rows ?? 0}</strong> doctors found &bull; min cases: <strong>{doctorSummary.min_cases ?? 0}</strong>
            </div>
          </div>
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 16 }}>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>Seasonality</div>
            {(!seasonality || !seasonality.seasons || Object.keys(seasonality.seasons).length === 0) ? (
              <div style={{ color: '#9ca3af', fontSize: 12 }}>No seasonality data yet.</div>
            ) : (
              Object.entries(seasonality.seasons).slice(0, 3).map(([key, value]) => (
                <div key={key} style={{ marginBottom: 6 }}>
                  <strong>{key}</strong>
                  <span style={{ float: 'right', color: '#7c3aed' }}>{value.total_cases}</span>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>Top: {value.top_disease || '—'}</div>
                </div>
              ))
            )}
          </div>
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 16 }}>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>Weekly Report</div>
            <div style={{ fontSize: 20, fontWeight: 650, color: '#2563eb' }}>
              {weeklySummary?.weeks?.length ?? 0}
            </div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>Weeks with case data</div>
          </div>
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 16 }}>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>Monthly Report</div>
            <div style={{ fontSize: 20, fontWeight: 650, color: '#16a34a' }}>
              {monthlySummary?.months?.length ?? 0}
            </div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>Months with case data</div>
          </div>
        </section>

        {/* Spike alerts */}
        <SpikeAlerts onExport={(range) => handleCsvPreview('spike-alerts', { days: range })} />

        {/* Trend chart + comparison */}
        <TrendChart globalDays={days} onExport={(d) => handleCsvPreview('disease-trends', { days: d })} />

        {/* District restock */}
        <DistrictRestock
          days={days}
          onExport={() => handleCsvPreview('restock')}
        />
      </div>

      {/* CSV preview modal */}
      {csvModal && (
        <CsvPreviewModal
          data={csvModal}
          onClose={() => setCsvModal(null)}
        />
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
