# WeAudit — submission notes

## 1. One thing I didn't know before this project and how I figured it out

This was my first time working with Django — I'd used FastAPI and Express before, but not Django. Early on I hit something that confused me: I added a delete button and a new API field, but the button never showed up and the response was missing the field, even though the code looked right. I compared what the server was actually sending against what my code said it should send, and they didn't match — so the server wasn't running what I'd written at all. Turned out dev.py starts Django with --noreload, so code changes only apply after a restart. Restarting fixed it, and I added a note to the README about it. Small thing, but it taught me not to trust that "the code is correct" means "the server is running that code".

## 2. One place where I disagreed with or corrected an AI suggestion

The AI's original equal-split logic always gave leftover cents to the same members every time — specifically whoever had the lowest user ID. That seemed fine at first, but I realized it wasn't: if the same people always absorb the extra cent, their balance drifts a tiny bit every single expense. Over enough expenses, it adds up to a real, visible error — I found a case where ₹1000 + ₹500 split three ways came out to ₹500.01 / ₹500.00 / ₹499.99 instead of an exact ₹500 each, and the settlement screen showed someone owed ₹499.99 instead of ₹500.

I disagreed with leaving it that way, since it looked correct on any single expense but was quietly wrong over time. My fix: instead of always giving the extra cent to the same members, rotate who absorbs it based on how many expenses the group already has (expense count % number of members). So the bias doesn't build up in one direction — it spreads out and evens back to exact amounts.

## 3. One thing I'd do differently with more time

Let people split an expense by custom amounts, instead of always splitting equally. Equal splits work, but real life isn't equal.

With more time I would:

- allow custom per-person amounts on each expense (equal split stays the default)
- add an invite link instead of typing usernames
- replace the browser's plain "confirm" popup for deleting with a proper modal plus an "undo" window, so a misclick isn't permanent