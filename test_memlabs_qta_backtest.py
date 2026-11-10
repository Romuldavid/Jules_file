"""
Unit tests for memlabs_qta_moex_backtest.py:
Verifies pure numpy linear OLS, logistic regression gradient descent,
feature creation, and strategy execution.
"""

import unittest
import numpy as np
import pandas as pd
from memlabs_qta_moex_backtest import (
    fit_linear_ols,
    fit_logistic_gd,
    create_memlabs_ar_df,
    get_key_rate,
    calculate_metrics,
    align_master_dataset,
    load_data,
    run_memlabs_ar_model,
    run_memlabs_logistic_model,
    run_memlabs_institutional_adaptation,
    run_forts_basis_arbitrage,
    run_benchmarks
)

class TestMemLabsQTABacktest(unittest.TestCase):

    def test_fit_linear_ols(self):
        # y = 2*x1 + 3*x2 + 1
        X = np.array([[1.0, 1.0, 2.0], [1.0, 2.0, 3.0], [1.0, 3.0, 4.0], [1.0, 4.0, 5.0]])
        y = np.array([9.0, 14.0, 19.0, 24.0])
        beta = fit_linear_ols(X, y)
        self.assertAlmostEqual(beta[0], 1.0, places=2)
        self.assertAlmostEqual(beta[1], 2.0, places=2)
        self.assertAlmostEqual(beta[2], 3.0, places=2)

    def test_fit_logistic_gd(self):
        X = np.array([[1.0, 1.0], [1.0, 2.0], [1.0, 10.0], [1.0, 12.0]])
        y = np.array([0.0, 0.0, 1.0, 1.0])
        w = fit_logistic_gd(X, y, lr=0.1, epochs=200)
        # Should predict higher probability for large X
        p_low = 1.0 / (1.0 + np.exp(-np.dot([1.0, 1.5], w)))
        p_high = 1.0 / (1.0 + np.exp(-np.dot([1.0, 11.0], w)))
        self.assertGreater(p_high, p_low)
        self.assertGreater(p_high, 0.5)

    def test_create_memlabs_ar_df(self):
        s = pd.Series([100.0, 102.0, 101.0, 105.0, 107.0])
        df = create_memlabs_ar_df(s, no_lags=2)
        self.assertIn('close_log_return', df.columns)
        self.assertIn('close_log_return_lag_1', df.columns)
        self.assertIn('close_log_return_lag_2', df.columns)
        self.assertTrue(np.isnan(df['close_log_return_lag_2'].iloc[1]))

    def test_key_rate_schedule(self):
        self.assertAlmostEqual(get_key_rate('2021-02-01'), 0.0425)
        self.assertAlmostEqual(get_key_rate('2022-03-01'), 0.2000)
        self.assertAlmostEqual(get_key_rate('2024-11-01'), 0.2100)
        self.assertAlmostEqual(get_key_rate('2026-05-01'), 0.1400)

    def test_data_pipeline_integrity(self):
        dfs = load_data()
        self.assertIn('SBER', dfs)
        self.assertIn('IMOEX', dfs)
        price_df, vol_df, val_df = align_master_dataset(dfs)
        self.assertGreater(len(price_df), 1400)
        self.assertTrue((price_df['SBER'] > 0).all())

    def test_institutional_adaptation_execution(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_memlabs_institutional_adaptation(price_df, 'SBER', no_lags=3)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        # Institutional adaptation should outperform naive Buy & Hold SBER
        sber_total = price_df['SBER'].iloc[-1] / price_df['SBER'].iloc[0]
        self.assertGreater(res['equity'][-1], sber_total)

    def test_naive_ar1_destruction(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_memlabs_ar_model(price_df, 'SBER', no_lags=1, apply_moex_frictions=True)
        self.assertEqual(len(res['equity']), len(price_df))
        # Naive AR(1) with 620 trades and short fees must collapse severely
        self.assertLess(res['equity'][-1], 0.3)

if __name__ == '__main__':
    unittest.main()
