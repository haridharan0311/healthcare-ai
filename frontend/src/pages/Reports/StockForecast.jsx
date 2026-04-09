import React from 'react';
import styles from './Reports.module.css';

export function StockDepletionForecast({ forecast, drugName, drugOptions, days, onDrugChange }) {
  return (
    <div>
      <h3 className={styles.panelTitle}>Stock Depletion Forecast</h3>
      <p className={styles.panelSubtitle}>
        Forecast stock depletion for a selected medicine using the last {days} days of history.
      </p>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>Select medicine</div>
          <select
            value={drugName}
            onChange={e => onDrugChange(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', minWidth: 260 }}
          >
            <option value="">Choose a medicine</option>
            {drugOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div style={{ fontSize: 12, color: '#6b7280' }}>Forecast horizon: {days} days</div>
      </div>

      {!drugName ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>Select a medicine to view its stock forecast.</div>
      ) : !forecast ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>Loading forecast...</div>
      ) : forecast.error ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#dc2626' }}>{forecast.error}</div>
      ) : (
        <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 18, background: '#f8fafc' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>{forecast.drug_name}</div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>{forecast.generic_name}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#2563eb' }}>{forecast.urgency?.toUpperCase() || 'UNKNOWN'}</div>
              <div style={{ fontSize: 11, color: '#6b7280' }}>Urgency level</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginTop: 16 }}>
            {[
              { label: 'Current stock', value: `${forecast.current_stock?.toLocaleString()} units` },
              { label: 'Avg. daily usage', value: `${forecast.avg_daily_usage?.toFixed(2)} units` },
              { label: 'Days until depletion', value: `${forecast.days_until_depletion} days` },
            ].map((item, i) => (
              <div key={i} style={{ background: '#fff', borderRadius: 10, padding: 14, border: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{item.label}</div>
                <div style={{ fontWeight: 700, fontSize: 18 }}>{item.value}</div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 16, fontSize: 12, color: '#374151' }}>
            Recommended reorder: <strong>{forecast.recommended_reorder?.toLocaleString()} units</strong>
          </div>
          <div style={{ marginTop: 8, fontSize: 11, color: '#6b7280' }}>
            Forecast period: {forecast.analysis_period}
          </div>
        </div>
      )}
    </div>
  );
}

export function AdaptiveBuffers({ data }) {
  if (!data) return null;

  return (
    <div>
      <h3 className={styles.panelTitle}>Adaptive Stock Buffers</h3>
      <p className={styles.panelSubtitle}>
        Recommended buffer multiplier based on recent demand and spike activity
      </p>

      {data.error ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#dc2626' }}>{data.error}</div>
      ) : (
        <div style={{ display: 'grid', gap: 14 }}>
          <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 18, background: '#f8fafc' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <div>
                <div style={{ fontSize: 12, color: '#6b7280' }}>Adaptive buffer</div>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#1d4ed8' }}>{data.adaptive_buffer}x</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 12, color: '#6b7280' }}>Interpretation</div>
                <div style={{ fontWeight: 700, fontSize: 16, textTransform: 'capitalize' }}>{data.interpretation || 'N/A'}</div>
              </div>
            </div>
            <div style={{ marginTop: 14, fontSize: 12, color: '#374151' }}>
              Recommended ordering buffer is calculated from spike activity and disease risk.
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
            {[
              { label: 'Spike count', value: data.spike_count },
              { label: 'Active diseases', value: data.total_diseases },
              { label: 'Spike %', value: `${data.spike_percentage}%` },
              { label: 'Base buffer', value: `${data.base_buffer}x` },
              { label: 'Max buffer', value: `${data.max_buffer}x` },
              { label: 'Buffer increase', value: `${data.buffer_increase}x` },
            ].map((item, idx) => (
              <div key={idx} style={{ background: '#fff', borderRadius: 10, padding: 14, border: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{item.label}</div>
                <div style={{ fontWeight: 700, marginTop: 6 }}>{item.value ?? 'N/A'}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
