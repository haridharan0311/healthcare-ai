import { getExportUrl } from '../api';

export default function ExportButton() {
  const buttons = [
    {
      label: 'Disease trends CSV',
      url:   'http://localhost:8000/api/export/disease-trends/',
      color: '#1D9E75',
    },
    {
      label: 'Spike alerts CSV',
      url:   'http://localhost:8000/api/export/spike-alerts/',
      color: '#E24B4A',
    },
    {
      label: 'Restock report CSV',
      url:   'http://localhost:8000/api/export/restock/',
      color: '#BA7517',
    },
  ];

  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginBottom: 24 }}>
      {buttons.map(btn => (
        <button
          key={btn.label}
          onClick={() => window.open(btn.url, '_blank')}
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none',
            background: btn.color, color: '#fff', fontSize: 13,
            fontWeight: 500, cursor: 'pointer',
          }}
        >
          {btn.label}
        </button>
      ))}
    </div>
  );
}