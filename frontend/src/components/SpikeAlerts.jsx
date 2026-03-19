import { useState, useEffect } from 'react';
import axios from 'axios';

const BASE = 'http://localhost:8000/api';

const DATE_OPTIONS = [
  { label: '8D',  days: 8   },
  { label: '2W',  days: 14  },
  { label: '3W',  days: 21  },
  { label: '1M',  days: 30  },
  { label: '2M',  days: 60  },
  { label: '3M',  days: 90  },
  { label: '6M',  days: 180 },
  { label: '1Y',  days: 365 },
];

export default function SpikeAlerts() {
  const [selected, setSelected] = useState('8D');
  const [alerts, setAlerts]     = useState([]);
  const [loading, setLoading]   = useState(true);

  const currentOption = DATE_OPTIONS.find(o => o.label === selected);
  const days = currentOption?.days ?? 8;

  useEffect(() => {
    setLoading(true);
    axios.get(`${BASE}/spike-alerts/?all=true&days=${days}`)
      .then(res => {
        setAlerts(res.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [days]);

  const spikes = alerts.filter(a => a.is_spike);
  const normal = alerts.filter(a => !a.is_spike);

  return (
    <div style={{
      background: '#fff', borderRadius: 12, padding: 24,
      marginBottom: 24, border: '1px solid #eee'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 500 }}>Spike alerts</h2>
          {!loading && spikes.length > 0 && (
            <span style={{
              background: '#E24B4A', color: '#fff',
              borderRadius: 20, padding: '2px 10px',
              fontSize: 12, fontWeight: 500
            }}>
              {spikes.length} spike{spikes.length > 1 ? 's' : ''}
            </span>
          )}
        </div>

        {/* Date range pills */}
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {DATE_OPTIONS.map(opt => (
            <button
              key={opt.label}
              onClick={() => setSelected(opt.label)}
              style={{
                padding: '5px 12px', borderRadius: 6,
                border: 'none', cursor: 'pointer', fontSize: 12,
                fontWeight: selected === opt.label ? 500 : 400,
                background: selected === opt.label ? '#E24B4A' : '#f0f0f0',
                color: selected === opt.label ? '#fff' : '#555',
                transition: 'all 0.15s',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Baseline info */}
      <p style={{ margin: '0 0 14px', fontSize: 12, color: '#999' }}>
        Baseline: last {days} days — spike if today &gt; mean + 2×std dev
      </p>

      {loading ? (
        <div style={{ padding: '24px 0', color: '#aaa', textAlign: 'center' }}>Loading...</div>
      ) : alerts.length === 0 ? (
        <div style={{ padding: '24px 0', color: '#aaa', textAlign: 'center' }}>No data for this period</div>
      ) : (
        <>
          {/* Column headers */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 90px 90px 90px 90px 100px',
            padding: '6px 16px', marginBottom: 4,
            fontSize: 11, fontWeight: 500, color: '#aaa',
            textTransform: 'uppercase', letterSpacing: '0.5px'
          }}>
            <span>Disease</span>
            <span style={{ textAlign: 'right' }}>Count ({selected})</span>
            <span style={{ textAlign: 'right' }}>Today</span>
            <span style={{ textAlign: 'right' }}>Mean</span>
            <span style={{ textAlign: 'right' }}>Threshold</span>
            <span style={{ textAlign: 'right' }}>Status</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[...spikes, ...normal].map(a => (
              <div key={a.disease_name} style={{
                display: 'grid',
                gridTemplateColumns: '1fr 90px 90px 90px 90px 100px',
                alignItems: 'center',
                padding: '12px 16px', borderRadius: 8,
                background: a.is_spike ? '#FCEBEB' : '#f8f8f8',
                border: `1px solid ${a.is_spike ? '#F09595' : '#ebebeb'}`,
              }}>
                {/* Disease name */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{
                    width: 9, height: 9, borderRadius: '50%', flexShrink: 0,
                    background: a.is_spike ? '#E24B4A' : '#c0c0c0',
                    display: 'inline-block'
                  }} />
                  <span style={{
                    fontWeight: a.is_spike ? 500 : 400,
                    fontSize: 14,
                    color: a.is_spike ? '#A32D2D' : '#444'
                  }}>
                    {a.disease_name}
                  </span>
                  {a.is_spike && (
                    <span style={{
                      fontSize: 10, background: '#E24B4A', color: '#fff',
                      borderRadius: 4, padding: '1px 6px',
                      fontWeight: 600, letterSpacing: '0.5px'
                    }}>SPIKE</span>
                  )}
                </div>

                {/* Period count */}
                <div style={{ textAlign: 'right' }}>
                  <span style={{
                    fontSize: 13, fontWeight: 500,
                    color: a.is_spike ? '#A32D2D' : '#333',
                    background: a.is_spike ? '#F7C1C1' : '#e8e8e8',
                    padding: '2px 8px', borderRadius: 4
                  }}>
                    {a.period_count}
                  </span>
                </div>

                {/* Today */}
                <div style={{ textAlign: 'right', fontSize: 13, color: a.is_spike ? '#A32D2D' : '#555' }}>
                  <strong>{a.today_count}</strong>
                </div>

                {/* Mean */}
                <div style={{ textAlign: 'right', fontSize: 13, color: '#555' }}>
                  <strong>{a.mean_last_7_days}</strong>
                </div>

                {/* Threshold */}
                <div style={{ textAlign: 'right', fontSize: 13, color: '#555' }}>
                  <strong>{a.threshold}</strong>
                </div>

                {/* Status badge */}
                <div style={{ textAlign: 'right' }}>
                  {a.is_spike ? (
                    <span style={{
                      fontSize: 11, background: '#E24B4A', color: '#fff',
                      borderRadius: 6, padding: '3px 10px', fontWeight: 500
                    }}>Spike</span>
                  ) : (
                    <span style={{
                      fontSize: 11, background: '#e8e8e8', color: '#777',
                      borderRadius: 6, padding: '3px 10px'
                    }}>Normal</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}