import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError('Invalid credentials. Please check your username and password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      height: '100vh', width: '100vw', 
      background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      <div style={{
        width: '100%', maxWidth: 400, padding: 40,
        background: '#fff', borderRadius: 24,
        boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
        border: '1px solid #fff'
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ 
            width: 48, height: 48, background: '#2563eb', borderRadius: 12,
            margin: '0 auto 16px', display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: 24, fontWeight: 800
          }}>H</div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: '#0f172a', margin: '0 0 8px 0' }}>Welcome Back</h1>
          <p style={{ color: '#64748b', fontSize: 14, margin: 0 }}>Please sign in to access Healthcare AI</p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && (
            <div style={{ 
              padding: '12px 16px', background: '#fef2f2', border: '1px solid #fee2e2',
              borderRadius: 12, color: '#dc2626', fontSize: 14, fontWeight: 500, marginBottom: 20
            }}>
              {error}
            </div>
          )}

          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#475569', marginBottom: 8 }}>Username</label>
            <input 
              type="text" 
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. super_admin"
              style={{
                width: '100%', padding: '12px 16px', borderRadius: 12, border: '1px solid #e2e8f0',
                fontSize: 14, outline: 'none', transition: 'border-color 0.2s',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#475569', marginBottom: 8 }}>Password</label>
            <input 
              type="password" 
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={{
                width: '100%', padding: '12px 16px', borderRadius: 12, border: '1px solid #e2e8f0',
                fontSize: 14, outline: 'none', transition: 'border-color 0.2s',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <button 
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '14px', borderRadius: 12, background: '#2563eb',
              color: '#fff', border: 'none', fontSize: 15, fontWeight: 700, cursor: 'pointer',
              transition: 'all 0.2s', boxShadow: '0 4px 6px -1px rgb(37 99 235 / 0.2)'
            }}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        
        <div style={{ marginTop: 24, textAlign: 'center', fontSize: 12, color: '#94a3b8' }}>
          Secure Multi-Tenant Environment &copy; 2026
        </div>
      </div>
    </div>
  );
}
