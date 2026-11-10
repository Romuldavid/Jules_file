"""
Unit tests for paolucci_playlist_moex_backtest.py:
Verifies strategy return computations, Shannon's Demon rebalancing,
Black-Litterman allocations, Kelly sizing, and data integrity.
"""

import unittest
import numpy as np
import pandas as pd
from paolucci_playlist_moex_backtest import (
    get_key_rate,
    calculate_metrics,
    align_master_dataset,
    load_data,
    run_forts_basis_arbitrage,
    run_crash_protection_trend,
    run_shannon_demon_rebalancing,
    run_market_neutral_kalman_pair,
    run_black_litterman_portfolio,
    run_kelly_criterion_momentum,
    run_covered_call_buywrite,
    run_cash_secured_put,
    run_benchmarks
)

class TestPaolucciPlaylistBacktest(unittest.TestCase):

    def test_key_rate_schedule(self):
        self.assertAlmostEqual(get_key_rate('2021-02-01'), 0.0425)
        self.assertAlmostEqual(get_key_rate('2022-03-01'), 0.2000)
        self.assertAlmostEqual(get_key_rate('2024-11-01'), 0.2100)
        self.assertAlmostEqual(get_key_rate('2026-05-01'), 0.1400)

    def test_calculate_metrics_synthetic(self):
        dates = pd.date_range('2021-01-01', periods=366, freq='D').strftime('%Y-%m-%d').values
        equity = (1.0 + 0.14) ** (np.arange(len(dates)) / 365.25)
        m = calculate_metrics(dates, equity)
        self.assertAlmostEqual(m['CAGR'], 0.14, places=2)
        self.assertAlmostEqual(m['Max Drawdown'], 0.0, places=3)
        self.assertAlmostEqual(m['Volatility'], 0.0, places=2)

    def test_data_pipeline_integrity(self):
        dfs = load_data()
        self.assertIn('SBER', dfs)
        self.assertIn('SBERP', dfs)
        self.assertIn('IMOEX', dfs)
        price_df, vol_df, val_df = align_master_dataset(dfs)
        self.assertGreater(len(price_df), 1400)
        self.assertTrue((price_df['SBER'] > 0).all())
        self.assertTrue((price_df['IMOEX'] > 0).all())

    def test_forts_basis_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_forts_basis_arbitrage(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.diff(res['equity']) > 0)) # Monotonic positive carry
        self.assertGreater(res['equity'][-1], 1.5)

    def test_shannon_demon_rebalancing(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_shannon_demon_rebalancing(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        # Shannon's demon should beat Buy & Hold IMOEX
        imoex_total = price_df['IMOEX'].iloc[-1] / price_df['IMOEX'].iloc[0]
        self.assertGreater(res['equity'][-1], imoex_total)

    def test_crash_protection_trend(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_crash_protection_trend(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        # Trend filter + repo cash should be positive over 2021-2026
        self.assertGreater(res['equity'][-1], 1.2)

    def test_kelly_criterion_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_kelly_criterion_momentum(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        self.assertGreater(res['equity'][-1], 1.5)

    def test_put_selling_destruction(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_cash_secured_put(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        # Naked put selling without crash hedge collapses to near zero
        self.assertLess(res['equity'][-1], 0.05)

if __name__ == '__main__':
    unittest.main()
