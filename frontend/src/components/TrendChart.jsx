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

const DATE_OPTIONS = [
  { label: '3D',  days: 3   },
  { label: '4D',  days: 4   },
  { label: '5D',  days: 5   },
  { label: '1W',  days: 7   },
  { label: '2W',  days: 14  },
  { label: '3W',  days: 21  },
  { label: '1M',  days: 30  },
  { label: '2M',  days: 60  },
  { label: '3M',  days: 90  },
  { label: '6M',  days: 180 },
  { label: '1Y',  days: 365 },
];

export default function TrendChart() {
  const [selected, setSelected] = useState('1W');
  const [chartData, setData]    = useState([]);
  const [diseases, setDiseases] = useState([]);
  const [loading, setLoading]   = useState(true);

  const days = DATE_OPTIONS.find(o => o.label === selected)?.days ?? 7;

  useEffect(() => {
    setLoading(true);
    fetchTimeSeries(days).then(res => {
      const raw = res.data;
      const dateSet    = [...new Set(raw.map(r => r.date))].sort();
      const diseaseSet = [...new Set(raw.map(r => r.disease_name))];

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
    <div style={{
      background: '#fff', borderRadius: 12, padding: 24,
      marginBottom: 24, border: '1px solid #eee'
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 500 }}>Disease trends</h2>

        {/* Date range pills */}
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {DATE_OPTIONS.map(opt => (
            <button
              key={opt.label}
              onClick={() => setSelected(opt.label)}
              style={{
                padding: '5px 11px',
                borderRadius: 6,
                border: 'none',
                cursor: 'pointer',
                fontSize: 12,
                fontWeight: selected === opt.label ? 500 : 400,
                background: selected === opt.label ? '#378ADD' : '#f0f0f0',
                color: selected === opt.label ? '#fff' : '#555',
                transition: 'all 0.15s',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div style={{ height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa' }}>
          Loading...
        </div>
      ) : chartData.length === 0 ? (
        <div style={{ height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa' }}>
          No data for this period
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              tickFormatter={d => {
                // Shorten label based on range
                if (days <= 7)  return d.slice(5);       // 03-18
                if (days <= 90) return d.slice(5);       // 03-18
                return d.slice(0, 7);                    // 2026-03
              }}
            />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              labelFormatter={l => `Date: ${l}`}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
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
