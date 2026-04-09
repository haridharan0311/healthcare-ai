import React from 'react';
import styles from './Reports.module.css';

export default function LowStockAlerts({ data, threshold }) {
  if (!data) return null;

  return (
    <div className={styles.contentPanel}>
      <h3 className={styles.panelTitle}>Low stock alerts</h3>
      <p className={styles.panelSubtitle}>
        Drugs where average stock per clinic &le; {threshold} units
      </p>
      {data.note && (
        <p style={{
          marginBottom: '16px', fontSize: '12px', color: '#374151',
          background: '#f0f9ff', border: '1px solid #bae6fd',
          padding: '8px 12px', borderRadius: '6px',
        }}>
          {data.note}
        </p>
      )}

      {/* Summary badges */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {[
          { label: 'Out of stock', key: 'out_of_stock', color: '#dc2626' },
          { label: 'Critical',     key: 'critical',     color: '#f97316' },
          { label: 'Low',          key: 'low',          color: '#eab308' },
          { label: 'Warning',      key: 'warning',      color: '#6b7280' },
        ].map(s => (
          <div key={s.key} style={{
            padding: '8px 18px', borderRadius: '8px',
            border: `1px solid ${s.color}40`,
            background: `${s.color}10`, fontSize: '13px',
          }}>
            <span style={{ color: s.color, fontWeight: 700, fontSize: '20px', marginRight: '6px' }}>
              {data[s.key] ?? 0}
            </span>
            <span style={{ color: '#6b7280' }}>{s.label}</span>
          </div>
        ))}
        <div style={{
          padding: '8px 18px', borderRadius: '8px',
          border: '1px solid #e5e7eb', background: '#f9fafb', fontSize: '13px',
        }}>
          <span style={{ fontWeight: 700, fontSize: '20px', marginRight: '6px' }}>
            {data.total_alerts ?? 0}
          </span>
          <span style={{ color: '#6b7280' }}>total alerts</span>
        </div>
      </div>

      {(data.alerts || []).length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af', fontSize: '14px' }}>
          No drugs with avg stock/clinic &le; {threshold}
        </div>
      ) : (
        <div className={styles.tableContainer}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                {['Drug', 'Generic', 'Avg/clinic', 'Total stock', 'Clinics', 'Threshold', 'Level', 'Action'].map(h => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.alerts.map((row, i) => {
                const ALERT_COLORS = {
                  out_of_stock: '#dc2626', critical: '#f97316', low: '#eab308', warning: '#9ca3af',
                };
                const c = ALERT_COLORS[row.alert_level] || '#9ca3af';
                return (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{row.drug_name}</td>
                    <td style={{ color: '#6b7280' }}>{row.generic_name}</td>
                    <td style={{ fontWeight: 700, color: c }}>{row.avg_stock_per_clinic}</td>
                    <td>{(row.total_stock || 0).toLocaleString()}</td>
                    <td>{row.clinic_count}</td>
                    <td>{row.threshold}</td>
                    <td>
                      <span style={{
                        background: `${c}20`, color: c,
                        padding: '2px 9px', borderRadius: '4px', fontSize: '11px', fontWeight: 700,
                      }}>
                        {row.alert_level.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      {row.restock_now && (
                        <span className={`${styles.badge} ${styles.badgeCritical}`}>RESTOCK NOW</span>
                      )}
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
