"""
Unit tests for kalman_mean_reversion_moex_backtest.py:
Verifies AR(1) estimation, KalmanOU filter updates, noise lever mapping,
and strategy return calculations.
"""

import unittest
import numpy as np
import pandas as pd
from kalman_mean_reversion_moex_backtest import (
    estimate_ar1,
    noise_lever_to_scale,
    KalmanOU,
    get_key_rate,
    calculate_metrics,
    align_master_dataset,
    load_data,
    run_kts_single_asset,
    run_kts_pair_spread,
    run_forts_basis_arbitrage,
    run_benchmarks
)

class TestKalmanMeanReversionBacktest(unittest.TestCase):

    def test_estimate_ar1(self):
        # Synthetic mean-reverting series
        np.random.seed(42)
        n = 100
        x = np.zeros(n)
        for t in range(1, n):
            x[t] = 0.7 * x[t-1] + np.random.normal(0, 1.0)
        res = estimate_ar1(x)
        self.assertIsNotNone(res)
        phi, mu, sigma = res
        self.assertGreater(phi, 0.4)
        self.assertLess(phi, 0.95)
        self.assertGreater(sigma, 0.5)

    def test_noise_lever_to_scale(self):
        self.assertAlmostEqual(noise_lever_to_scale(0.0), 0.1)
        self.assertAlmostEqual(noise_lever_to_scale(50.0), 5.05)
        self.assertAlmostEqual(noise_lever_to_scale(100.0), 1e8)

    def test_kalman_ou_updates(self):
        phi, mu, sigma = 0.8, 100.0, 2.0
        kf = KalmanOU(phi, mu, sigma, obs_noise_scale=1.0)
        # Price is observed at 110.0
        x_updated = kf.update(110.0)
        # Updated fair value should move towards 110.0 from 100.0
        self.assertGreater(x_updated, 100.0)
        self.assertLess(x_updated, 110.0)

    def test_key_rate_schedule(self):
        self.assertAlmostEqual(get_key_rate('2021-02-01'), 0.0425)
        self.assertAlmostEqual(get_key_rate('2022-03-01'), 0.2000)
        self.assertAlmostEqual(get_key_rate('2024-11-01'), 0.2100)
        self.assertAlmostEqual(get_key_rate('2026-05-01'), 0.1400)

    def test_data_pipeline_integrity(self):
        dfs = load_data()
        self.assertIn('SBER', dfs)
        self.assertIn('SBERP', dfs)
        self.assertIn('IMOEX', dfs)
        price_df, vol_df, val_df = align_master_dataset(dfs)
        self.assertGreater(len(price_df), 1400)
        self.assertTrue((price_df['SBER'] > 0).all())
        self.assertTrue((price_df['SBERP'] > 0).all())

    def test_kts_pair_spread_optimal(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_kts_pair_spread(price_df, 'SBER', 'SBERP', noise_lever=0.0)
        self.assertEqual(len(res['equity']), len(price_df))
        self.assertTrue(np.all(np.isfinite(res['equity'])))
        # Optimal SBER/SBERP pair should be profitable
        self.assertGreater(res['equity'][-1], 1.5)

    def test_kts_single_asset_failure(self):
        dfs = load_data()
        price_df, _, _ = align_master_dataset(dfs)
        res = run_kts_single_asset(price_df, 'SBER', noise_lever=50.0)
        self.assertEqual(len(res['equity']), len(price_df))
        # Single-asset mean reversion fails severely on trending/crashing stock
        self.assertLess(res['equity'][-1], 0.5)

if __name__ == '__main__':
    unittest.main()
