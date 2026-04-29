import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Component Crash Detected:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '24px',
          background: '#fff1f2',
          border: '1px solid #fda4af',
          borderRadius: '12px',
          color: '#be123c',
          textAlign: 'center',
          margin: '12px 0'
        }}>
          <h3 style={{ margin: '0 0 8px 0' }}>Visualization Error</h3>
          <p style={{ margin: 0, fontSize: '14px' }}>
            We couldn't render this component. This usually happens due to unexpected data formats.
          </p>
          <button 
            onClick={() => this.setState({ hasError: false })}
            style={{
              marginTop: '12px',
              padding: '6px 16px',
              background: '#be123c',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
