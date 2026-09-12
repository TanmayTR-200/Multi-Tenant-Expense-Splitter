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
- ship the Docker Compose setup for one-command startup.