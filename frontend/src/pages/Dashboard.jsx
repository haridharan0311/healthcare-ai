import { useState, useEffect, useCallback } from 'react';
import {
  fetchTrends, fetchTimeSeries, fetchSpikes,
  fetchRestock, fetchTrendComparison, fetchDistrictRestock,
  fetchDistricts, getExportUrl
} from '../api';
import TrendChart       from '../components/TrendChart';
import SpikeAlerts      from '../components/SpikeAlerts';
import DistrictRestock  from '../components/DistrictRestock';
import SummaryCards     from '../components/SummaryCards';
import CsvPreviewModal  from '../components/CsvPreviewModal';

const DATE_OPTIONS = [
  { label: '1W',  days: 7   },
  { label: '2W',  days: 14  },
  { label: '1M',  days: 30  },
  { label: '3M',  days: 90  },
  { label: '6M',  days: 180 },
  { label: '1Y',  days: 365 },
];

export default function Dashboard() {
  const [days, setDays]               = useState(30);
  const [trends, setTrends]           = useState([]);
  const [comparison, setComparison]   = useState(null);
  const [spikes, setSpikes]           = useState([]);
  const [csvModal, setCsvModal]       = useState(null);
  const [loading, setLoading]         = useState(true);

  const loadAll = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetchTrends(days),
      fetchSpikes(Math.max(days, 8), true),
      fetchTrendComparison(days),
    ]).then(([tRes, sRes, cRes]) => {
      setTrends(tRes.data);
      setSpikes(sRes.data);
      setComparison(cRes.data);
      setLoading(false);
    });
  }, [days]);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Auto-refresh every 60 seconds
  useEffect(() => {
    const interval = setInterval(loadAll, 60000);
    return () => clearInterval(interval);
  }, [loadAll]);

  const handleCsvPreview = async (type) => {
    const url = getExportUrl(type, { days });
    const res = await fetch(url);
    const text = await res.text();
    const rows = text.trim().split('\n').map(r =>
      r.split(',').map(c => c.replace(/^"|"$/g, '').trim())
    );
    setCsvModal({ type, rows, url });
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
        <div>
          <span style={{ fontWeight: 600, fontSize: 18 }}>Healthcare AI</span>
          <span style={{ color: '#aaa', marginLeft: 12, fontSize: 13 }}>
            Tamil Nadu Analytics
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Global date range selector */}
          <div style={{ display: 'flex', gap: 4 }}>
            {DATE_OPTIONS.map(opt => (
              <button key={opt.label} onClick={() => setDays(opt.days)} style={{
                padding: '5px 12px', borderRadius: 6, border: 'none',
                cursor: 'pointer', fontSize: 12,
                fontWeight: days === opt.days ? 600 : 400,
                background: days === opt.days ? '#2563eb' : '#f0f0f0',
                color: days === opt.days ? '#fff' : '#555',
              }}>
                {opt.label}
              </button>
            ))}
          </div>
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
        <SummaryCards trends={trends} spikes={spikes} days={days} />

        {/* Spike alerts */}
        <SpikeAlerts
          data={spikes}
          days={days}
          loading={loading}
          onExport={() => handleCsvPreview('spike-alerts')}
        />

        {/* Trend chart + comparison */}
        <TrendChart
          days={days}
          comparison={comparison}
          onExport={() => handleCsvPreview('disease-trends')}
        />

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
    </div>
  );
}
