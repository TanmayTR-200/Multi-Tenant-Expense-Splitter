from collections import deque


def minimum_cash_flow(balances_cents: dict) -> list:
    """Collapse arbitrary debts into the fewest transfers.

    Args:
        balances_cents: {user_id: net_balance_cents} where positive means
            the user should receive money and negative means they owe it.

    Returns:
        [{'from': uid, 'to': uid, 'amount_cents': int}, ...]

    Edge cases handled:
      - empty group / all-zero balances -> []
      - single member (who somehow has a non-zero balance) -> []
      - float-free: everything in integer cents; totals always balance
    """
    debtors = deque()
    creditors = deque()
    for uid, bal in balances_cents.items():
        if bal < 0:
            debtors.append([uid, -bal])
        elif bal > 0:
            creditors.append([uid, bal])

    transfers = []
    while debtors and creditors:
        debtor, owed = debtors[0]
        creditor, owed_to = creditors[0]
        amount = min(owed, owed_to)
        transfers.append({'from': debtor, 'to': creditor, 'amount_cents': amount})
        if owed > owed_to:
            debtors[0][1] = owed - owed_to
            creditors.popleft()
        elif owed_to > owed:
            creditors[0][1] = owed_to - owed
            debtors.popleft()
        else:
            debtors.popleft()
            creditors.popleft()
    return transfers
