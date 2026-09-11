# WeAudit — Multi-Tenant Expense Splitter

A simplified Splitwise with strict tenant isolation, built as three services:

| Service | Stack | Port | Purpose |
|---------|-------|------|---------|
| `backend/` | Django + DRF + simplejwt | 8000 | User auth, groups, expenses, splits, balances |
| `settlement_service/` | FastAPI | 8001 | Fetches group data from Django, computes minimum transfers |
| `frontend/` | React (Vite) | 5173 | Login, groups/expenses UI, settlement summary |

## How to run

**Prereqs:** Python 3.11+, Node 18+.

### ⚡ Fastest: one command, one terminal

```bash
# from the repo root — installs nothing, just starts everything
python dev.py
```

That starts Django (+ port 8000), the settlement service (8001), and the
React frontend (5173) as **background processes in the single terminal**,
merges their logs with `[django]` / `[settle]` / `[vite]` prefixes, and
`Ctrl+C` stops all of them. Skip anything you don't need with
`python dev.py --no-frontend` (also `--no-backend`, `--no-settle`).

Windows alternative that opens each service in its **own window**:
double-click `start_dev.bat` (or run it from the terminal). Close each
window to stop that service.

### Manually (three terminals — the conventional way)

Each of these is a long-running process that blocks its terminal, which is
why the manual route needs three of them:

```bash
# Terminal 1 — Django core API
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

```bash
# Terminal 2 — FastAPI settlement service
cd settlement_service
pip install -r requirements.txt
# uses the same DJANGO_SECRET_KEY (default matches backend dev key)
# set DJANGO_SECRET_KEY and DJANGO_URL if you change them in settings.py
uvicorn main:app --port 8001
```

```bash
# Terminal 3 — React frontend
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### Try it
1. Register two accounts (e.g. `alice` and `bob`).
2. Alice creates a group, then opens it and **adds Bob from the Members card** —
   start typing Bob's username and pick him from the suggestions.
3. Alice or Bob adds an expense — it is split **equally** among all members.
   Every expense row shows who paid and each member's share.
4. Press **See who owes whom** to view the minimal settlement.

## API surface

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api/auth/register/` | public | returns access + refresh tokens |
| POST | `/api/auth/login/` | public | simplejwt token pair |
| GET  | `/api/groups/` | user JWT | groups the user belongs to |
| POST | `/api/groups/` | user JWT | create a group |
| GET  | `/api/groups/<id>/` | user JWT + membership | group + balances + expenses |
| POST | `/api/groups/<id>/` | user JWT + membership | add expense; `paid_by` is always the caller |
| POST | `/api/groups/<id>/members/` | user JWT + **creator** | add an existing user by `{"username": "bob"}` |
| GET  | `/api/users/?q=bob` | user JWT | search registered usernames (member picker) |
| GET  | `/api/internal/groups/<id>/` | user JWT + `X-Internal-Token` | settlement service only |
| POST | `/settle` | user JWT | body `{"group_id": N}` → minimal transfers |

## Tenant isolation (the important part)

Tenant identity is **never** taken from a client-supplied user or group id. Every
group-scoped lookup goes through `_user_groups(request.user)` which is derived
exclusively from that token's `user_id`'s `Membership` rows:

```python
def _user_groups(user):
    return Group.objects.filter(memberships__user=user)

def _get_group_or_403(request, group_id):
    return _user_groups(request.user).filter(id=group_id).first()  # None -> 404
```

`ExpenseSerializer.validate` likewise re-checks that every split target is a
member of the group, and `ExpenseSerializer.create` forces `paid_by` to the
authenticated user — a client cannot charge someone else or split to outsiders.

Because responses are a 404 for both "group doesn't exist" and "you're not in
it", non-members can't even probe group existence.

**Service-to-service:** the FastAPI `/settle` endpoint verifies the caller's JWT
itself, then forwards that same token to Django, which re-enforces membership
*and* independently requires the shared `X-Internal-Token` (derived from
`SECRET_KEY`). So the settlement path can never leak another tenant's data.

## Settlement algorithm

`settlement_service/settlement.py` implements the classic **minimum cash flow**
greedy: take the biggest debtor and the biggest creditor, transfer
`min(owed, owed_to)` between them, and repeat. Each transfer zeroes at least
one party, so at most `n-1` transfers — the theoretical minimum for `n` members.

Edge cases handled:
- empty group / all-zero balances → no transfers
- single member with a non-zero balance → no transfers (nothing to settle with)
- **rounding**: all math is in integer cents from Django through FastAPI;
  equal splits distribute remainder cents so `sum(splits) == amount` always,
  and *which* members absorb the leftover cents rotates from one expense to
  the next — so shares that are divisible in total come out exact (₹1000 +
  ₹500 over 3 members is ₹500 each, not 500.01/500.00/499.99)

## Tests

```bash
cd backend && python manage.py test api        # 19 tests: isolation, splits, members, auth, token claims
cd settlement_service && python -m unittest test_settlement   # 6 tests: algorithm edge cases
```

An end-to-end `smoke_test.ps1` exercise registers users, creates a group,
adds members, adds expenses, and verifies the settlement response.