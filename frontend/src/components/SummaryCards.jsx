import { useState, useEffect } from 'react';
import { fetchTrends, fetchSpikes, fetchTodaySummary } from '../api';
import { fetchLowStockAlerts } from '../api';

export default function SummaryCards({ days }) {
  const [trends,      setTrends]      = useState([]);
  const [spikes,      setSpikes]      = useState([]);
  const [todaySummary,setTodaySummary]= useState(null);
  const [criticalDrugs,setCritical]  = useState(0);
  const [loading,     setLoading]     = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchTrends(days),
      fetchSpikes(Math.max(days, 8), true),
      fetchTodaySummary(),           // ← dedicated endpoint, no date param
      fetchLowStockAlerts(50),       // threshold=50 for critical count
    ]).then(([tRes, sRes, todayRes, stockRes]) => {
      setTrends(tRes.data || []);
      setSpikes(sRes.data || []);
      setTodaySummary(todayRes.data);
      setCritical(stockRes.data?.out_of_stock || 0);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [days]);

  const totalPeriod = trends.reduce((s, t) => s + (t.total_cases || 0), 0);
  const spikeCount  = spikes.filter(s => s.is_spike).length;
  const topDisease  = trends[0]?.disease_name || '—';
  const todayCount  = todaySummary?.total_today || 0;
  const todayDate   = todaySummary?.date || '';

  // Answer your 5-card choice here — update based on what you select above
  const cards = [
    {
      label: 'Cases today',
      value: loading ? '—' : todayCount.toLocaleString(),
      sub:   todayDate,
      color: '#2563eb',
    },
    {
      label: `Cases (${days}d)`,
      value: loading ? '—' : totalPeriod.toLocaleString(),
      sub:   `Last ${days} days`,
      color: '#0891b2',
    },
    {
      label: 'Active spikes',
      value: loading ? '—' : spikeCount,
      sub:   'Diseases above threshold',
      color: '#dc2626',
    },
    {
      label: 'Top disease',
      value: loading ? '—' : topDisease,
      sub:   `Score: ${trends[0]?.trend_score || 0}`,
      color: '#7c3aed',
    },
    {
      label: 'Critical drugs',
      value: loading ? '—' : criticalDrugs,
      sub:   'Stock = 0',
      color: '#d97706',
    },
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(5, 1fr)',
      gap: 14, marginBottom: 24
    }}>
      {cards.map(card => (
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
      ))}
    </div>
  );
}
