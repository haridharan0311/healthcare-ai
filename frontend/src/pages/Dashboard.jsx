import { useState, useEffect, useCallback } from 'react';
import {
  fetchTrends, fetchSpikes,
  fetchTrendComparison,
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

  const loadAll = useCallback(() => {
    setRefreshing(true);
    Promise.all([
      fetchTrends(days),
      fetchSpikes(Math.max(days, 8), true),
      fetchTrendComparison(days),
    ]).then(() => {
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
    // Full page reload after 1 second
    setTimeout(() => {
      window.location.reload();
    }, 500);
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
