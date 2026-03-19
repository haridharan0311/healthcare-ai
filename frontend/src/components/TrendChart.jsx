import { useState, useEffect } from 'react';
import { fetchTimeSeries } from '../api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const COLORS = [
  '#378ADD', '#1D9E75', '#D85A30', '#7F77DD',
  '#BA7517', '#D4537E', '#639922', '#E24B4A'
];

export default function TrendChart() {
  const [days, setDays]       = useState(7);
  const [chartData, setData]  = useState([]);
  const [diseases, setDiseases] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchTimeSeries(days).then(res => {
      const raw = res.data;

      // Collect all unique disease names and dates
      const dateSet    = [...new Set(raw.map(r => r.date))].sort();
      const diseaseSet = [...new Set(raw.map(r => r.disease_name))];

      // Build recharts format: [{date, Dengue: 3, Flu: 5, ...}]
      const lookup = {};
      raw.forEach(r => {
        if (!lookup[r.date]) lookup[r.date] = { date: r.date };
        lookup[r.date][r.disease_name] = r.case_count;
      });

      setData(dateSet.map(d => lookup[d] || { date: d }));
      setDiseases(diseaseSet);
      setLoading(false);
    });
  }, [days]);

  return (
    <div style={{ background: 'var(--card-bg)', borderRadius: 12, padding: 24, marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 500 }}>Disease trends</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          {[7, 30].map(d => (
            <button key={d} onClick={() => setDays(d)} style={{
              padding: '6px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: days === d ? '#378ADD' : '#e8e8e8',
              color: days === d ? '#fff' : '#444',
              fontWeight: days === d ? 500 : 400,
            }}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p style={{ color: '#888', textAlign: 'center', padding: 40 }}>Loading...</p>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {diseases.map((d, i) => (
              <Line
                key={d}
                type="monotone"
                dataKey={d}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
