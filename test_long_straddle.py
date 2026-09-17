import unittest
import math
from long_straddle_bond_backtest import (
    INITIAL_CAPITAL, CB_RATE_INIT, BOND_SPREAD, BOND_YIELD_ANNUAL, TAKE_PROFIT_PCT,
    black76_call, black76_put
)

class TestLongStraddleStrategy(unittest.TestCase):

    def test_bond_yield_calculation(self):
        expected_rate = (7.50 + 1.00) / 100.0
        self.assertAlmostEqual(BOND_YIELD_ANNUAL, expected_rate, places=6)

        # Bond yield over 90 days on 1,000,000 RUB
        q_income = INITIAL_CAPITAL * BOND_YIELD_ANNUAL * (90 / 365.0)
        self.assertGreater(q_income, 0)
        self.assertAlmostEqual(q_income, 20958.9041, places=2)

    def test_black76_option_pricing(self):
        F = 100.0
        K = 100.0
        T = 0.25
        r = 0.085
        sigma = 0.20

        call_val = black76_call(F, K, T, r, sigma)
        put_val = black76_put(F, K, T, r, sigma)

        self.assertGreater(call_val, 0)
        self.assertGreater(put_val, 0)
        # Put-Call parity for futures options: C - P = exp(-rT) * (F - K)
        parity_diff = (call_val - put_val) - math.exp(-r * T) * (F - K)
        self.assertAlmostEqual(parity_diff, 0.0, places=5)

    def test_take_profit_target(self):
        premium_paid = 10000.0
        target_profit = TAKE_PROFIT_PCT * premium_paid
        self.assertEqual(target_profit, 2000.0)

if __name__ == '__main__':
    unittest.main()
