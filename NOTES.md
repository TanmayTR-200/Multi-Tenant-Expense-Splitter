# WeAudit — submission notes

## 1. One thing I didn't know before this project and how I figured it out

I didn't know that Django can run *old* code without telling me.

I added a delete button to the dashboard. The code was correct, but the button never showed up, and the API response was missing the new field I had just written.

How I figured it out: I compared what the running server actually returned with what my code said it should return. They didn't match — so the server was running old code. The cause: `dev.py` starts Django with `--noreload`, which turns off auto-reload, so code changes only appear after a restart. I restarted the server and the button appeared. I also added a note about this to the README so nobody trips on it again.

Lesson: when the UI disagrees with code I just wrote, I check the running server before I check the code.

One more thing I learned along the way: Django tests never touch my real database. They build a throwaway in-memory copy, run the fake users (`alice`, `bob`) inside it, and wipe it when tests end. That's why the fake names in `tests.py` never show up in my real data.

## 2. One place where I disagreed with or corrected an AI suggestion

The AI suggested protecting the internal endpoint (the one that gives the settlement service group data) with just one shared secret token.

I disagreed. With only a shared token, anyone holding it could fetch *any* group's data for *any* user — that breaks the tenant isolation this whole project is built around.

My fix: the endpoint now requires **both** — the shared token (proves the request came from our own settlement service) **and** a valid user token that is re-checked against group membership (proves this user is allowed to see this group). So a user can only settle groups they're actually in. The endpoint also returns 404 for both "no such group" and "not your group", so nobody can even discover which groups exist.

A second one is more personal: the AI pushed hard to keep the test suite, and I wanted to delete `tests.py` ("it already works, why test again?"). I kept it in the end, because the tests check security rules I would never manually re-test every time — only the creator can delete a group (403 for other members, 404 for strangers, 401 with no login).

## 3. One thing I'd do differently with more time

Let people split an expense by custom amounts, instead of always splitting equally. Equal splits work, but real life isn't equal.

With more time I would:

- allow custom per-person amounts on each expense (equal split stays the default)
- add an invite link instead of typing usernames
- replace the browser's plain "confirm" popup for deleting with a proper modal plus an "undo" window, so a misclick isn't permanent
