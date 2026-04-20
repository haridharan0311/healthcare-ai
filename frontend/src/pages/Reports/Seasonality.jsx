import React from 'react';
import styles from './Reports.module.css';

const SEASON_COLORS = { Summer: '#f97316', Monsoon: '#2563eb', Winter: '#7c3aed', All: '#6b7280' };

function ProgressBar({ pct, color }) {
  return (
    <div style={{ background: '#f3f4f6', borderRadius: 4, height: 5, marginTop: 4 }}>
      <div style={{ background: color || '#2563eb', height: 5, borderRadius: 4, width: `${pct}%`, transition: 'width 0.3s' }} />
    </div>
  );
}

export default function Seasonality({ data }) {
  if (!data) return null;

  return (
    <div className={styles.contentPanel}>
      <h3 className={styles.panelTitle}>Disease occurrence by season</h3>
      <p className={styles.panelSubtitle}>{data.period}</p>
      
      <div style={{
        marginBottom: '20px', fontSize: '13px', color: '#374151',
        background: '#f0f9ff', border: '1px solid #bae6fd',
        padding: '12px 14px', borderRadius: '8px', lineHeight: 1.6,
      }}>
        <strong>How to read this:</strong> Each card shows diseases grouped by their season in the database.
      </div>

      <div className={styles.gridContainer}>
        {Object.entries(data.seasons || {}).map(([season, info]) => {
          const color = SEASON_COLORS[season] || '#6b7280';
          return (
            <div key={season} className={styles.card} style={{ borderTop: `4px solid ${color}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ fontWeight: 700, fontSize: '16px', color }}>{season}</div>
                <div style={{ background: `${color}15`, color, padding: '2px 8px', borderRadius: '8px', fontWeight: 600, fontSize: '12px' }}>
                   {(info.total_cases || 0).toLocaleString()} cases
                </div>
              </div>
              <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '16px' }}>
                Top: <strong>{info.top_disease}</strong> &middot; {info.top_disease_count}
              </div>

              {info.diseases.map((d, i) => (
                <div key={i} style={{ marginBottom: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                    <span>{d.disease_name}</span>
                    <strong>{(d.case_count || 0).toLocaleString()} ({d.percentage || 0}%)</strong>
                  </div>
                  <ProgressBar pct={d.percentage || 0} color={color} />
                </div>
              ))}
            </div>
          );
        })}
      </div>

    </div>
  );
}
