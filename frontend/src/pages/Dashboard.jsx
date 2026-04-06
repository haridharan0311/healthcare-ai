import { useState, useEffect, useCallback } from 'react';
import {
  fetchTrends, fetchSpikes,
  fetchTopMedicines, fetchLowStockAlerts,
  fetchSeasonality, fetchDoctorTrends,
  fetchTodaySummary, fetchWhatChangedToday,
  getExportUrl
} from '../api';
import TrendChart       from '../components/TrendChart';
import SpikeAlerts      from '../components/SpikeAlerts';
import DistrictRestock  from '../components/DistrictRestock';
import SummaryCards     from '../components/SummaryCards';
import CsvPreviewModal  from '../components/CsvPreviewModal';

// ── Transform "What Changed Today" API response ──────────────────────────
function transformWhatChangedData(data) {
  const changes = [];

  // Total appointments
  if (data.total_appointments) {
    changes.push({
      title: 'Total Appointments',
      description: 'Appointments recorded today',
      value: `${data.total_appointments.toLocaleString()} appointments`
    });
  }

  // Top disease today
  if (data.today_by_disease && data.today_by_disease.length > 0) {
    const topDisease = data.today_by_disease[0];
    changes.push({
      title: 'Top Disease Today',
      description: `${topDisease.disease_name} cases recorded`,
      value: `${topDisease.count} cases`
    });
  }

  // Stock risks
  if (data.stock_risks) {
    const { critical_count, out_of_stock_count } = data.stock_risks;
    if (critical_count > 0) {
      changes.push({
        title: 'Critical Stock Alerts',
        description: 'Medicines at critical stock levels',
        value: `${critical_count.toLocaleString()} items`
      });
    }
    if (out_of_stock_count > 0) {
      changes.push({
        title: 'Out of Stock',
        description: 'Medicines completely out of stock',
        value: `${out_of_stock_count.toLocaleString()} items`
      });
    }
  }

  // Trend shifts
  if (data.trend_shifts && data.trend_shifts.top_gainers && data.trend_shifts.top_gainers.length > 0) {
    const topGainer = data.trend_shifts.top_gainers[0];
    changes.push({
      title: 'Rising Trend',
      description: `${topGainer.disease_name} showing growth`,
      value: `+${topGainer.growth_rate}% increase`
    });
  }

  return changes;
}

export default function Dashboard() {
  const [days]                        = useState(30);
  const [csvModal, setCsvModal]       = useState(null);
  const [refreshing, setRefreshing]   = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [refreshKey, setRefreshKey]   = useState(0);  // Force re-render of child components
  const [currentTime, setCurrentTime] = useState(new Date());  // Live timer

  const [summaryTrends, setSummaryTrends] = useState([]);
  const [summarySpikes, setSummarySpikes] = useState([]);
  const [summaryToday, setSummaryToday] = useState(null);
  const [summaryLoaded, setSummaryLoaded] = useState(false);
  const [topMedicines, setTopMedicines] = useState([]);
  const [lowStock, setLowStock] = useState({});
  const [seasonality, setSeasonality] = useState({});
  const [doctorTrends, setDoctorTrends] = useState([]);
  const [doctorSummary, setDoctorSummary] = useState({});
  const [whatChangedToday, setWhatChangedToday] = useState(null);

  const loadSummaryData = useCallback(() => {
    return Promise.allSettled([
      fetchTrends(days),
      fetchSpikes(Math.max(days, 8), true),
      fetchTodaySummary(),
      fetchLowStockAlerts(50),
    ]).then(([trendsRes, spikesRes, todayRes, stockRes]) => {
      setSummaryTrends(trendsRes.status === 'fulfilled' ? trendsRes.value.data || [] : []);
      setSummarySpikes(spikesRes.status === 'fulfilled' ? spikesRes.value.data || [] : []);
      setSummaryToday(todayRes.status === 'fulfilled' ? todayRes.value.data || {} : {});
      setLowStock(stockRes.status === 'fulfilled' ? stockRes.value.data || {} : {});
      setSummaryLoaded(true);
    });
  }, [days]);

  const loadInsights = useCallback(() => {
    return Promise.allSettled([
      fetchTopMedicines(days, 5),
      fetchSeasonality(365),
      fetchDoctorTrends(days, 10),
      fetchWhatChangedToday(),
    ]).then(([topMedRes, seasonRes, doctorRes, whatChangedRes]) => {
      setTopMedicines(topMedRes.status === 'fulfilled' ? topMedRes.value.data?.top_medicines || [] : []);
      setSeasonality(seasonRes.status === 'fulfilled' ? seasonRes.value.data || {} : {});
      setDoctorSummary(doctorRes.status === 'fulfilled' ? doctorRes.value.data || {} : {});
      setDoctorTrends(doctorRes.status === 'fulfilled' ? (doctorRes.value.data?.data || []) : []);
      setWhatChangedToday(whatChangedRes.status === 'fulfilled' ? (whatChangedRes.value.data ? transformWhatChangedData(whatChangedRes.value.data) : null) : null);
    });
  }, [days]);

  const loadAll = useCallback(() => {
    setRefreshing(true);
    return Promise.all([loadSummaryData(), loadInsights()])
      .then(() => {
        setLastRefresh(new Date());
        setRefreshKey(k => k + 1);
      })
      .finally(() => setRefreshing(false));
  }, [loadInsights, loadSummaryData]);

  useEffect(() => {
    loadSummaryData();
    const ticket = setTimeout(loadInsights, 200);
    return () => clearTimeout(ticket);
  }, [loadSummaryData, loadInsights]);

  // Auto-refresh every 2 minutes to reduce load
  useEffect(() => {
    const interval = setInterval(loadAll, 120000);
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
        <SummaryCards
          key={refreshKey}
          days={days}
          summary={{
            loaded: summaryLoaded,
            trends: summaryTrends,
            spikes: summarySpikes,
            todaySummary: summaryToday,
            stockAlerts: lowStock,
          }}
        />

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
              topMedicines.slice(0, 4).map((m, i) => {
                const avgPerRx = m.prescription_count ? (m.total_quantity / m.prescription_count).toFixed(1) : '0.0';
                return (
                  <div key={`${m.drug_name}-${i}`} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                      <div>
                        <strong>{m.drug_name}</strong>
                        <div style={{ fontSize: 11, color: '#6b7280' }}>{m.generic_name || 'Generic'}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#2563eb' }}>{(m.total_quantity || 0).toLocaleString()}</div>
                        <div style={{ fontSize: 11, color: '#6b7280' }}>units used</div>
                      </div>
                    </div>
                    <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
                      {(m.prescription_count || 0).toLocaleString()} prescriptions · avg {avgPerRx}/rx
                    </div>
                  </div>
                );
              })
            )}
          </div>
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 16 }}>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 12 }}>Low Stock Snapshot</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
              <div style={{ background: '#fef2f2', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 12, color: '#991b1b', marginBottom: 4 }}>Critical</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#b91c1c' }}>{(lowStock?.critical ?? 0).toLocaleString()}</div>
              </div>
              <div style={{ background: '#f8fafc', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 12, color: '#475569', marginBottom: 4 }}>Out of stock</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#1d4ed8' }}>{(lowStock?.out_of_stock ?? 0).toLocaleString()}</div>
              </div>
            </div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              {lowStock?.note || 'Includes urgent stock alerts and complete stock-outs.'}
            </div>
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
              Object.entries(seasonality.seasons).map(([key, value]) => (
                <div key={key} style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <strong>{key}</strong>
                    <span style={{ color: '#7c3aed', fontWeight: 700 }}>{value.total_cases.toLocaleString()}</span>
                  </div>
                  <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
                    Top disease: <strong>{value.top_disease || '—'}</strong> ({value.top_disease_count || 0} cases)
                  </div>
                </div>
              ))
            )}
            {seasonality?.note && (
              <div style={{ marginTop: 6, fontSize: 11, color: '#6b7280' }}>{seasonality.note}</div>
            )}
          </div>
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 16 }}>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>What Changed Today</div>
            {!whatChangedToday ? (
              <div style={{ color: '#9ca3af', fontSize: 12 }}>Loading today's changes...</div>
            ) : whatChangedToday.length === 0 ? (
              <div style={{ color: '#9ca3af', fontSize: 12 }}>No significant changes today.</div>
            ) : (
              whatChangedToday.slice(0, 3).map((change, i) => (
                <div key={i} style={{ marginBottom: 8, padding: 8, background: '#f8fafc', borderRadius: 6 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#374151' }}>{change.title}</div>
                  <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>{change.description}</div>
                  {change.value && (
                    <div style={{ fontSize: 11, color: '#059669', marginTop: 2, fontWeight: 500 }}>
                      {change.value}
                    </div>
                  )}
                </div>
              ))
            )}
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
