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
        <div style={{ display: 'grid', gap: 18 }}>
          {list.slice(0, 6).map((disease, i) => (
            <div key={i} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 18, background: '#f8fafc' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{disease.disease_name}</div>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>
                    {disease.unique_medicines} medicines · {disease.total_prescriptions?.toLocaleString()} prescriptions
                  </div>
                </div>
                <div style={{ background: '#dbeafe', color: '#1d4ed8', padding: '4px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600 }}>
                  Top medicines
                </div>
              </div>
              {disease.medicines?.length > 0 ? (
                <div style={{ display: 'grid', gap: 10 }}>
                  {disease.medicines.slice(0, 5).map((med, j) => (
                    <div key={j} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', borderRadius: 8, background: '#fff', border: '1px solid #e5e7eb' }}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{med.drug_name}</div>
                        <div style={{ fontSize: 11, color: '#6b7280' }}>{med.generic_name}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontWeight: 700 }}>{(med.prescriptions || 0).toLocaleString()}</div>
                        <div style={{ fontSize: 11, color: '#9ca3af' }}>prescriptions</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 12, color: '#9ca3af' }}>No medicines found for this disease.</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
