import { useState, useEffect } from 'react';
import { fetchSpikes } from '../api';

const RANGE_OPTIONS = [
  { label: '8D',  days: 8   },
  { label: '2W',  days: 14  },
  { label: '3W',  days: 21  },
  { label: '1M',  days: 30  },
  { label: '2M',  days: 60  },
  { label: '3M',  days: 90  },
  { label: '6M',  days: 180 },
  { label: '1Y',  days: 365 },
];

export default function SpikeAlerts({ onExport }) {
  // SpikeAlerts owns its range — NOT driven by global days
  const [range,   setRange]   = useState(8);
  const [data,    setData]    = useState([]);
  const [showAll, setShowAll] = useState(true);
  const [loading, setLoading] = useState(true);

  // Re-fetch whenever local range changes
  useEffect(() => {
    setLoading(true);
    fetchSpikes(range, true).then(res => {
      setData(res.data || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [range]); // ← ONLY local range, not global days

  const spikes  = data.filter(a => a.is_spike);
  const normal  = data.filter(a => !a.is_spike);
  const visible = showAll ? [...spikes, ...normal] : spikes;

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 24, marginBottom: 24, border: '1px solid #e5e7eb' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>Spike alerts</h2>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Local range pills — independent of global days */}
          <div style={{ display: 'flex', gap: 3 }}>
            {RANGE_OPTIONS.map(opt => (
              <button
                key={opt.label}
                onClick={() => setRange(opt.days)}
                style={{
                  padding: '4px 10px', borderRadius: 5, border: 'none',
                  cursor: 'pointer', fontSize: 11,
                  fontWeight: range === opt.days ? 600 : 400,
                  background: range === opt.days ? '#dc2626' : '#f3f4f6',
                  color: range === opt.days ? '#fff' : '#555',
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowAll(s => !s)}
            style={{
              padding: '4px 12px', borderRadius: 5, border: '1px solid #e5e7eb',
              background: '#fff', cursor: 'pointer', fontSize: 12, color: '#555'
            }}
          >
            {showAll ? 'Spikes only' : 'Show all'}
          </button>
          <button
            onClick={() => onExport && onExport(range)}
            style={{
              padding: '4px 12px', borderRadius: 5, border: 'none',
              background: '#f3f4f6', cursor: 'pointer', fontSize: 12
            }}
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Formula — shows actual baseline window */}
      <div style={{
        fontSize: 11, color: '#6b7280', marginBottom: 14,
        padding: '6px 12px', background: '#f9fafb', borderRadius: 6, fontFamily: 'monospace'
      }}>
        Formula: spike if today_count &gt; mean(last {range - 1} days) + 2 × std_dev
        &nbsp;·&nbsp; Baseline: {range} days &nbsp;·&nbsp;
        {loading ? 'Loading...' : `${data.length} diseases · ${spikes.length} spikes`}
      </div>

      {loading ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>Loading...</div>
      ) : visible.length === 0 ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No data for this range</div>
      ) : (
        <>
          {/* Column headers */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1.4fr 80px 70px 80px 70px 90px 80px',
            padding: '6px 14px', fontSize: 10, color: '#9ca3af',
            fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px'
          }}>
            <span>Disease</span>
            <span style={{ textAlign: 'right' }}>Count ({range}d)</span>
            <span style={{ textAlign: 'right' }}>Today</span>
            <span style={{ textAlign: 'right' }}>Mean</span>
            <span style={{ textAlign: 'right' }}>Std Dev</span>
            <span style={{ textAlign: 'right' }}>Threshold</span>
            <span style={{ textAlign: 'right' }}>Status</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginTop: 4 }}>
            {visible.map(a => (
              <div
                key={a.disease_name}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1.4fr 80px 70px 80px 70px 90px 80px',
                  alignItems: 'center',
                  padding: '10px 14px', borderRadius: 8,
                  background: a.is_spike ? '#fef2f2' : '#fafafa',
                  border: `1px solid ${a.is_spike ? '#fecaca' : '#e5e7eb'}`,
                }}
              >
                {/* Disease name */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: a.is_spike ? '#dc2626' : '#d1d5db',
                    display: 'inline-block', flexShrink: 0
                  }} />
                  <span style={{
                    fontWeight: a.is_spike ? 600 : 400, fontSize: 13,
                    color: a.is_spike ? '#991b1b' : '#374151'
                  }}>
                    {a.disease_name}
                  </span>
                  {a.is_spike && (
                    <span style={{
                      fontSize: 9, background: '#dc2626', color: '#fff',
                      borderRadius: 3, padding: '1px 5px', fontWeight: 700, letterSpacing: '0.5px'
                    }}>SPIKE</span>
                  )}
                </div>

                {/* Period count */}
                <div style={{ textAlign: 'right' }}>
                  <span style={{
                    background: a.is_spike ? '#fee2e2' : '#f3f4f6',
                    padding: '2px 7px', borderRadius: 4, fontSize: 12, fontWeight: 500
                  }}>
                    {a.period_count}
                  </span>
                </div>

                <div style={{ textAlign: 'right', fontSize: 13, fontWeight: 700, color: a.is_spike ? '#991b1b' : '#111' }}>
                  {a.today_count}
                </div>
                <div style={{ textAlign: 'right', fontSize: 12, color: '#6b7280' }}>{a.mean_last_7_days}</div>
                <div style={{ textAlign: 'right', fontSize: 12, color: '#6b7280' }}>{a.std_dev}</div>
                <div style={{ textAlign: 'right', fontSize: 12, color: '#6b7280' }}>{a.threshold}</div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{
                    fontSize: 11, padding: '3px 9px', borderRadius: 5, fontWeight: 600,
                    background: a.is_spike ? '#dc2626' : '#dcfce7',
                    color: a.is_spike ? '#fff' : '#166534',
                  }}>
                    {a.is_spike ? 'Spike' : 'Normal'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
