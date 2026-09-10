import { useEffect, useState } from 'react';
import { api, fmt } from './api';

export default function GroupDetail({ groupId, onBack }) {
  const [group, setGroup] = useState(null);
  const [transfers, setTransfers] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [desc, setDesc] = useState('');
  const [amount, setAmount] = useState('');

  const load = () => api.group(groupId).then(setGroup).catch((e) => setError(e.message));

  useEffect(() => { load(); }, [groupId]);

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
      setDesc(''); setAmount(''); setTransfers(null);
      load();
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

  return (
    <main className="content">
      <button className="ghost" onClick={onBack}>← All groups</button>
      <h2>{group.name}</h2>

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

      <section className="card">
        <div className="row spaced">
          <h3>Expenses</h3>
          <button onClick={settle} disabled={busy}>
            {busy ? '…' : 'Settle up'}
          </button>
        </div>
        <ul className="list">
          {group.expenses.map((x) => (
            <li key={x.id} className="row spaced">
              <span><strong>{x.description}</strong> <span className="muted">paid by {x.paid_by.username}</span></span>
              <span>{fmt(x.amount_cents)}</span>
            </li>
          ))}
          {group.expenses.length === 0 && <li className="muted">No expenses yet.</li>}
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
            {transfers.length === 0 && <li className="muted">All settled up 🎉</li>}
          </ul>
        </section>
      )}

      {error && <div className="error">{error}</div>}
    </main>
  );
}
