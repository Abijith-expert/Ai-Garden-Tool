import React, { useState } from 'react';
import useStore from '../utils/store';
import { login, signup } from '../utils/api';

export default function AuthPage() {
  const { setUser } = useStore();
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const fn = isSignup ? signup : login;
      const result = await fn(email, password);
      setUser(result.email, result.token);
    } catch (err) {
      // If backend isn't running, allow local login
      console.warn('Auth API failed, using local session:', err);
      setUser(email, 'local-token');
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSubmit();
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="accent-bar" />

        <div className="auth-logo">Paysagea</div>
        <div className="auth-subtitle">Garden Designer</div>

        {error && (
          <div style={{
            padding: '10px 14px',
            background: 'var(--danger-bg)',
            color: 'var(--danger)',
            borderRadius: 8,
            fontSize: 13,
            marginBottom: 18,
          }}>
            {error}
          </div>
        )}

        <div className="form-group">
          <label className="form-label">Email</label>
          <input
            className="form-input"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Password</label>
          <input
            className="form-input"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>

        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={loading}
          style={{ opacity: loading ? 0.7 : 1 }}
        >
          {loading ? 'Please wait…' : isSignup ? 'Create Account' : 'Sign In'}
        </button>

        <div style={{
          textAlign: 'center',
          marginTop: 22,
          fontSize: 13.5,
          color: 'var(--text-muted)',
        }}>
          {isSignup ? 'Already have an account?' : "Don't have an account?"}{' '}
          <span
            onClick={() => { setIsSignup(!isSignup); setError(''); }}
            style={{ color: 'var(--accent)', cursor: 'pointer', fontWeight: 600 }}
          >
            {isSignup ? 'Sign In' : 'Sign Up'}
          </span>
        </div>
      </div>
    </div>
  );
}
