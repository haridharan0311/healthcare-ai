import { useState, useEffect } from 'react';
import { fetchRestock } from '../api';

const STATUS_STYLE = {
  critical:   { background: '#FCEBEB', color: '#A32D2D', border: '1px solid #F09595' },
  low:        { background: '#FAEEDA', color: '#633806', border: '1px solid #FAC775' },
  sufficient: { background: '#EAF3DE', color: '#27500A', border: '1px solid #C0DD97' },
};

export default function RestockTable() {
  const [items, setItems]   = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRestock().then(res => {
      setItems(res.data);
      setLoading(false);
    });
  }, []);

  return (
    <div style={{ background: 'var(--card-bg)', borderRadius: 12, padding: 24, marginBottom: 24 }}>
      <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 500 }}>Medicine restock</h2>

      {loading ? (
        <p style={{ color: '#888' }}>Loading...</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #eee' }}>
                {['Drug', 'Generic', 'Current stock', 'Predicted demand', 'Suggested restock', 'Status', 'Diseases'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 500, color: '#555', whiteSpace: 'nowrap' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>{item.drug_name}</td>
                  <td style={{ padding: '10px 12px', color: '#666' }}>{item.generic_name}</td>
                  <td style={{ padding: '10px 12px' }}>{item.current_stock.toLocaleString()}</td>
                  <td style={{ padding: '10px 12px' }}>{Number(item.predicted_demand).toFixed(1)}</td>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>
                    {item.suggested_restock.toLocaleString()}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {item.status ? (
                      <span style={{
                        ...(STATUS_STYLE[item.status] || STATUS_STYLE['sufficient']),
                        borderRadius: 6, padding: '3px 12px', fontSize: 12, fontWeight: 500,
                        display: 'inline-block'
                      }}>
                        {item.status}
                      </span>
                    ) : (
                      <span style={{
                        ...STATUS_STYLE['sufficient'],
                        borderRadius: 6, padding: '3px 12px', fontSize: 12, fontWeight: 500,
                        display: 'inline-block'
                      }}>
                        sufficient
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '10px 12px', color: '#666', fontSize: 12 }}>
                    {item.contributing_diseases.join(', ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

