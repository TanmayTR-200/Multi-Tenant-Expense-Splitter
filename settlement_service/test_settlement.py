import unittest

from settlement import minimum_cash_flow


class TestMinimumCashFlow(unittest.TestCase):
    def test_simple_pair(self):
        # A paid 300, B's share 300 -> B owes A 300
        result = minimum_cash_flow({1: 300, 2: -300})
        self.assertEqual(result, [{'from': 2, 'to': 1, 'amount_cents': 300}])

    def test_empty(self):
        self.assertEqual(minimum_cash_flow({}), [])
        self.assertEqual(minimum_cash_flow({1: 0, 2: 0}), [])

    def test_single_member_nonzero(self):
        # Degenerate data: one member with non-zero balance cannot settle
        # with anyone; must return [] and not infinite-loop.
        self.assertEqual(minimum_cash_flow({1: 500}), [])
        self.assertEqual(minimum_cash_flow({1: -500}), [])

    def test_collapse_three_way(self):
        # A: +60, B: -40, C: -20  ->  B->A 40, C->A 20 (2 transfers)
        result = minimum_cash_flow({1: 60, 2: -40, 3: -20})
        self.assertEqual(len(result), 2)
        # Totals must balance
        for uid in (1, 2, 3):
            net = sum(
                t['amount_cents'] * (1 if t['to'] == uid else -1 if t['from'] == uid else 0)
                for t in result
            )
            self.assertEqual(net, {1: 60, 2: -40, 3: -20}[uid])

    def test_rounding_cents(self):
        # 100 cents split 3 ways in Django leaves 34/33/33; balances sum to 0.
        result = minimum_cash_flow({1: 34, 2: -17, 3: -17})
        self.assertEqual(len(result), 2)
        total_out = sum(t['amount_cents'] for t in result if t['from'] == 2) + sum(
            t['amount_cents'] for t in result if t['from'] == 3
        )
        self.assertEqual(total_out, 34)


if __name__ == '__main__':
    unittest.main()
