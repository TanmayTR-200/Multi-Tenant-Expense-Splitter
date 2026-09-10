import { useEffect, useState } from 'react';
import { api, fmt } from './api';

export default function Groups({ onOpen }) {
  const [groups, setGroups] = useState([]);
  const [name, setName] = useState('');
  const [error, setError] = useState('');

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

  return (
    <main className="content">
      <h2>Your groups</h2>
      <form className="row" onSubmit={create}>
        <input placeholder="New group name" required value={name}
          onChange={(e) => setName(e.target.value)} />
        <button>Create</button>
      </form>
      {error && <div className="error">{error}</div>}
      <ul className="list">
        {groups.map((g) => (
          <li key={g.id} className="card row spaced" onClick={() => onOpen(g.id)}>
            <div>
              <strong>{g.name}</strong>
              <div className="muted">{g.members.length} member{g.members.length !== 1 ? 's' : ''}</div>
            </div>
            <span className={g.your_balance_cents >= 0 ? 'pos' : 'neg'}>
              {fmt(g.your_balance_cents)}
            </span>
          </li>
        ))}
        {groups.length === 0 && <li className="muted">No groups yet — create one above.</li>}
      </ul>
    </main>
  );
}
