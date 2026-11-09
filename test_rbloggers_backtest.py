"""
test_rbloggers_backtest.py
Модульные тесты для проверки корректности квантовых вычислений,
финансовых метрик и алгоритмов бэктестирования стратегий с R-bloggers.
"""

import unittest
import numpy as np
import pandas as pd
from rbloggers_moex_backtest import calculate_metrics, run_rbloggers_backtests


class TestRBloggersBacktest(unittest.TestCase):
    def setUp(self):
        # Синтетический ряд с известными параметрами
        # 252 торговых дня, стабильная доходность 10% годовых
        daily_ret = (1.0 + 0.10) ** (1.0 / 252) - 1.0
        dates = pd.date_range("2023-01-01", periods=252, freq="B")
        self.steady_rets = pd.Series(daily_ret, index=dates)
        self.zero_rf = pd.Series(0.0, index=dates)

        # Безрисковая ставка 8%
        rf_daily = (1.0 + 0.08) ** (1.0 / 252) - 1.0
        self.rf_8pct = pd.Series(rf_daily, index=dates)

    def test_calculate_metrics_steady(self):
        m = calculate_metrics(self.steady_rets, self.zero_rf)
        self.assertAlmostEqual(m["CAGR"], 0.10, places=3)
        self.assertAlmostEqual(m["MaxDrawdown"], 0.0, places=4)
        self.assertAlmostEqual(m["WinRate"], 1.0, places=4)

    def test_calculate_metrics_excess_sharpe(self):
        # Доходность 10% при безрисковой ставке 8%
        # Добавляем волатильность
        np.random.seed(42)
        noise = np.random.normal(0, 0.01, size=len(self.steady_rets))
        noisy_rets = self.steady_rets + noise
        m = calculate_metrics(noisy_rets, self.rf_8pct)
        self.assertTrue(m["Volatility"] > 0)
        self.assertTrue("Sharpe" in m)
        self.assertTrue("Sortino" in m)
        self.assertTrue("Calmar" in m)

    def test_empty_or_nan_series(self):
        empty_s = pd.Series([], dtype=float)
        m = calculate_metrics(empty_s, empty_s)
        self.assertEqual(m, {})

    def test_backtest_execution_and_output_files(self):
        metrics_df, equity_df = run_rbloggers_backtests()
        self.assertIsInstance(metrics_df, pd.DataFrame)
        self.assertIsInstance(equity_df, pd.DataFrame)
        self.assertGreater(len(metrics_df), 5)
        self.assertGreater(len(equity_df), 500)

        # Проверка обязательных колонок
        expected_cols = ["Strategy", "CAGR", "Volatility", "Sharpe", "Sortino", "MaxDrawdown", "Calmar", "WinRate", "ProfitFactor", "TotalReturn"]
        for c in expected_cols:
            self.assertIn(c, metrics_df.columns)

        # Проверка наличия ключевых стратегий
        strategies = metrics_df["Strategy"].tolist()
        self.assertTrue(any("Adaptive Asset Allocation" in s for s in strategies))
        self.assertTrue(any("Volatility Targeting" in s for s in strategies))
        self.assertTrue(any("Cointegration Pairs" in s for s in strategies))
        self.assertTrue(any("Trend Following" in s for s in strategies))
        self.assertTrue(any("Mean Reversion" in s for s in strategies))


if __name__ == "__main__":
    unittest.main()
