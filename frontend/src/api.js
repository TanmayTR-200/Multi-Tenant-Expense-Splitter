const DJANGO = 'http://127.0.0.1:8000/api';
const SETTLE = 'http://127.0.0.1:8001';

export function getToken() {
  return localStorage.getItem('access_token');
}

export function setTokens(access) {
  localStorage.setItem('access_token', access);
}

export function setUsername(username) {
  if (username) localStorage.setItem('username', username);
}

export function currentUsername() {
  const stored = localStorage.getItem('username');
  if (stored) return stored;
  const token = getToken();
  if (!token) return '';
  try {
    const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4)));
    return payload.username || '';
  } catch {
    return '';
  }
}

export function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('username');
}

async function req(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(`${DJANGO}${path}`, {
      method, headers, body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error(
      'Cannot reach the backend. Make sure all services are running (python dev.py), then refresh the page.'
    );
  }
  if (res.status === 401) { logout(); throw new Error('Session expired. Please log in again.'); }
  if (!res.ok) {
    let detail = res.statusText;
    try { const j = await res.json(); detail = j.detail || JSON.stringify(j); } catch {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  register: (username, email, password) =>
    req('/auth/register/', { method: 'POST', body: { username, email, password } }),
  login: async (username, password) => {
    const res = await fetch(`${DJANGO}/auth/login/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      throw new Error(j.detail || 'Invalid credentials');
    }
    const j = await res.json();
    setTokens(j.access);
    return j;
  },
  groups: () => req('/groups/'),
  createGroup: (name) => req('/groups/', { method: 'POST', body: { name } }),
  group: (id) => req(`/groups/${id}/`),
  searchUsers: (q) => req(`/users/?q=${encodeURIComponent(q.trim())}`),
  addMember: (groupId, username) =>
    req(`/groups/${groupId}/members/`, {
      method: 'POST',
      body: { username },
    }),
  addExpense: (groupId, description, amountCents, splits, paidBy) => {
    const body = { description, amount_cents: amountCents };
    if (splits) body.splits = splits;
    if (paidBy) body.paid_by = paidBy;
    return req(`/groups/${groupId}/`, { method: 'POST', body });
  },
  settle: async (groupId) => {
    const res = await fetch(`${SETTLE}/settle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({ group_id: groupId }),
    });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      throw new Error(j.detail || `Settlement failed (${res.status})`);
    }
    return res.json();
  },
};

export const fmt = (cents) =>
  (cents / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
