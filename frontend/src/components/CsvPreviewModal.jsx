export default function CsvPreviewModal({ data, onClose }) {
  if (!data) return null;
  const { rows, url, type } = data;
  const headers = rows[0] || [];
  const body    = rows.slice(1, 51); // show max 50 rows in preview

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 24
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, width: '100%', maxWidth: 1000,
        maxHeight: '85vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0,0,0,0.2)'
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 24px', borderBottom: '1px solid #e5e7eb',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>
              Preview: {type.replace(/-/g, ' ')}
            </h3>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: '#9ca3af' }}>
              Showing first {Math.min(body.length, 50)} rows of {rows.length - 1} total
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <a href={url} download style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: '#2563eb', color: '#fff', fontSize: 13,
              fontWeight: 500, cursor: 'pointer', textDecoration: 'none',
              display: 'inline-block'
            }}>
              Download CSV
            </a>
            <button onClick={onClose} style={{
              padding: '8px 16px', borderRadius: 8, border: '1px solid #e5e7eb',
              background: '#fff', cursor: 'pointer', fontSize: 13
            }}>
              Close
            </button>
          </div>
        </div>

        {/* Table */}
        <div style={{ overflow: 'auto', flex: 1 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead style={{ position: 'sticky', top: 0, background: '#f9fafb' }}>
              <tr>
                {headers.map((h, i) => (
                  <th key={i} style={{
                    padding: '10px 12px', textAlign: 'left',
                    fontWeight: 600, color: '#374151',
                    borderBottom: '2px solid #e5e7eb', whiteSpace: 'nowrap'
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row, ri) => (
                <tr key={ri} style={{ background: ri % 2 === 0 ? '#fff' : '#f9fafb' }}>
                  {row.map((cell, ci) => (
                    <td key={ci} style={{
                      padding: '8px 12px', borderBottom: '1px solid #f3f4f6',
                      color: '#374151', whiteSpace: 'nowrap'
                    }}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
