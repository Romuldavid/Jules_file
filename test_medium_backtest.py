"""
test_medium_backtest.py
Модульные тесты для квантового аудита стратегий с Medium.com.
"""

import unittest
import os
import pandas as pd
from medium_moex_backtest import run_medium_backtests


class TestMediumBacktests(unittest.TestCase):
    def test_run_medium_backtests(self):
        metrics_df, equity_df = run_medium_backtests()
        self.assertIsInstance(metrics_df, pd.DataFrame)
        self.assertIsInstance(equity_df, pd.DataFrame)
        self.assertFalse(metrics_df.empty)

        # Проверка ключевых стратегий
        strategies = metrics_df["Strategy"].tolist()
        self.assertTrue(any("SuperTrend" in s for s in strategies))
        self.assertTrue(any("Machine Learning" in s for s in strategies))
        self.assertTrue(any("Bollinger Bands" in s for s in strategies))
        self.assertTrue(any("Stop-Loss Paradox" in s for s in strategies))
        self.assertTrue(any("FORTS Calendar Arbitrage" in s for s in strategies))

        # Проверка превосходства FORTS арбитража
        forts_row = metrics_df[metrics_df["Strategy"].str.contains("FORTS Calendar")].iloc[0]
        ml_row = metrics_df[metrics_df["Strategy"].str.contains("Machine Learning")].iloc[0]
        self.assertGreater(forts_row["CAGR"], ml_row["CAGR"])
        self.assertGreater(forts_row["TotalReturn"], ml_row["TotalReturn"])

        # Проверка создания файлов
        self.assertTrue(os.path.exists("medium_strategies_metrics.csv"))
        self.assertTrue(os.path.exists("medium_strategies_equity.csv"))
        self.assertTrue(os.path.exists("medium_strategies_chart.png"))


if __name__ == "__main__":
    unittest.main()
