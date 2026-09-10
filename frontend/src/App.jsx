import { useState, useEffect } from 'react';
import { api, logout, getToken } from './api';
import Login from './Login';
import Groups from './Groups';
import GroupDetail from './GroupDetail';

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('access_token'));
  const [loading, setLoading] = useState(true);
  const [groupId, setGroupId] = useState(null);
  const user = getToken() ? decodeJwtUsername(getToken()) : null;

  function decodeJwtUsername(token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.username || payload.sub || '';
    } catch {
      return '';
    }
  }

  useEffect(() => {
    let cancelled = false;
    const tryStart = async () => {
      if (cancelled) return;
      // Small guard so the Django runserver has time to bind its port;
      // this prevents the startup race where the frontend fires
      // /groups/<id>/ requests before Django is listening.
      await new Promise((r) => setTimeout(r, 250));
      setLoading(false);
    };
    tryStart();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="app">
        <div className="center">
          <div className="loader">Loading services…</div>
        </div>
      </div>
    );
  }

  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand" onClick={() => setGroupId(null)}>💸 Expense Splitter</span>
        {user && <span className="user-chip">{user}</span>}
        <button className="ghost" onClick={() => { logout(); setAuthed(false); }}>
          Log out
        </button>
      </header>
      {groupId
        ? <GroupDetail groupId={groupId} onBack={() => setGroupId(null)} />
        : <Groups onOpen={setGroupId} />}
    </div>
  );
}
