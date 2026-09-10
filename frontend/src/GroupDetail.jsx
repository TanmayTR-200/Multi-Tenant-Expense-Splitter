import { useEffect, useState } from 'react';
import { api, fmt } from './api';

export default function GroupDetail({ groupId, onBack }) {
  const [group, setGroup] = useState(null);
  const [transfers, setTransfers] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [desc, setDesc] = useState('');
  const [amount, setAmount] = useState('');
  const [memberQ, setMemberQ] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showMatches, setShowMatches] = useState(false);

  const load = () =>
    api.group(groupId)
      .then((g) => { setGroup(g); setTransfers(null); })
      .catch((e) => setError(e.message));

  useEffect(() => { load(); }, [groupId]);

  useEffect(() => {
    const q = memberQ.trim();
    if (!q) { setSuggestions([]); setShowMatches(false); return; }
    let alive = true;
    api.searchUsers(q).then((r) => { if (alive) { setSuggestions(r); setShowMatches(true); } })
      .catch((e) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [memberQ]);

  const addExpense = async (e) => {
    e.preventDefault();
    setError('');
    const dollars = parseFloat(amount);
    if (!Number.isFinite(dollars) || dollars <= 0) {
      setError('Amount must be a positive number');
      return;
    }
    setBusy(true);
    try {
      // No splits sent: the API splits equally among all group members,
      // and the payer is always the authenticated user (never client-chosen).
      await api.addExpense(groupId, desc, Math.round(dollars * 100), null);
      setDesc(''); setAmount('');
      await load();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  const addMember = async (username) => {
    setError(''); setBusy(true);
    try {
      await api.addMember(groupId, username);
      setMemberQ(''); setSuggestions([]); setShowMatches(false);
      await load();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  const settle = async () => {
    setError(''); setBusy(true);
    try {
      const res = await api.settle(groupId);
      setTransfers(res.transfers);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  if (!group) return <main className="content">{error || 'Loading…'}</main>;

  const noExpenses = group.expenses.length === 0;
  const alone = group.members.length === 1;

  return (
    <main className="content">
      <button className="ghost" onClick={onBack}>← All groups</button>
      <h2>{group.name}</h2>
      <p className="muted">Created by {group.created_by}</p>

      {alone && (
        <div className="callout">
          👥 Your group only has you in it. Add members below so expenses can be
          split and settled between people.
        </div>
      )}

      <section className="card">
        <h3>Members</h3>
        <ul className="list">
          {group.members.map((m) => (
            <li key={m.id} className="row spaced">
              <span>{m.username}{m.username === group.created_by ? ' (creator)' : ''}</span>
            </li>
          ))}
        </ul>
        {group.is_creator && (
          <div className="row add-member">
            <div className="search-box">
              <input
                placeholder="Add member by username, e.g. bob"
                value={memberQ}
                onChange={(e) => setMemberQ(e.target.value)}
                onBlur={() => setTimeout(() => setShowMatches(false), 200)}
                onFocus={() => memberQ.trim() && setShowMatches(true)}
              />
              {showMatches && (
                <ul className="matches">
                  {suggestions.length === 0 && <li className="muted">No matching users.</li>}
                  {suggestions.map((u) => (
                    <li key={u.id} className="row spaced clickable" onMouseDown={() => addMember(u.username)}>
                      <span>{u.username}</span>
                      <span className="pos">+ Add</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <button
              onClick={() => memberQ.trim() && addMember(memberQ.trim())}
              disabled={busy || !memberQ.trim()}
            >
              Add
            </button>
          </div>
        )}
        {!group.is_creator && (
          <p className="muted">Only the group creator can add members.</p>
        )}
      </section>

      <section className="card">
        <h3>Balances</h3>
        <ul className="list">
          {group.balances.map((b) => (
            <li key={b.user_id} className="row spaced">
              <span>{b.username}</span>
              <span className={b.balance_cents >= 0 ? 'pos' : 'neg'}>
                {fmt(b.balance_cents)}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <form className="card row" onSubmit={addExpense}>
        <input placeholder="Description" required value={desc}
          onChange={(e) => setDesc(e.target.value)} />
        <input placeholder="Amount (e.g. 42.50)" required inputMode="decimal"
          value={amount} onChange={(e) => setAmount(e.target.value)} />
        <button disabled={busy}>Add expense (split equally)</button>
      </form>
      {noExpenses && (
        <p className="muted">No expenses yet — add one above.</p>
      )}

      <section className="card">
        <div className="row spaced">
          <h3>Expenses</h3>
          <button onClick={settle} disabled={busy}>
            {busy ? '…' : 'See who owes whom'}
          </button>
        </div>
        <ul className="list">
          {group.expenses.map((x) => (
            <li key={x.id}>
              <div className="row spaced">
                <span><strong>{x.description}</strong> <span className="muted">— paid by {x.paid_by.username}</span></span>
                <span>{fmt(x.amount_cents)}</span>
              </div>
              <div className="muted small">
                split: {x.splits.map((s) => `${s.username} ${fmt(s.amount_cents)}`).join(' · ')}
              </div>
            </li>
          ))}
        </ul>
      </section>

      {transfers && (
        <section className="card">
          <h3>Suggested payments</h3>
          <ul className="list">
            {transfers.map((t, i) => (
              <li key={i} className="row spaced">
                <span><strong>{t.from.username}</strong> pays <strong>{t.to.username}</strong></span>
                <span className="pos">{fmt(t.amount_cents)}</span>
              </li>
            ))}
            {transfers.length === 0 && <li className="muted">
              {noExpenses ? 'Add an expense first, then see who owes whom.' : 'All settled up 🎉'}
            </li>}
          </ul>
        </section>
      )}

      {error && <div className="error">{error}</div>}
    </main>
  );
}
