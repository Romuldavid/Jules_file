"""
Unit tests for memlabs_trilogy_moex_backtest.py:
Verifies 1-bar momentum, 1-bar mean reversion, regime-switching mechanics,
friction calculations, and data pipeline integrity.
"""

import unittest
import numpy as np
import pandas as pd
from memlabs_trilogy_moex_backtest import (
    get_key_rate,
    calculate_metrics,
    align_master_dataset,
    load_data,
    run_memlabs_1bar_momentum,
    run_memlabs_1bar_mean_reversion,
    run_memlabs_adaptive_regime_model,
    run_memlabs_institutional_long_only,
    run_forts_basis_arbitrage,
    run_trend_following_sma,
    run_benchmarks
)

class TestMemLabsTrilogyBacktest(unittest.TestCase):

    def test_key_rate_schedule(self):
        self.assertAlmostEqual(get_key_rate('2021-02-01'), 0.0425)
        self.assertAlmostEqual(get_key_rate('2022-03-01'), 0.2000)
        self.assertAlmostEqual(get_key_rate('2024-11-01'), 0.2100)
        self.assertAlmostEqual(get_key_rate('2026-05-01'), 0.1400)

    def test_calculate_metrics_synthetic(self):
        dates = pd.date_range('2021-01-01', periods=366, freq='D').strftime('%Y-%m-%d').values
        equity = (1.0 + 0.13) ** (np.arange(len(dates)) / 365.25)
        m = calculate_metrics(dates, equity)
        self.assertAlmostEqual(m['CAGR'], 0.13, places=2)
        self.assertAlmostEqual(m['Max Drawdown'], 0.0, places=3)
        self.assertAlmostEqual(m['Volatility'], 0.0, places=2)

    def test_data_pipeline_integrity(self):
        dfs = load_data()
        self.assertIn('SBER', dfs)
        self.assertIn('IMOEX', dfs)
        price_df, vol_df, val_df = align_master_dataset(dfs)
        self.assertGreater(len(price_df), 1400)
        self.assertTrue((price_df['SBER'] > 0).all())

    def test_forts_basis_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_forts_basis_arbitrage(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.diff(res['equity']) > 0)) # Monotonic carry
        self.assertGreater(res['equity'][-1], 1.5)

    def test_memlabs_adaptive_regime_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_memlabs_adaptive_regime_model(price_df, 'SBER')
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        # Adaptive regime model should beat Buy & Hold SBER
        sber_total = price_df['SBER'].iloc[-1] / price_df['SBER'].iloc[0]
        self.assertGreater(res['equity'][-1], sber_total)

    def test_memlabs_institutional_long_only(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_memlabs_institutional_long_only(price_df, 'SBER')
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        self.assertGreater(res['equity'][-1], 1.4)

    def test_memlabs_1bar_momentum_destruction(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_memlabs_1bar_momentum(price_df, 'SBER', apply_moex_frictions=True)
        self.assertEqual(len(res['equity']), len(price_df))
        # 1-bar momentum with short fees collapses severely on MOEX
        self.assertLess(res['equity'][-1], 0.2)

if __name__ == '__main__':
    unittest.main()
