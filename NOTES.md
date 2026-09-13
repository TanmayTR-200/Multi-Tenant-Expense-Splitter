# NOTES.md

## 1. One thing I didn't know before this project and how I figured it out

**Django REST Framework's `save(**kwargs)` doesn't merge kwargs into
`validated_data` cleanly on custom `ModelSerializer.create()`.**

I initially wrote `expense = Expense.objects.create(**validated_data, group=group)`
inside `create()` and passed extra keyword args like `paid_by=` from the view via
`serializer.save(group=group, paid_by=request.user)`. That blew up with
`QuerySet.create() got multiple values for keyword argument 'group'` because DRF
injects `save()`'s kwargs into `validated_data` before calling `create()`, so
`group` appeared twice. I figured it out by reading the DRF source path from the
traceback (`serializer.save()` → `self.create.validated_data` update), and fixed it
by pulling `group`/`request` from the serializer's `context` instead. This also
turned out to be the right *security* shape: the group and every referenced
user (split targets, and the optional `paid_by`) are validated server-side
against the group's membership — client input picks *which member*, but can
never make an expense touch a non-member.

**A second one, from the final stretch — "why does `tests.py` contain fake
users that never show up in my real data?"** I traced it instead of shrugging:
`manage.py test` reads the same `DATABASES` setting the app uses, sees the
engine is SQLite, and builds a disposable **in-memory** twin
(`file:memorydb_default?mode=memory` in the test output), then replays the same
migrations into it. The fake `alice`/`bob` users live in a same-schema
throwaway that is wiped the moment tests end — `db.sqlite3` is never opened.
Fake data and real data share a *shape*, never *contents*, which is exactly why
a test pass means something without risking anything.

**And the bug that taught me the most: `--noreload`.** I shipped the dashboard
delete button; the code was right and the button didn't render — the live API
response was missing the new `is_creator` field entirely. Root cause: `dev.py`
launches Django with `--noreload`, so the long-running server was serving *old*
code. Diffing the live `/api/groups/` payload against the serializer on disk
made it obvious in minutes. Lesson: when the UI disagrees with code you just
wrote, suspect the running process before the code.

## 2. One place where I disagreed with or corrected an AI suggestion

An earlier draft suggested authenticating Django's internal settlement-data
endpoint with **only** the shared internal token (`X-Internal-Token`), on the
grounds that "the settlement service legitimately needs full group data." I
disagreed: that would let the settlement service return *any* group's data for
*any* caller, i.e. a tenant-isolation hole at the exact integration boundary the
task scores. I made the endpoint require **both** the internal service token
(proves the request came from our FastAPI service) **and** a valid user JWT whose
membership is re-checked server-side (proves the caller is allowed to see that
group). The FastAPI side forwards the caller's own token, so the group a user can
settle is always walled off by their memberships — and the endpoint returns 404
for both "no group" and "not your group" so it can't be probed.

A second, more personal one: the AI argued strongly for keeping the test suite
and I pushed back hard — "the feature already runs, why test it again?" I
wanted to delete `tests.py` outright. Its analogies didn't move me; what moved
me was the concrete list of *security rules* I would never manually re-check on
every change — creator deletes → 204, non-creator member → 403, non-member →
404 (can't even probe existence), no token → 401, and the delete cascades with
no orphaned expenses. Once I also understood tests run against a disposable
in-memory DB (see §1), keeping them cost nothing and deleting them saved
nothing. I kept them — 26 backend tests at submission time.

## 3. One thing I'd do differently with more time

**Add per-user, per-expense custom split amounts in the UI and an invite flow.**
Right now expenses split equally among all group members (remainder cents
distributed deterministically) and membership is granted by the creator typing a
username. With more time I'd:

- let the creator assign arbitrary split *weights* per member (with the same
  remainder algorithm), and
- replace username-typing with an invite/link flow plus a "you were added to
  group X" surface in the UI,
- move Django onto Postgres and run the settlement computation as a pure library
  against the same data (idempotency/ETags for concurrent balances), 
- add a retry/backoff wrapper on the FastAPI→Django call, and
- ship the Docker Compose setup for one-command startup,
- and replace the delete confirmation's `window.confirm` with a proper modal
  plus a short "undo" window (soft delete) so a misclick isn't permanent.