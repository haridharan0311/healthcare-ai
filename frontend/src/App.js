import TrendChart    from './components/TrendChart';
import SpikeAlerts   from './components/SpikeAlerts';
import RestockTable  from './components/RestockTable';
import ExportButton  from './components/ExportButton';

export default function App() {
  return (
    <div style={{
      minHeight: '100vh',
      background: '#f7f7f5',
      padding: '32px 24px',
      fontFamily: 'system-ui, sans-serif',
      '--card-bg': '#ffffff',
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>

        <div style={{ marginBottom: 32 }}>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 500 }}>
            Healthcare analytics
          </h1>
          <p style={{ margin: '4px 0 0', color: '#888', fontSize: 14 }}>
            Disease trends · Spike detection · Medicine restock
          </p>
        </div>

        <ExportButton />
        <SpikeAlerts />
        <TrendChart />
        <RestockTable />

      </div>
    </div>
  );
}
