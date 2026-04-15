import { useState, useEffect } from 'react';
import styles from './Reports.module.css';

function ProgressBar({ pct, color }) {
  return (
    <div style={{ background: '#f3f4f6', borderRadius: 4, height: 5, marginTop: 4 }}>
      <div style={{ background: color || '#2563eb', height: 5, borderRadius: 4, width: `${Math.min(Math.max(pct, 0), 100)}%`, transition: 'width 0.3s' }} />
    </div>
  );
}

function ReportTable({ diseases, color }) {
  if (!diseases || diseases.length === 0) return <div style={{ padding: 20, textAlign: 'center', color: '#9ca3af' }}>No disease data for this period.</div>;
  
  return (
    <div className={styles.tableContainer} style={{ marginTop: 20 }}>
      <table className={styles.dataTable}>
        <thead>
          <tr>
            <th style={{ width: 60 }}>#</th>
            <th>Disease name</th>
            <th style={{ textAlign: 'right' }}>Case count</th>
            <th style={{ width: '40%' }}>Distribution</th>
          </tr>
        </thead>
        <tbody>
          {diseases.map((d, i) => (
            <tr key={i}>
              <td style={{ fontWeight: 700, color: '#9ca3af' }}>{i + 1}</td>
              <td style={{ fontWeight: 600 }}>{d.disease_name}</td>
              <td style={{ textAlign: 'right', fontWeight: 700 }}>
                {d.case_count.toLocaleString()}
                <span style={{ fontSize: 11, color: '#9ca3af', fontWeight: 400, marginLeft: 6 }}>({d.percentage}%)</span>
              </td>
              <td>
                <ProgressBar pct={d.percentage} color={color} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function WeeklyReport({ data }) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  const weeks = data?.weeks || [];
  
  useEffect(() => {
    if (weeks.length > 0) setSelectedIndex(0);
  }, [data, weeks.length]);

  if (!data) return null;

  const selectedWeek = weeks[selectedIndex];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h3 className={styles.panelTitle}>Weekly disease case report</h3>
          <p className={styles.panelSubtitle}>{data.period} &middot; {weeks.length} weeks</p>
        </div>
        
        {weeks.length > 0 && (
          <div style={{ background: '#f8fafc', padding: 12, borderRadius: 12, border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 6, textTransform: 'uppercase' }}>Select week</div>
            <select 
              value={selectedIndex} 
              onChange={e => setSelectedIndex(Number(e.target.value))}
              style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #cbd5e1', background: '#fff', minWidth: 280, fontSize: 13, fontWeight: 600 }}
            >
              {weeks.map((w, i) => (
                <option key={i} value={i}>{w.week_label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {weeks.length === 0 ? (
        <div style={{ padding: 60, textAlign: 'center', color: '#9ca3af', border: '2px dashed #e2e8f0', borderRadius: 16 }}>No data for selected range</div>
      ) : selectedWeek && (
        <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', background: '#eff6ff', borderRadius: 12, borderLeft: '4px solid #2563eb' }}>
            <div>
              <div style={{ fontWeight: 800, fontSize: 16, color: '#1e40af' }}>{selectedWeek.week_label}</div>
              <div style={{ fontSize: 12, color: '#60a5fa', marginTop: 2 }}>{selectedWeek.week_start} to {selectedWeek.week_end}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#2563eb' }}>{selectedWeek.total_cases.toLocaleString()}</div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#60a5fa', textTransform: 'uppercase' }}>Total cases</div>
            </div>
          </div>
          <ReportTable diseases={selectedWeek.diseases} color="#2563eb" />
        </div>
      )}
    </div>
  );
}

export function MonthlyReport({ data }) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  const months = data?.months || [];
  
  useEffect(() => {
    if (months.length > 0) setSelectedIndex(0);
  }, [data, months.length]);

  if (!data) return null;

  const selectedMonth = months[selectedIndex];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h3 className={styles.panelTitle}>Monthly disease case report</h3>
          <p className={styles.panelSubtitle}>{data.period} &middot; {months.length} months</p>
        </div>
        
        {months.length > 0 && (
          <div style={{ background: '#f8fafc', padding: 12, borderRadius: 12, border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 6, textTransform: 'uppercase' }}>Select month</div>
            <select 
              value={selectedIndex} 
              onChange={e => setSelectedIndex(Number(e.target.value))}
              style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #cbd5e1', background: '#fff', minWidth: 280, fontSize: 13, fontWeight: 600 }}
            >
              {months.map((m, i) => (
                <option key={i} value={i}>{m.month_label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {months.length === 0 ? (
        <div style={{ padding: 60, textAlign: 'center', color: '#9ca3af', border: '2px dashed #e2e8f0', borderRadius: 16 }}>No data for selected range</div>
      ) : selectedMonth && (
        <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', background: '#f5f3ff', borderRadius: 12, borderLeft: '4px solid #7c3aed' }}>
            <div style={{ fontWeight: 800, fontSize: 18, color: '#5b21b6' }}>{selectedMonth.month_label}</div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#7c3aed' }}>{selectedMonth.total_cases.toLocaleString()}</div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase' }}>Total cases</div>
            </div>
          </div>
          <ReportTable diseases={selectedMonth.diseases} color="#7c3aed" />
        </div>
      )}
    </div>
  );
}
