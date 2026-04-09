import React from 'react';
import styles from './Reports.module.css';

export default function TopMedicines({ data, days }) {
  if (!data || data.length === 0) {
    return <div className={styles.panelSubtitle}>No medicine data found.</div>;
  }

  return (
    <div className={styles.contentPanel}>
      <h3 className={styles.panelTitle}>Top {data.length} medicines</h3>
      <p className={styles.panelSubtitle}>
        Current stock from inventory &middot; Prescriptions written in last {days} days
      </p>
      
      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              {['#', 'Drug name', 'Generic name', 'Dosage type', 'Current stock', 'Prescriptions', 'Variants'].map(h => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i}>
                <td style={{ fontWeight: 700, color: '#9ca3af' }}>#{i + 1}</td>
                <td style={{ fontWeight: 600 }}>{row.drug_name}</td>
                <td style={{ color: '#6b7280' }}>{row.generic_name}</td>
                <td>{row.dosage_type}</td>
                <td>
                  <span style={{ fontWeight: 700, color: '#2563eb', fontSize: '14px' }}>
                    {(row.current_stock || 0).toLocaleString()}
                  </span>
                  <span style={{ fontSize: '11px', color: '#9ca3af', marginLeft: '4px' }}>units</span>
                </td>
                <td>
                  <span style={{ fontWeight: 600 }}>
                    {(row.prescription_count || 0).toLocaleString()}
                  </span>
                  <span style={{ fontSize: '11px', color: '#9ca3af', marginLeft: '4px' }}>
                    last {days}d
                  </span>
                </td>
                <td style={{ color: '#6b7280' }}>{row.variant_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
