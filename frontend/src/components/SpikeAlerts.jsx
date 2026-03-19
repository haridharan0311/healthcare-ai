import { useState, useEffect } from 'react';
import { fetchSpikes } from '../api';

export default function SpikeAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSpikes().then(res => {
      setAlerts(res.data);
      setLoading(false);
    });
  }, []);

  const spikes  = alerts.filter(a => a.is_spike);
  const normal  = alerts.filter(a => !a.is_spike);

  return (
    <div style={{ background: 'var(--card-bg)', borderRadius: 12, padding: 24, marginBottom: 24 }}>
      <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 500 }}>
        Spike alerts
        {spikes.length > 0 && (
          <span style={{
            marginLeft: 10, background: '#E24B4A', color: '#fff',
            borderRadius: 20, padding: '2px 10px', fontSize: 13, fontWeight: 500
          }}>
            {spikes.length} spike{spikes.length > 1 ? 's' : ''}
          </span>
        )}
      </h2>

      {loading ? (
        <p style={{ color: '#888' }}>Loading...</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[...spikes, ...normal].map(a => (
            <div key={a.disease_name} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px', borderRadius: 8,
              background: a.is_spike ? '#FCEBEB' : '#f5f5f5',
              border: `1px solid ${a.is_spike ? '#F09595' : '#e0e0e0'}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: a.is_spike ? '#E24B4A' : '#b0b0b0',
                  display: 'inline-block', flexShrink: 0
                }} />
                <span style={{
                  fontWeight: a.is_spike ? 500 : 400,
                  color: a.is_spike ? '#A32D2D' : '#555'
                }}>
                  {a.disease_name}
                </span>
                {a.is_spike && (
                  <span style={{
                    fontSize: 11, background: '#E24B4A', color: '#fff',
                    borderRadius: 4, padding: '1px 6px', fontWeight: 500
                  }}>SPIKE</span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 20, fontSize: 13, color: '#666' }}>
                <span>Today: <strong style={{ color: a.is_spike ? '#A32D2D' : '#333' }}>{a.today_count}</strong></span>
                <span>Mean: <strong>{a.mean_last_7_days}</strong></span>
                <span>Threshold: <strong>{a.threshold}</strong></span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
