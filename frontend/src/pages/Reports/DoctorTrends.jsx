import React from 'react';
import styles from './Reports.module.css';

const SEASON_COLORS = { Summer: '#f97316', Monsoon: '#2563eb', Winter: '#7c3aed', All: '#6b7280' };

export default function DoctorTrends({ data, days }) {
  if (!data) return null;

  return (
    <div>
      <h3 className={styles.panelTitle}>Doctor-wise disease cases</h3>
      <p className={styles.panelSubtitle}>
        {data.period || `Last ${days} days`}
        &nbsp;· {data.total_rows || 0} entries with &ge; {data.min_cases || 10} cases
      </p>

      {(data.data || []).length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af', fontSize: '14px' }}>
          No doctors with {data.min_cases || 10}+ cases in this period
        </div>
      ) : (
        <div className={styles.tableContainer}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                {['#', 'Doctor', 'Disease', 'Season', 'Cases'].map(h => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data.data || []).map((row, i) => {
                const sc = SEASON_COLORS[row.season] || '#6b7280';
                return (
                  <tr key={i}>
                    <td style={{ color: '#9ca3af', fontWeight: 600 }}>{i + 1}</td>
                    <td style={{ fontWeight: 500 }}>{row.doctor_name}</td>
                    <td>{row.disease_name}</td>
                    <td>
                      <span style={{
                        background: `${sc}15`, color: sc,
                        padding: '2px 8px', borderRadius: '4px',
                        fontSize: '11px', fontWeight: 600,
                      }}>
                        {row.season}
                      </span>
                    </td>
                    <td>
                      <span style={{
                        background: '#eff6ff', color: '#2563eb',
                        padding: '3px 12px', borderRadius: '12px',
                        fontWeight: 700, fontSize: '13px',
                      }}>
                        {row.case_count}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
