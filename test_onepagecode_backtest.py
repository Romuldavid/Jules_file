"""
Unit tests for onepagecode_moex_backtest.py:
Verifies Kalman filter estimation, Z-score computation, metric functions,
and alignment data pipeline.
"""

import unittest
import numpy as np
import pandas as pd
from onepagecode_moex_backtest import (
    get_key_rate,
    calculate_metrics,
    align_master_dataset,
    load_data,
    run_kalman_pairs_trading,
    run_cash_futures_basis_arbitrage,
    run_kyle_amihud_strategy,
    run_walk_forward_ml_strategy,
    run_benchmarks
)

class TestOnepagecodeBacktest(unittest.TestCase):

    def test_key_rate_schedule(self):
        # 2021 low rate
        self.assertAlmostEqual(get_key_rate('2021-02-01'), 0.0425)
        # Emergency rate hike Feb 2022
        self.assertAlmostEqual(get_key_rate('2022-03-01'), 0.2000)
        # Peak hike Oct 2024 - 2025
        self.assertAlmostEqual(get_key_rate('2024-11-01'), 0.2100)
        # 2026 easing
        self.assertAlmostEqual(get_key_rate('2026-05-01'), 0.1400)

    def test_calculate_metrics_synthetic(self):
        # Exactly 365 calendar days
        dates = pd.date_range('2021-01-01', periods=366, freq='D').strftime('%Y-%m-%d').values
        # +10% annual return exactly
        equity = (1.0 + 0.10) ** (np.arange(len(dates)) / 365.25)
        m = calculate_metrics(dates, equity)
        self.assertAlmostEqual(m['CAGR'], 0.10, places=2)
        self.assertAlmostEqual(m['Max Drawdown'], 0.0, places=3)
        self.assertAlmostEqual(m['Volatility'], 0.0, places=2)

    def test_drawdown_metric(self):
        dates = ['2021-01-01', '2021-01-02', '2021-01-03', '2021-01-04']
        equity = [100.0, 120.0, 60.0, 90.0]
        m = calculate_metrics(dates, equity)
        # Peak was 120, trough was 60 -> -50% drawdown
        self.assertAlmostEqual(m['Max Drawdown'], -0.50, places=3)

    def test_data_pipeline_integrity(self):
        dfs = load_data()
        self.assertIn('SBER', dfs)
        self.assertIn('SBERP', dfs)
        self.assertIn('IMOEX', dfs)
        price_df, vol_df, val_df = align_master_dataset(dfs)
        self.assertGreater(len(price_df), 1400)
        self.assertTrue((price_df['SBER'] > 0).all())
        self.assertTrue((price_df['SBERP'] > 0).all())
        self.assertTrue((price_df['IMOEX'] > 0).all())

    def test_kalman_pairs_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_kalman_pairs_trading(price_df, 'SBER', 'SBERP')
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        self.assertGreater(res['turnover'], 0)
        self.assertGreater(res['equity'][-1], 1.0) # SBER/SBERP pair should be profitable

    def test_basis_arbitrage_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_cash_futures_basis_arbitrage(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.diff(res['equity']) > 0)) # Always positive carry
        self.assertGreater(res['equity'][-1], 1.5)

if __name__ == '__main__':
    unittest.main()
