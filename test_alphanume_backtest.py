"""
Unit tests for alphanume_moex_backtest.py:
Verifies strategy return computations, metric calculations, Key Rate interpolation,
and data integrity.
"""

import unittest
import numpy as np
import pandas as pd
from alphanume_moex_backtest import (
    get_key_rate,
    calculate_metrics,
    align_master_dataset,
    load_data,
    run_dividend_aristocrat_strategy,
    run_alphanume_basis_carry,
    run_leveraged_decay_short,
    run_trading_halt_reversal_strategy,
    run_benchmarks
)

class TestAlphanumeBacktest(unittest.TestCase):

    def test_key_rate_schedule(self):
        self.assertAlmostEqual(get_key_rate('2021-02-01'), 0.0425)
        self.assertAlmostEqual(get_key_rate('2022-03-01'), 0.2000)
        self.assertAlmostEqual(get_key_rate('2024-11-01'), 0.2100)
        self.assertAlmostEqual(get_key_rate('2026-05-01'), 0.1400)

    def test_calculate_metrics_synthetic(self):
        dates = pd.date_range('2021-01-01', periods=366, freq='D').strftime('%Y-%m-%d').values
        equity = (1.0 + 0.12) ** (np.arange(len(dates)) / 365.25)
        m = calculate_metrics(dates, equity)
        self.assertAlmostEqual(m['CAGR'], 0.12, places=2)
        self.assertAlmostEqual(m['Max Drawdown'], 0.0, places=3)
        self.assertAlmostEqual(m['Volatility'], 0.0, places=2)

    def test_data_pipeline_integrity(self):
        dfs = load_data()
        self.assertIn('SBER', dfs)
        self.assertIn('LKOH', dfs)
        self.assertIn('IMOEX', dfs)
        price_df, vol_df, val_df = align_master_dataset(dfs)
        self.assertGreater(len(price_df), 1400)
        self.assertTrue((price_df['SBER'] > 0).all())
        self.assertTrue((price_df['IMOEX'] > 0).all())

    def test_basis_arbitrage_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_alphanume_basis_carry(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.diff(res['equity']) > 0)) # Monotonically increasing carry
        self.assertGreater(res['equity'][-1], 1.5)

    def test_short_leveraged_decay_destruction(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_leveraged_decay_short(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        # Due to high borrow cost, equity must decrease significantly over 2021-2026
        self.assertLess(res['equity'][-1], 0.60)

    def test_dividend_aristocrat_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_dividend_aristocrat_strategy(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        self.assertGreater(res['turnover'], 0)

if __name__ == '__main__':
    unittest.main()
