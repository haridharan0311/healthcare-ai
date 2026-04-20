import React from 'react';

const COLORS = {
  cases: '#2563eb',   // Blue
  period: '#0891b2',  // Cyan
  spikes: '#dc2626',  // Red
  disease: '#7c3aed', // Purple
  inventory: '#ea580c'// Orange
};

const SkeletonCard = ({ color }) => (
  <div style={{
    background: '#fff', borderRadius: 8,
    padding: '24px', border: '1px solid #e2e8f0',
    borderBottom: `2px solid ${color}`,
    display: 'flex', flexDirection: 'column', gap: 12
  }}>
    <div style={{ width: '40%', height: 14, background: '#f1f5f9', borderRadius: 4 }} />
    <div style={{ width: '70%', height: 32, background: '#f1f5f9', borderRadius: 4 }} />
    <div style={{ width: '60%', height: 14, background: '#f1f5f9', borderRadius: 4 }} />
  </div>
);

export default function SummaryCards({ days, summary = {} }) {
  const { loaded, spikes, todaySummary } = summary;

  if (!loaded) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginBottom: 28 }}>
        {Object.values(COLORS).map((c, i) => <SkeletonCard key={i} color={c} />)}
      </div>
    );
  }

  const totalWtd = todaySummary?.total_wtd || 0;
  const totalMtd = todaySummary?.total_mtd || 0;
  const activeOutbreaks = todaySummary?.active_outbreaks || 0;
  const topDisease = todaySummary?.top_disease || '—';

  const cards = [
    {
      label: 'Daily Admissions',
      value: (todaySummary?.total_today || 0).toLocaleString(),
      sub: 'New appointments today',
      color: COLORS.cases,
      icon: '📈'
    },
    {
      label: 'Weekly Throughput',
      value: totalWtd.toLocaleString(),
      sub: 'This week',
      color: COLORS.period,
      icon: '🗓️'
    },
    {
      label: 'Monthly Throughput',
      value: totalMtd.toLocaleString(),
      sub: 'This month',
      color: COLORS.inventory,
      icon: '📊'
    },
    {
      label: 'Active Outbreaks',
      value: activeOutbreaks.toLocaleString(),
      sub: 'Security alerts detected',
      color: COLORS.spikes,
      icon: '🚨'
    },
    {
      label: 'Dominant Pathology',
      value: topDisease,
      sub: 'Highest prevalence currently',
      color: COLORS.disease,
      icon: '🦠'
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginBottom: 28 }}>
      {cards.map(card => (
        <div key={card.label} style={{
          background: '#fff', borderRadius: 8,
          padding: '24px', border: '1px solid #e2e8f0',
          borderBottom: `2px solid ${card.color}`,
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)',
          transition: 'transform 0.2s, box-shadow 0.2s',
          cursor: 'default',
          position: 'relative',
          overflow: 'hidden'
        }}>
          {/* Accent decoration */}
          <div style={{
            position: 'absolute', top: -10, right: -10, fontSize: 40, opacity: 0.05, transform: 'rotate(15deg)'
          }}>
            {card.icon}
          </div>

          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6 }}>
            {card.label}
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', lineHeight: 1.1, marginBottom: 4 }}>
            {card.value}
          </div>
          <div style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>{card.sub}</div>
        </div>
      ))}
    </div>
  );
}
