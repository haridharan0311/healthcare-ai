import { useState, useEffect } from 'react';
import { fetchTimeSeries, fetchTrendComparison } from '../api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = ['#2563eb','#16a34a','#dc2626','#7c3aed','#d97706','#db2777','#0891b2','#ea580c'];

const RANGE_OPTIONS = [
  { label: '3D', days: 3 }, { label: '1W', days: 7 },
  { label: '2W', days: 14 }, { label: '1M', days: 30 },
  { label: '3M', days: 90 }, { label: '6M', days: 180 }, { label: '1Y', days: 365 },
];

export default function TrendChart({ days: globalDays, comparison, onExport }) {
  const [localDays, setLocalDays] = useState(globalDays);
  const [chartData, setChartData] = useState([]);
  const [diseases, setDiseases]   = useState([]);
  const [showComparison, setShowComparison] = useState(false);
  const [loading, setLoading]     = useState(true);

  useEffect(() => { setLocalDays(globalDays); }, [globalDays]);

  useEffect(() => {
    setLoading(true);
    fetchTimeSeries(localDays).then(res => {
      const raw      = res.data;
      const dateSet  = [...new Set(raw.map(r => r.date))].sort();
      const diseaseSet = [...new Set(raw.map(r => r.disease_name))];
      const lookup   = {};
      raw.forEach(r => {
        if (!lookup[r.date]) lookup[r.date] = { date: r.date };
        lookup[r.date][r.disease_name] = r.case_count;
      });
      setChartData(dateSet.map(d => lookup[d] || { date: d }));
      setDiseases(diseaseSet);
      setLoading(false);
    });
  }, [localDays]);

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 24, marginBottom: 24, border: '1px solid #eee' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>Disease trends</h2>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 3 }}>
            {RANGE_OPTIONS.map(opt => (
              <button key={opt.label} onClick={() => setLocalDays(opt.days)} style={{
                padding: '4px 10px', borderRadius: 5, border: 'none', cursor: 'pointer',
                fontSize: 11, fontWeight: localDays === opt.days ? 600 : 400,
                background: localDays === opt.days ? '#2563eb' : '#f3f4f6',
                color: localDays === opt.days ? '#fff' : '#555',
              }}>{opt.label}</button>
            ))}
          </div>
          <button onClick={() => setShowComparison(s => !s)} style={{
            padding: '4px 12px', borderRadius: 5, fontSize: 12, cursor: 'pointer',
            border: '1px solid #e5e7eb',
            background: showComparison ? '#eff6ff' : '#fff',
            color: showComparison ? '#2563eb' : '#555',
          }}>
            {showComparison ? 'Hide' : 'vs prev period'}
          </button>
          <button onClick={onExport} style={{
            padding: '4px 12px', borderRadius: 5, border: 'none',
            background: '#f3f4f6', cursor: 'pointer', fontSize: 12
          }}>Export CSV</button>
        </div>
      </div>

      {/* Period comparison badges */}
      {showComparison && comparison?.results?.length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
          {comparison.results.slice(0, 8).map(r => (
            <div key={r.disease_name} style={{
              padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 500,
              background: r.direction === 'up' ? '#fef2f2' : r.direction === 'down' ? '#f0fdf4' : '#f9fafb',
              color: r.direction === 'up' ? '#dc2626' : r.direction === 'down' ? '#16a34a' : '#6b7280',
              border: `1px solid ${r.direction === 'up' ? '#fecaca' : r.direction === 'down' ? '#bbf7d0' : '#e5e7eb'}`,
            }}>
              {r.disease_name} &nbsp;
              {r.direction === 'up' ? '↑' : r.direction === 'down' ? '↓' : '→'}
              {r.pct_change > 0 ? '+' : ''}{r.pct_change}%
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>Loading...</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }}
              tickFormatter={d => localDays <= 14 ? d.slice(5) : localDays <= 90 ? d.slice(5) : d.slice(0,7)} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {diseases.map((d, i) => (
              <Line key={d} type="monotone" dataKey={d}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2} dot={false} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
