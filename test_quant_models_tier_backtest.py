"""
Unit tests for quant_models_tier_moex_backtest.py:
Verifies model strategy return computations, Kalman filter updates,
HMM regime filtering, and metric integrity.
"""

import unittest
import numpy as np
import pandas as pd
from quant_models_tier_moex_backtest import (
    get_key_rate,
    calculate_metrics,
    align_master_dataset,
    load_data,
    run_kalman_filter_strategy,
    run_nelson_siegel_basis_carry,
    run_hmm_regime_switching,
    run_garch_vol_targeting,
    run_naive_arima_regression,
    run_black_scholes_putwrite,
    run_benchmarks
)

class TestQuantModelsTierBacktest(unittest.TestCase):

    def test_key_rate_schedule(self):
        self.assertAlmostEqual(get_key_rate('2021-02-01'), 0.0425)
        self.assertAlmostEqual(get_key_rate('2022-03-01'), 0.2000)
        self.assertAlmostEqual(get_key_rate('2024-11-01'), 0.2100)
        self.assertAlmostEqual(get_key_rate('2026-05-01'), 0.1400)

    def test_calculate_metrics_synthetic(self):
        dates = pd.date_range('2021-01-01', periods=366, freq='D').strftime('%Y-%m-%d').values
        equity = (1.0 + 0.15) ** (np.arange(len(dates)) / 365.25)
        m = calculate_metrics(dates, equity)
        self.assertAlmostEqual(m['CAGR'], 0.15, places=2)
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

    def test_nelson_siegel_basis_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_nelson_siegel_basis_carry(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.diff(res['equity']) > 0)) # Monotonically increasing carry
        self.assertGreater(res['equity'][-1], 1.5)

    def test_kalman_filter_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_kalman_filter_strategy(price_df, 'SBER', 'SBERP')
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        self.assertGreater(res['turnover'], 0)
        self.assertGreater(res['equity'][-1], 1.0)

    def test_hmm_regime_switching_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_hmm_regime_switching(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        # HMM regime filter should outperform Buy & Hold IMOEX
        imoex_total = price_df['IMOEX'].iloc[-1] / price_df['IMOEX'].iloc[0]
        self.assertGreater(res['equity'][-1], imoex_total)

    def test_black_scholes_putwrite_destruction(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_black_scholes_putwrite(price_df)
        self.assertEqual(len(res['equity']), len(price_df))
        # Due to unhedged crash exposure, equity must collapse to near zero
        self.assertLess(res['equity'][-1], 0.05)

if __name__ == '__main__':
    unittest.main()
