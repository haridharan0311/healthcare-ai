import React from 'react';
import styles from './Reports.module.css';

export default function MedicineDependency({ data, days }) {
  if (!data) return null;

  const list = Array.isArray(data) ? data : [];

  return (
    <div>
      <h3 className={styles.panelTitle}>Medicine Dependencies &amp; Co-occurrence</h3>
      <p className={styles.panelSubtitle}>
        Medicine usage patterns by disease over the last {days} days
      </p>

      {list.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>No dependency data available</div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 18, marginBottom: '32px' }}>
            {list.slice(0, 4).map((disease, i) => (
              <div key={i} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 18, background: '#f8fafc' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{disease.disease_name}</div>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>
                      {disease.unique_medicines} medicines · {disease.total_prescriptions?.toLocaleString()} prescriptions
                    </div>
                  </div>
                  <div style={{ background: '#dbeafe', color: '#1d4ed8', padding: '4px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600 }}>
                    Top {disease.medicines?.length || 0}
                  </div>
                </div>
                <div style={{ display: 'grid', gap: 8 }}>
                   {(disease.medicines || []).slice(0, 3).map((m, j) => (
                     <div key={j} style={{ fontSize: 12, display: 'flex', justifyContent: 'space-between' }}>
                       <span>{m.drug_name}</span>
                       <strong style={{ color: '#2563eb' }}>{m.prescriptions}</strong>
                     </div>
                   ))}
                </div>
              </div>
            ))}
          </div>

          <h4 className={styles.panelTitle} style={{ fontSize: '16px' }}>Detailed dependency Table</h4>
          <div className={styles.tableContainer}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  {['#', 'Disease', 'Total Prescriptions', 'Unique Medicines', 'Primary Medicine', 'Co-occurrence Count'].map(h => <th key={h}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {list.map((row, idx) => (
                  <tr key={idx}>
                    <td style={{ color: '#9ca3af', fontWeight: 600 }}>{idx + 1}</td>
                    <td style={{ fontWeight: 600 }}>{row.disease_name}</td>
                    <td>{(row.total_prescriptions || 0).toLocaleString()}</td>
                    <td>{row.unique_medicines}</td>
                    <td>
                      <span style={{ fontWeight: 500 }}>{row.medicines?.[0]?.drug_name || '—'}</span>
                    </td>
                    <td>
                      <span style={{ background: '#eff6ff', color: '#2563eb', padding: '2px 8px', borderRadius: '4px', fontWeight: 700, fontSize: '12px' }}>
                        {row.medicines?.[0]?.prescriptions || 0}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
