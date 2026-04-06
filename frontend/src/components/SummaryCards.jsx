import { useState, useEffect, useCallback } from 'react';
import { fetchTrends, fetchSpikes, fetchTodaySummary } from '../api';
import { fetchLowStockAlerts } from '../api';

// Skeleton loader for cards
const SkeletonCard = ({ color }) => (
  <div style={{
    background: '#fff', borderRadius: 12,
    padding: '18px 20px', border: '1px solid #e5e7eb',
    borderLeft: `4px solid ${color}`,
  }}>
    <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 8, height: 14, background: '#f0f0f0', borderRadius: 4, width: '70%' }} />
    <div style={{ fontSize: 26, fontWeight: 700, color: '#e5e7eb', lineHeight: 1.2, height: 32, background: '#f0f0f0', borderRadius: 4, marginBottom: 8, width: '80%' }} />
    <div style={{ fontSize: 11, color: '#e5e7eb', height: 14, background: '#f0f0f0', borderRadius: 4, width: '60%' }} />
  </div>
);

export default function SummaryCards({ days, summary = null }) {
  const [trends,      setTrends]      = useState([]);
  const [spikes,      setSpikes]      = useState([]);
  const [todaySummary,setTodaySummary]= useState(null);
  const [stockAlerts, setStockAlerts] = useState({ critical: 0, out_of_stock: 0, total_alerts: 0 });
  const [loading,     setLoading]     = useState(true);

  const summaryPassed = Boolean(summary);
  const summaryLoaded = summaryPassed && summary.loaded;

  const fetchData = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetchTrends(days).catch(e => { console.error('fetchTrends error:', e); return { data: [] }; }),
      fetchSpikes(Math.max(days, 8), true).catch(e => { console.error('fetchSpikes error:', e); return { data: [] }; }),
      fetchTodaySummary().catch(e => { console.error('fetchTodaySummary error:', e); return { data: {} }; }),
      fetchLowStockAlerts(50).catch(e => { console.error('fetchLowStockAlerts error:', e); return { data: { out_of_stock: 0, critical: 0, total_alerts: 0 } }; }),
    ]).then(([tRes, sRes, todayRes, stockRes]) => {
      setTrends(tRes.data || []);
      setSpikes(sRes.data || []);
      setTodaySummary(todayRes.data || {});
      setStockAlerts({
        critical: stockRes.data?.critical || 0,
        out_of_stock: stockRes.data?.out_of_stock || 0,
        total_alerts: stockRes.data?.total_alerts || 0,
      });
      setLoading(false);
    }).catch(err => {
      console.error('Error fetching summary data:', err);
      setLoading(false);
    });
  }, [days]);

  const currentTrends = summaryPassed ? summary.trends || [] : trends;
  const currentSpikes = summaryPassed ? summary.spikes || [] : spikes;
  const currentToday  = summaryPassed ? summary.todaySummary || {} : todaySummary;
  const currentStock  = summaryPassed ? summary.stockAlerts || { critical: 0, out_of_stock: 0, total_alerts: 0 } : stockAlerts;
  const currentLoading = summaryPassed ? !summaryLoaded : loading;

  useEffect(() => {
    if (summaryPassed) {
      return;
    }
    fetchData();
  }, [fetchData, summaryPassed]);

  useEffect(() => {
    if (summaryPassed) return;
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData, summaryPassed]);

  const totalPeriod = currentTrends.reduce((s, t) => s + (t.total_cases || 0), 0);
  const spikeCount  = currentSpikes.filter(s => s.is_spike).length;
  const topDisease  = currentTrends[0]?.disease_name || '—';
  const todayCount  = currentToday?.total_today || 0;
  const todayDate   = currentToday?.date || '';

  const colors = ['#2563eb', '#0891b2', '#dc2626', '#7c3aed', '#d97706'];

  const cards = [
    {
      label: 'Cases today',
      value: currentLoading ? '—' : todayCount.toLocaleString(),
      sub:   todayDate,
      color: '#2563eb',
    },
    {
      label: `Cases (${days}d)`,
      value: currentLoading ? '—' : totalPeriod.toLocaleString(),
      sub:   `Last ${days} days`,
      color: '#0891b2',
    },
    {
      label: 'Active spikes',
      value: currentLoading ? '—' : spikeCount,
      sub:   'Diseases above threshold',
      color: '#dc2626',
    },
    {
      label: 'Top disease',
      value: currentLoading ? '—' : topDisease,
      sub:   `Score: ${currentTrends[0]?.trend_score || 0}`,
      color: '#7c3aed',
    },
    {
      label: 'Stock alerts',
      value: currentLoading ? '—' : currentStock.total_alerts?.toLocaleString(),
      sub:   currentLoading ? '—' : `${currentStock.critical} critical · ${currentStock.out_of_stock} out of stock`,
      color: '#d97706',
    },
  ];

  return (
    <div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: 14, marginBottom: 24
      }}>
        {currentLoading ? (
          colors.map((color) => (
            <SkeletonCard key={color} color={color} />
          ))
        ) : (
          cards.map(card => (
            <div key={card.label} style={{
              background: '#fff', borderRadius: 12,
              padding: '18px 20px', border: '1px solid #e5e7eb',
              borderLeft: `4px solid ${card.color}`,
            }}>
              <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                {card.label}
              </div>
              <div style={{ fontSize: 26, fontWeight: 700, color: card.color, lineHeight: 1.2 }}>
                {card.value}
              </div>
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>{card.sub}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
