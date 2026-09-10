import { useState } from 'react';
import { api } from './api';

export default function Login({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      if (mode === 'register') await api.register(form.username, form.email, form.password);
      await api.login(form.username, form.password);
      onLogin();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <h1>💸 Expense Splitter</h1>
        <p className="muted">{mode === 'login' ? 'Welcome back' : 'Create an account'}</p>
        <input placeholder="Username" required value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })} />
        {mode === 'register' && (
          <input type="email" placeholder="Email" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
        )}
        <input type="password" placeholder="Password (min 8 chars)" required minLength={8}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <div className="error">{error}</div>}
        <button disabled={busy}>{busy ? '…' : mode === 'login' ? 'Log in' : 'Sign up'}</button>
        <a className="muted link" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'Need an account? Sign up' : 'Have an account? Log in'}
        </a>
      </form>
    </div>
  );
}
