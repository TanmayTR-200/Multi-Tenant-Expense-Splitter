import { useState } from 'react';
import { api, logout } from './api';
import Login from './Login';
import Groups from './Groups';
import GroupDetail from './GroupDetail';

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('access_token'));
  const [groupId, setGroupId] = useState(null);

  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand" onClick={() => setGroupId(null)}>💸 Expense Splitter</span>
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
