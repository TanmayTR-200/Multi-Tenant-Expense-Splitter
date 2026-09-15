import React from 'react';
import { useEffect, useState } from 'react';
import { api, fmt, currentUsername } from './api';
import Avatar from './Avatar';

function balanceLabel(cents) {
  if (cents > 0) return <span className="pill pos">gets back {fmt(cents)}</span>;
  if (cents < 0) return <span className="pill neg">owes {fmt(-cents)}</span>;
  return <span className="pill flat">settled up</span>;
}

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
  const [payer, setPayer] = useState('');
  const me = currentUsername();

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
      await api.addExpense(groupId, desc, Math.round(dollars * 100), null, payer);
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
      <div className="row back-row">
        <button className="ghost" onClick={onBack}>← All groups</button>
      </div>
      <h2>{group.name}</h2>
      <div className="detail-meta">
        <span className="muted small">Created by {group.created_by}</span>
        <span className="chip">{group.members.length} member{group.members.length !== 1 ? 's' : ''}</span>
      </div>

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
            <li key={m.id} className="balance-row">
              <Avatar username={m.username} />
              <span className="who">{m.username}
                {m.username === group.created_by && <span className="badge">creator</span>}
              </span>
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
            <li key={b.user_id} className="balance-row">
              <Avatar username={b.username} />
              <span className="who">{b.username}</span>
              {balanceLabel(b.balance_cents)}
            </li>
          ))}
        </ul>
      </section>

      <form className="card row" onSubmit={addExpense}>
        <input placeholder="Description, e.g. Dinner" required value={desc}
          onChange={(e) => setDesc(e.target.value)} />
        <input placeholder="Amount, e.g. 42.50" required inputMode="decimal"
          value={amount} onChange={(e) => setAmount(e.target.value)} />
        <select
          aria-label="Paid by"
          value={payer || me || group.members[0]?.username || ''}
          onChange={(e) => setPayer(e.target.value)}
        >
          {group.members.map((m) => (
            <option key={m.id} value={m.username}>Paid by {m.username}</option>
          ))}
        </select>
        <button disabled={busy}>Add expense</button>
      </form>
      <p className="muted small" style={{ marginTop: -10, marginBottom: 14 }}>
        Expenses split equally among all members.
      </p>
      {noExpenses && (
        <div className="empty">No expenses yet — add one above.</div>
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
            <li key={x.id} className="expense">
              <Avatar username={x.paid_by.username} />
              <div className="expense-main">
                <div className="expense-top">
                  <strong>{x.description}</strong>
                  <span className="amount">{fmt(x.amount_cents)}</span>
                </div>
                <div className="muted small">paid by {x.paid_by.username}</div>
                <div className="chips">
                  {x.splits.map((s) => (
                    <span key={s.user_id} className="chip">
                      {s.username} {fmt(s.amount_cents)}
                    </span>
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {transfers && (
        <section className="card settle-card">
          <h3>Suggested payments</h3>
          <ul className="list">
            {transfers.map((t, i) => (
              <li key={i} className="transfer">
                <Avatar username={t.from.username} size="sm" />
                <span className="who">{t.from.username}</span>
                <span className="arrow">→</span>
                <Avatar username={t.to.username} size="sm" />
                <span className="who">{t.to.username}</span>
                <span className="pill pos">pays {fmt(t.amount_cents)}</span>
              </li>
            ))}
            {transfers.length === 0 && (
              <li className="empty">
                {noExpenses
                  ? 'Add an expense first, then see who owes whom.'
                  : 'All settled up 🎉'}
              </li>
            )}
          </ul>
        </section>
      )}

      {error && <div className="error">{error}</div>}
    </main>
  );
}
