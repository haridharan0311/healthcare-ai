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

  const handleCsvPreview = async (type, params = {}) => {
    const url = getExportUrl(type, { ...params });
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
        <span style={{ fontWeight: 600, fontSize: 18 }}>Healthcare AI</span>
        <div style={{ display: 'flex', gap: 8 }}>
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
        <SummaryCards days={days} />

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
    </div>
  );
}
