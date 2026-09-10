"""Per-user and per-group balance computations.

All amounts are integer cents. A positive balance means the user is owed
money by the group; a negative balance means the user owes money.
"""
from collections import defaultdict

from .models import Expense, ExpenseSplit


def compute_user_balances(group):
    """Return {user_id: balance_cents} for every member of `group`.

    paid_by increases a member's balance, their share decreases it.
    """
    balances = defaultdict(int)
    for m in group.memberships.select_related('user'):
        balances[m.user_id] += 0  # ensure every member appears

    for expense in group.expenses.all():
        balances[expense.paid_by_id] += expense.amount_cents
        for split in expense.splits.all():
            balances[split.user_id] -= split.amount_cents
    return dict(balances)


def group_net_for_user(user, group):
    """Net balance of `user` within `group` (owed-to positive, owes negative)."""
    paid = sum(
        e.amount_cents for e in Expense.objects.filter(group=group, paid_by=user)
    )
    owed = sum(
        s.amount_cents for s in ExpenseSplit.objects.filter(user=user, expense__group=group)
    )
    return paid - owed

