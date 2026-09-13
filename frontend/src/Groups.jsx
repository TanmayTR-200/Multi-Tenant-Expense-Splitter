import React from 'react';
import { useEffect, useState } from 'react';
import { api, fmt, currentUsername } from './api';
import Avatar from './Avatar';

export default function Groups({ onOpen }) {
  const [groups, setGroups] = useState([]);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const user = currentUsername();

  const load = () => api.groups().then(setGroups).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.createGroup(name);
      setName('');
      load();
    } catch (err) { setError(err.message); }
  };

  const del = async (e, g) => {
    e.stopPropagation();
    if (deletingId !== null) return;
    if (!window.confirm(
      `Delete "${g.name}"? This removes the group and all its expenses, and can't be undone.`
    )) return;
    setDeletingId(g.id);
    setError('');
    try {
      await api.deleteGroup(g.id);
      load();
    } catch (err) { setError(err.message); }
    finally { setDeletingId(null); }
  };

  return (
    <main className="content">
      <div className="welcome">
        {user && <span className="you">Signed in as <strong>{user}</strong></span>}
      </div>
      <h2>Your groups</h2>
      <form className="row" onSubmit={create}>
        <input placeholder="New group name, e.g. Ski Trip 2026" required value={name}
          onChange={(e) => setName(e.target.value)} />
        <button>Create</button>
      </form>
      {error && <div className="error">{error}</div>}
      <ul className="list">
        {groups.map((g) => (
          <li key={g.id} className="group-card" onClick={() => onOpen(g.id)}>
            <div className="stack">
              {g.members.slice(0, 4).map((m) => (
                <Avatar key={m.id} username={m.username} size="sm" />
              ))}
            </div>
            <div className="group-info">
              <div className="group-title">{g.name}</div>
              <div className="muted small">
                {g.members.length} member{g.members.length !== 1 ? 's' : ''}
              </div>
            </div>
            {g.your_balance_cents === 0 ? (
              <span className="pill flat">settled up</span>
            ) : (
              <span className={`pill ${g.your_balance_cents > 0 ? 'pos' : 'neg'}`}>
                {g.your_balance_cents > 0 ? 'you get ' : 'you owe '}
                {fmt(Math.abs(g.your_balance_cents))}
              </span>
            )}
            <span className="chevron">›</span>
            {g.is_creator && (
              <button
                className="delete"
                aria-label={`Delete ${g.name}`}
                title="Delete group"
                disabled={deletingId === g.id}
                onClick={(e) => del(e, g)}
              >
                {deletingId === g.id ? '…' : '🗑'}
              </button>
            )}
          </li>
        ))}
        {groups.length === 0 && (
          <li className="empty">
            No groups yet. Create one above to start splitting expenses.
          </li>
        )}
      </ul>
    </main>
  );
}
