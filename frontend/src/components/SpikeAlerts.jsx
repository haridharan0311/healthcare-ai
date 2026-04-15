import { useState, useEffect } from 'react';
import { fetchSpikes } from '../api';

export default function SpikeAlerts({ onExport }) {
  const [data,    setData]    = useState([]);
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fixed 8-day range logic
  useEffect(() => {
    setLoading(true);
    fetchSpikes(true).then(res => {
      setData(res.data || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const spikes  = data.filter(a => a.is_spike);
  const normal  = data.filter(a => !a.is_spike);
  const visible = showAll ? [...spikes, ...normal] : spikes;

  return (
    <div style={{ 
      background: '#fff', 
      borderRadius: 16, 
      padding: 24, 
      marginBottom: 24, 
      border: '1px solid #f1f5f9',
      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#1e293b' }}>Active Outbreak Monitoring</h2>
          {spikes.length > 0 && (
            <span style={{ 
              background: '#fee2e2', color: '#dc2626', borderRadius: 20, 
              padding: '2px 12px', fontSize: 12, fontWeight: 700, border: '1px solid #fecaca' 
            }}>
              {spikes.length} Alert{spikes.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setShowAll(s => !s)}
            style={{
              padding: '6px 14px', borderRadius: 8, border: '1px solid #e2e8f0',
              background: '#fff', cursor: 'pointer', fontSize: 13, color: '#444',
              fontWeight: 600
            }}
          >
            {showAll ? 'Spikes only' : 'Show all'}
          </button>
          <button
            onClick={() => onExport && onExport(8)}
            style={{
              padding: '6px 14px', borderRadius: 8, border: 'none',
              background: '#f1f5f9', cursor: 'pointer', fontSize: 13, color: '#475569',
              fontWeight: 600
            }}
          >
            Export
          </button>
        </div>
      </div>


      {loading ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8' }}>Analyzing baseline...</div>
      ) : visible.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: 12 }}>
          No anomalies detected in the current 8-day window.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f1f5f9', fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
                <th style={{ padding: '12px 16px' }}>Disease</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>Baseline (7d)</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>Today</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>Std Dev</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>Threshold</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {visible.map(a => (
                <tr 
                  key={a.disease_name} 
                  style={{ 
                    borderBottom: '1px solid #f8fafc',
                    background: a.is_spike ? '#fffafb' : 'transparent',
                    transition: 'background 0.2s'
                  }}
                >
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ 
                        width: 8, height: 8, borderRadius: '50%', 
                        background: a.is_spike ? '#dc2626' : '#94a3b8' 
                      }} />
                      <span style={{ fontWeight: 600, color: a.is_spike ? '#991b1b' : '#334155' }}>{a.disease_name}</span>
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', color: '#64748b', fontSize: 13 }}>{a.mean_last_7_days}</td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 700, color: a.is_spike ? '#dc2626' : '#1e293b' }}>{a.today_count}</td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', color: '#64748b', fontSize: 13 }}>{a.std_dev}</td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', color: '#64748b', fontSize: 13 }}>{a.threshold}</td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <span style={{ 
                      fontSize: 11, fontWeight: 700, padding: '4px 12px', borderRadius: 6,
                      background: a.is_spike ? '#dc2626' : '#f1f5f9',
                      color: a.is_spike ? '#fff' : '#64748b'
                    }}>
                      {a.is_spike ? 'SPIKE' : 'NORMAL'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
