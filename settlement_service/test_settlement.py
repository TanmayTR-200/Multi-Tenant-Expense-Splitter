import unittest

from settlement import minimum_cash_flow


class TestMinimumCashFlow(unittest.TestCase):
    def test_simple_pair(self):
        result = minimum_cash_flow({1: 300, 2: -300})
        self.assertEqual(result, [{'from': 2, 'to': 1, 'amount_cents': 300}])

    def test_empty(self):
        self.assertEqual(minimum_cash_flow({}), [])
        self.assertEqual(minimum_cash_flow({1: 0, 2: 0}), [])

    def test_single_member_nonzero(self):
        self.assertEqual(minimum_cash_flow({1: 500}), [])
        self.assertEqual(minimum_cash_flow({1: -500}), [])

    def test_collapse_three_way(self):
        result = minimum_cash_flow({1: 60, 2: -40, 3: -20})
        self.assertEqual(len(result), 2)
        for uid in (1, 2, 3):
            net = sum(
                t['amount_cents'] * (1 if t['to'] == uid else -1 if t['from'] == uid else 0)
                for t in result
            )
            self.assertEqual(net, {1: 60, 2: -40, 3: -20}[uid])

    def test_chain_nets_to_single_transfer(self):
        result = minimum_cash_flow({1: -100, 2: 0, 3: 100})
        self.assertEqual(
            result, [{'from': 1, 'to': 3, 'amount_cents': 100}]
        )

    def test_rounding_cents(self):
        result = minimum_cash_flow({1: 34, 2: -17, 3: -17})
        self.assertEqual(len(result), 2)
        total_out = sum(t['amount_cents'] for t in result if t['from'] == 2) + sum(
            t['amount_cents'] for t in result if t['from'] == 3
        )
        self.assertEqual(total_out, 34)


if __name__ == '__main__':
    unittest.main()
