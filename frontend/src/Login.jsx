import React from 'react';
import { useState } from 'react';
import { api, setTokens } from './api';

export default function Login({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(''); setInfo(''); setBusy(true);
    try {
      if (mode === 'register') {
        setInfo('Creating account…');
        // The register endpoint already returns JWTs — use them directly
        // instead of making a second round-trip to /auth/login/.
        const r = await api.register(form.username, form.email, form.password);
        setTokens(r.access);
      } else {
        await api.login(form.username, form.password);
      }
      onLogin();
    } catch (err) {
      setError(err.message || 'Something went wrong — please try again.');
    } finally {
      setBusy(false);
      setInfo('');
    }
  };

  const toggle = () => {
    setMode(mode === 'login' ? 'register' : 'login');
    setError(''); setInfo('');
  };

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <h1>💸 Expense Splitter</h1>
        <p className="muted">{mode === 'login' ? 'Welcome back' : 'Create an account'}</p>

        <label className="field">
          <span>Username</span>
          <input placeholder="username" autoComplete="username" required autoFocus
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </label>

        {mode === 'register' && (
          <label className="field">
            <span>Email</span>
            <input type="email" placeholder="you@example.com" autoComplete="email" required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </label>
        )}

        <label className="field">
          <span>Password{mode === 'register' ? ' (at least 8 characters)' : ''}</span>
          <input type="password" placeholder="••••••••"
            autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
            required minLength={8} value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </label>

        {error && <div className="error" role="alert">{error}</div>}
        {info && <div className="info" role="status">{info}</div>}

        <button type="submit" disabled={busy}>
          {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
        </button>

        <button type="button" className="link-btn" onClick={toggle}>
          {mode === 'login' ? "Don't have an account? Create one" : 'Already have an account? Log in'}
        </button>
      </form>
    </div>
  );
}
