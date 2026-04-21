import React from 'react';

const COLORS = {
  cases: '#2563eb',   // Blue
  period: '#0891b2',  // Cyan
  spikes: '#dc2626',  // Red
  disease: '#7c3aed', // Purple
  inventory: '#ea580c'// Orange
};

const SkeletonCard = ({ color }) => (
  <div className="skeleton-card" style={{
    background: '#fff', 
    borderRadius: 16,
    padding: '24px', 
    border: '1px solid #f1f5f9',
    borderBottom: `3px solid ${color}`,
    display: 'flex', 
    flexDirection: 'column', 
    gap: 14,
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
    position: 'relative',
    overflow: 'hidden'
  }}>
    <div className="shimmer" />
    <div style={{ width: '40%', height: 12, background: '#f1f5f9', borderRadius: 4 }} />
    <div style={{ width: '80%', height: 32, background: '#f1f5f9', borderRadius: 4 }} />
    <div style={{ width: '60%', height: 12, background: '#f1f5f9', borderRadius: 4 }} />
  </div>
);

export default function SummaryCards({ days, summary = {} }) {
  const { loaded, todaySummary } = summary;

  if (!loaded) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 20, marginBottom: 32 }}>
        {Object.values(COLORS).map((c, i) => <SkeletonCard key={i} color={c} />)}
        <style>{`
          .skeleton-card { position: relative; overflow: hidden; }
          .shimmer {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent);
            animation: loading-shimmer 1.5s infinite;
          }
          @keyframes loading-shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
          }
        `}</style>
      </div>
    );
  }

  const totalWtd = todaySummary?.total_wtd || 0;
  const totalMtd = todaySummary?.total_mtd || 0;
  const activeOutbreaks = todaySummary?.active_outbreaks || 0;
  const topDisease = todaySummary?.top_disease || '—';

  const cards = [
    { label: 'Daily Admits', value: (todaySummary?.total_today || 0).toLocaleString(), sub: 'Today', color: COLORS.cases, icon: '📈' },
    { label: 'Weekly Vol', value: totalWtd.toLocaleString(), sub: 'Last 7 days', color: COLORS.period, icon: '🗓️' },
    { label: 'Monthly Vol', value: totalMtd.toLocaleString(), sub: 'Last 30 days', color: COLORS.inventory, icon: '📊' },
    { label: 'Outbreaks', value: activeOutbreaks.toLocaleString(), sub: 'Detected now', color: COLORS.spikes, icon: '🚨' },
    { label: 'Top Disease', value: topDisease, sub: 'Regional peak', color: COLORS.disease, icon: '🦠' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 20, marginBottom: 32 }}>
      {cards.map((card, idx) => (
        <div key={card.label} className="summary-card" style={{
          background: 'rgba(255, 255, 255, 0.9)',
          backdropFilter: 'blur(8px)',
          borderRadius: 16,
          padding: '24px',
          border: '1px solid rgba(255, 255, 255, 0.4)',
          borderBottom: `4px solid ${card.color}`,
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
          animation: `fadeInUp 0.5s ease forwards ${idx * 0.1}s`,
          opacity: 0,
          transform: 'translateY(10px)'
        }}>
          {/* Subtle Icon Glow */}
          <div style={{
            position: 'absolute', top: -10, right: -10, fontSize: 48, opacity: 0.08, transform: 'rotate(12deg)',
            userSelect: 'none'
          }}>
            {card.icon}
          </div>

          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: card.color }} />
            {card.label}
          </div>
          <div style={{ fontSize: 24, fontWeight: 900, color: '#0f172a', lineHeight: 1.1, marginBottom: 4, letterSpacing: '-0.5px' }}>
            {card.value}
          </div>
          <div style={{ fontSize: 12, color: '#64748b', fontWeight: 600, opacity: 0.8 }}>{card.sub}</div>
        </div>
      ))}
      <style>{`
        .summary-card:hover {
          transform: translateY(-4px) scale(1.02);
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
          background: #fff;
        }
        @keyframes fadeInUp {
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
