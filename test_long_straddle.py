import unittest
import math
from long_straddle_bond_backtest import (
    INITIAL_CAPITAL, BOND_SPREAD, TAKE_PROFIT_PCT,
    get_cb_rate_for_date, get_bond_yield_for_period,
    black76_call, black76_put
)

class TestLongStraddleStrategy(unittest.TestCase):

    def test_dynamic_cb_rate_schedule(self):
        self.assertEqual(get_cb_rate_for_date('2023-01-01'), 7.50)
        self.assertEqual(get_cb_rate_for_date('2023-08-20'), 12.00)
        self.assertEqual(get_cb_rate_for_date('2024-11-01'), 21.00)
        self.assertEqual(get_cb_rate_for_date('2026-07-01'), 14.00)

    def test_bond_yield_period_calculation(self):
        # 1 day yield at 7.5% + 1% = 8.5% p.a.
        y_1day = get_bond_yield_for_period('2023-01-01', '2023-01-02')
        self.assertAlmostEqual(y_1day, 0.085 / 365.0, places=6)

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
