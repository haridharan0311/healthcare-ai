import { useState, useEffect } from 'react';
import { fetchTimeSeries, fetchTrendComparison } from '../api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const COLORS = ['#2563eb','#16a34a','#dc2626','#7c3aed','#d97706','#db2777','#0891b2','#ea580c'];
const RANGE_OPTIONS = [
  { label: '3D', days: 3 }, { label: '1W', days: 7 },
  { label: '2W', days: 14 }, { label: '1M', days: 30 },
  { label: '3M', days: 90 }, { label: '6M', days: 180 }, { label: '1Y', days: 365 },
];

function periodLabel(days) {
  if (days <= 3)  return 'last 3 days';
  if (days <= 7)  return 'this week';
  if (days <= 14) return 'last 2 weeks';
  if (days <= 30) return 'this month';
  if (days <= 90) return 'last 3 months';
  if (days <= 180) return 'last 6 months';
  return 'this year';
}

function prevPeriodLabel(days) {
  if (days <= 3)  return 'previous 3 days';
  if (days <= 7)  return 'last week';
  if (days <= 14) return '2 weeks before';
  if (days <= 30) return 'last month';
  if (days <= 90) return '3 months before';
  if (days <= 180) return '6 months before';
  return 'last year';
}

export default function TrendChart({ globalDays, onExport }) {
  const [localDays,       setLocalDays]       = useState(globalDays || 30);
  const [chartData,       setChartData]       = useState([]);
  const [diseases,        setDiseases]        = useState([]);
  const [comparison,      setComparison]      = useState(null);
  const [showComparison,  setShowComparison]  = useState(false);
  const [loading,         setLoading]         = useState(true);
  const [compLoading,     setCompLoading]     = useState(false);

  useEffect(() => { setLocalDays(globalDays || 30); }, [globalDays]);

  // Fetch time-series when local days changes
  useEffect(() => {
    setLoading(true);
    fetchTimeSeries(localDays).then(res => {
      const raw        = res.data || [];
      const dateSet    = [...new Set(raw.map(r => r.date))].sort();
      const diseaseSet = [...new Set(raw.map(r => r.disease_name))];
      const lookup     = {};
      raw.forEach(r => {
        if (!lookup[r.date]) lookup[r.date] = { date: r.date };
        lookup[r.date][r.disease_name] = r.case_count;
      });
      setChartData(dateSet.map(d => lookup[d] || { date: d }));
      setDiseases(diseaseSet);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [localDays]);

  // Fetch comparison when toggled or days changes
  useEffect(() => {
    if (!showComparison) return;
    setCompLoading(true);
    fetchTrendComparison(localDays).then(res => {
      setComparison(res.data);
      setCompLoading(false);
    }).catch(() => setCompLoading(false));
  }, [showComparison, localDays]);

  const formatXAxis = (d) => {
    if (localDays <= 14) return d?.slice(5) || '';    // MM-DD
    if (localDays <= 90) return d?.slice(5) || '';
    return d?.slice(0, 7) || '';                       // YYYY-MM
  };

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 24, marginBottom: 24, border: '1px solid #e5e7eb' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>Disease trends</h2>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 3 }}>
            {RANGE_OPTIONS.map(opt => (
              <button
                key={opt.label}
                onClick={() => setLocalDays(opt.days)}
                style={{
                  padding: '4px 10px', borderRadius: 5, border: 'none', cursor: 'pointer',
                  fontSize: 11, fontWeight: localDays === opt.days ? 600 : 400,
                  background: localDays === opt.days ? '#2563eb' : '#f3f4f6',
                  color: localDays === opt.days ? '#fff' : '#555',
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowComparison(s => !s)}
            style={{
              padding: '4px 12px', borderRadius: 5, fontSize: 12, cursor: 'pointer',
              border: '1px solid #e5e7eb',
              background: showComparison ? '#eff6ff' : '#fff',
              color: showComparison ? '#2563eb' : '#555',
              fontWeight: showComparison ? 600 : 400,
            }}
          >
            Compare periods
          </button>

          <button
            onClick={() => onExport && onExport(localDays)}
            style={{
              padding: '4px 12px', borderRadius: 5, border: 'none',
              background: '#f3f4f6', cursor: 'pointer', fontSize: 12
            }}
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Comparison panel — human readable */}
      {showComparison && (
        <div style={{
          background: '#f8faff', border: '1px solid #dbeafe',
          borderRadius: 8, padding: '12px 16px', marginBottom: 16
        }}>
          <div style={{ fontSize: 12, color: '#1d4ed8', fontWeight: 600, marginBottom: 8 }}>
            Comparing: &nbsp;
            <span style={{ fontWeight: 700 }}>{periodLabel(localDays)}</span>
            &nbsp; vs &nbsp;
            <span style={{ fontWeight: 700 }}>{prevPeriodLabel(localDays)}</span>
          </div>

          {compLoading ? (
            <div style={{ fontSize: 12, color: '#9ca3af' }}>Loading comparison...</div>
          ) : comparison?.results?.length > 0 ? (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {comparison.results.map(r => (
                <div
                  key={r.disease_name}
                  title={`${periodLabel(localDays)}: ${r.period2_count} cases | ${prevPeriodLabel(localDays)}: ${r.period1_count} cases`}
                  style={{
                    padding: '5px 12px', borderRadius: 20, fontSize: 12, fontWeight: 500,
                    background: r.direction === 'up' ? '#fef2f2' : r.direction === 'down' ? '#f0fdf4' : '#f9fafb',
                    color:      r.direction === 'up' ? '#dc2626' : r.direction === 'down' ? '#16a34a' : '#6b7280',
                    border:     `1px solid ${r.direction === 'up' ? '#fecaca' : r.direction === 'down' ? '#bbf7d0' : '#e5e7eb'}`,
                    cursor: 'default',
                  }}
                >
                  <span style={{ fontWeight: 700 }}>{r.disease_name}</span>
                  &nbsp;
                  {r.direction === 'up' ? '↑' : r.direction === 'down' ? '↓' : '→'}
                  &nbsp;
                  {/* Show absolute change, not raw % */}
                  <span>
                    {r.period2_count} vs {r.period1_count} cases
                  </span>
                  &nbsp;
                  <span style={{ fontSize: 11, opacity: 0.8 }}>
                    ({r.pct_change > 0 ? '+' : ''}{r.pct_change}%)
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 12, color: '#9ca3af' }}>No comparison data available</div>
          )}

          {/* Period date labels */}
          {comparison && (
            <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8 }}>
              Current: {comparison.period2} &nbsp;|&nbsp; Previous: {comparison.period1}
            </div>
          )}
        </div>
      )}

      {/* Chart */}
      {loading ? (
        <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
          Loading...
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={formatXAxis} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
              labelFormatter={l => `Date: ${l}`}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {diseases.map((d, i) => (
              <Line
                key={d} type="monotone" dataKey={d}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2} dot={false} connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}