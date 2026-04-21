import { useState, useEffect, useRef } from 'react';
import { useTimeSeriesTrends } from '../hooks/useDashboardData';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const COLORS = [
  '#4f46e5', '#0d9488', '#64748b', '#7c3aed', 
  '#e11d48', '#2563eb', '#db2777', '#b45309',
  '#0f172a', '#10b981', '#ef4444', '#f59e0b'
];

export default function TrendChart({ onExport }) {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useTimeSeriesTrends(days);
  
  const [selectedDiseases, setSelectedDiseases] = useState([]);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLayoutReady, setIsLayoutReady] = useState(false);
  const containerRef = useRef(null);

  const { chartData = [], allDiseases = [] } = data || {};

  // Initialize selected diseases when data loads
  useEffect(() => {
    if (!isInitialized && allDiseases.length > 0) {
      setSelectedDiseases(allDiseases.slice(0, 4));
      setIsInitialized(true);
    }
  }, [allDiseases, isInitialized]);

  // Layout stabilization
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) setIsLayoutReady(true);
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const toggleDisease = (name) => {
    setSelectedDiseases(prev => 
      prev.includes(name) ? prev.filter(d => d !== name) : [...prev, name]
    );
  };

  const setPreset = (count) => {
    if (count === 'all') setSelectedDiseases([...allDiseases]);
    else if (count === 0) setSelectedDiseases([]);
    else setSelectedDiseases(allDiseases.slice(0, count));
  };

  const formatXAxis = (d) => {
    if (!d) return '';
    const parts = d.split('-');
    return parts.length < 3 ? d : `${parts[1]}-${parts[2]}`;
  };

  return (
    <div style={{ 
      background: '#fff', borderRadius: 16, padding: 24, marginBottom: 24, 
      border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: '#0f172a' }}>Disease Trends</h2>
          <div style={{ fontSize: 13, color: '#64748b' }}>Comparison analysis and longitudinal monitoring</div>
        </div>
        
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ display: 'flex', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 2 }}>
            {[7, 14, 30, 90].map(d => (
              <button
                key={d} onClick={() => setDays(d)}
                style={{
                  padding: '6px 12px', border: 'none', borderRadius: 6,
                  background: days === d ? '#1e293b' : 'transparent',
                  color: days === d ? '#fff' : '#64748b',
                  fontSize: 11, fontWeight: 700, cursor: 'pointer'
                }}
              >
                {d}D
              </button>
            ))}
          </div>
          <button onClick={() => onExport && onExport(days)} style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', fontWeight: 600 }}>📊 Export</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 32 }}>
        <div style={{ borderRight: '1px solid #f1f5f9', paddingRight: 24 }}>
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 12 }}>Presets</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {[2, 5, 'all', 0].map(p => (
                <button key={p} onClick={() => setPreset(p)} style={{ padding: '8px', borderRadius: 6, border: '1px solid #e2e8f0', fontSize: 11, background: '#f8fafc' }}>
                  {p === 'all' ? 'All' : p === 0 ? 'Clear' : `Top ${p}`}
                </button>
              ))}
            </div>
          </div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 12 }}>Disease List</div>
          <div style={{ maxHeight: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {allDiseases.map((d, i) => (
              <label key={d} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13 }}>
                <input type="checkbox" checked={selectedDiseases.includes(d)} onChange={() => toggleDisease(d)} />
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length] }} />
                {d}
              </label>
            ))}
          </div>
        </div>

        <div ref={containerRef} style={{ height: 400, width: '100%', minHeight: 400, position: 'relative' }}>
          {isLoading || !isLayoutReady ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', background: '#f8fafc', borderRadius: 12 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 24, height: 24, border: '3px solid #e2e8f0', borderTopColor: '#2563eb', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                  Analyzing patterns...
              </div>
            </div>
          ) : (
            <ResponsiveContainer width="99%" height="99%" minWidth={0} minHeight={0}>
              <LineChart data={chartData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="date" tickFormatter={formatXAxis} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: 20, fontSize: 12, fontWeight: 700 }} />
                {selectedDiseases.map((d, i) => (
                  <Line key={d} type="monotone" dataKey={d} stroke={COLORS[allDiseases.indexOf(d) % COLORS.length]} strokeWidth={2.5} dot={false} activeDot={{ r: 6, strokeWidth: 2, stroke: '#fff' }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}