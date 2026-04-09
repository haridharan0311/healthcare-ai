import React from 'react';
import styles from './Reports.module.css';

function ProgressBar({ pct, color }) {
  return (
    <div style={{ background: '#f3f4f6', borderRadius: 4, height: 5, marginTop: 4 }}>
      <div style={{ background: color || '#2563eb', height: 5, borderRadius: 4, width: `${Math.min(Math.max(pct, 0), 100)}%`, transition: 'width 0.3s' }} />
    </div>
  );
}

function DiseaseList({ diseases, color }) {
  if (!diseases || diseases.length === 0) return null;
  return (
    <>
      {diseases.map((d, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: 2 }}>
            <span style={{ color: '#374151' }}>
              <span style={{ color: '#9ca3af', marginRight: 4 }}>#{i + 1}</span>
              {d.disease_name}
            </span>
            <span style={{ fontWeight: 600 }}>
              {(d.case_count || 0).toLocaleString()}
              <span style={{ color: '#9ca3af', fontWeight: 400, marginLeft: 4 }}>({d.percentage || 0}%)</span>
            </span>
          </div>
          <ProgressBar pct={d.percentage || 0} color={color} />
        </div>
      ))}
    </>
  );
}

export function WeeklyReport({ data }) {
  if (!data) return null;
  return (
    <div>
      <h3 className={styles.panelTitle}>Weekly disease case report</h3>
      <p className={styles.panelSubtitle}>
        {data.period}&nbsp;·&nbsp;{data.total_weeks} week{data.total_weeks !== 1 ? 's' : ''}
      </p>
      {(data.weeks || []).length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>No data for selected range</div>
      ) : (
        <div className={styles.gridContainer}>
          {data.weeks.map(week => (
            <div key={week.week_start} className={styles.card} style={{ borderTop: '4px solid #2563eb' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13, color: '#1e40af' }}>Week {week.week_number}</div>
                  <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{week.week_start} – {week.week_end}</div>
                </div>
                <div style={{ background: '#eff6ff', color: '#2563eb', padding: '4px 10px', borderRadius: 8, fontWeight: 700, fontSize: 14 }}>
                  {(week.total_cases || 0).toLocaleString()}
                </div>
              </div>
              <DiseaseList diseases={week.diseases} color="#2563eb" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function MonthlyReport({ data }) {
  if (!data) return null;
  return (
    <div>
      <h3 className={styles.panelTitle}>Monthly disease case report</h3>
      <p className={styles.panelSubtitle}>
        {data.period}&nbsp;·&nbsp;{data.total_months} month{data.total_months !== 1 ? 's' : ''}
      </p>
      {(data.months || []).length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>No data for selected range</div>
      ) : (
        <div className={styles.gridContainer}>
          {data.months.map(month => (
            <div key={month.month_key} className={styles.card} style={{ borderTop: '4px solid #7c3aed' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <div style={{ fontWeight: 700, fontSize: 14, color: '#5b21b6' }}>{month.month_label}</div>
                <div style={{ background: '#f5f3ff', color: '#7c3aed', padding: '4px 10px', borderRadius: 8, fontWeight: 700, fontSize: 14 }}>
                  {(month.total_cases || 0).toLocaleString()}
                </div>
              </div>
              <DiseaseList diseases={month.diseases} color="#7c3aed" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
