import unittest
import numpy as np
import pandas as pd
from smartlab_strategies_backtest import calculate_metrics


class TestSmartlabBacktest(unittest.TestCase):
    def test_metrics_flat_series(self):
        # Если портфель не изменился за 1 год
        dates = pd.date_range("2023-01-01", "2024-01-01", freq="B")
        equity = pd.Series(1.0, index=dates)
        metrics = calculate_metrics(equity, risk_free_rate=0.10)

        self.assertAlmostEqual(metrics["Total Return"], 0.0, places=4)
        self.assertAlmostEqual(metrics["CAGR"], 0.0, places=4)
        self.assertAlmostEqual(metrics["Max Drawdown"], 0.0, places=4)
        self.assertAlmostEqual(metrics["Annual Volatility"], 0.0, places=4)

    def test_metrics_doubling_series(self):
        # Портфель удвоился за 1 год линейно
        dates = pd.date_range("2023-01-01", "2024-01-01", freq="B")
        vals = np.linspace(1.0, 2.0, len(dates))
        equity = pd.Series(vals, index=dates)
        metrics = calculate_metrics(equity, risk_free_rate=0.10)

        self.assertAlmostEqual(metrics["Total Return"], 1.0, places=2)
        self.assertGreater(metrics["CAGR"], 0.90)
        self.assertAlmostEqual(metrics["Max Drawdown"], 0.0, places=4)
        self.assertGreater(metrics["Sharpe Ratio"], 0.0)
        self.assertGreater(metrics["Calmar Ratio"], 0.0)

    def test_drawdown_calculation(self):
        # Просадка 20%
        dates = pd.date_range("2023-01-01", periods=5, freq="D")
        vals = [100.0, 120.0, 96.0, 110.0, 120.0]  # от 120 падение до 96 = -20%
        equity = pd.Series(vals, index=dates)
        metrics = calculate_metrics(equity, risk_free_rate=0.0)

        self.assertAlmostEqual(metrics["Max Drawdown"], 0.20, places=4)


if __name__ == "__main__":
    unittest.main()
