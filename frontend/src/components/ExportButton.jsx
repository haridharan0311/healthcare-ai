import { getExportUrl } from '../api';

export default function ExportButton() {
  const handleExport = () => {
    window.open(getExportUrl(), '_blank');
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 24 }}>
      <button onClick={handleExport} style={{
        padding: '10px 24px', borderRadius: 8, border: 'none',
        background: '#1D9E75', color: '#fff', fontSize: 14,
        fontWeight: 500, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8
      }}>
        Download CSV report
      </button>
    </div>
  );
}