export default function SummaryCards({ trends, spikes, days }) {
  const totalCases   = trends.reduce((s, t) => s + t.total_cases, 0);
  const spikeCount   = spikes.filter(s => s.is_spike).length;
  const topDisease   = trends[0]?.disease_name || '—';
  const highRisk     = trends.filter(t => t.trend_score > 50).length;

  const cards = [
    { label: 'Total cases',    value: totalCases.toLocaleString(), color: '#2563eb', sub: `Last ${days} days` },
    { label: 'Active spikes',  value: spikeCount,                  color: '#dc2626', sub: 'Diseases above threshold' },
    { label: 'Top disease',    value: topDisease,                   color: '#7c3aed', sub: 'Highest trend score' },
    { label: 'High risk',      value: highRisk,                     color: '#d97706', sub: 'Score > 50' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
      {cards.map(card => (
        <div key={card.label} style={{
          background: '#fff', borderRadius: 12, padding: '20px 24px',
          border: '1px solid #eee',
          borderLeft: `4px solid ${card.color}`
        }}>
          <div style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>{card.label}</div>
          <div style={{ fontSize: 28, fontWeight: 600, color: card.color }}>{card.value}</div>
          <div style={{ fontSize: 11, color: '#aaa', marginTop: 4 }}>{card.sub}</div>
        </div>
      ))}
    </div>
  );
}