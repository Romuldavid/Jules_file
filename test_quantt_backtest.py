"""
test_quantt_backtest.py
Модульные тесты для проверки аудита стратегий из библиотеки Quantt.
"""

import unittest
import os
import pandas as pd
from quantt_moex_backtest import run_quantt_backtests


class TestQuanttBacktests(unittest.TestCase):
    def test_run_quantt_backtests(self):
        metrics_df, equity_df = run_quantt_backtests()
        self.assertIsInstance(metrics_df, pd.DataFrame)
        self.assertIsInstance(equity_df, pd.DataFrame)
        self.assertFalse(metrics_df.empty)

        # Проверка стратегий
        strategies = metrics_df["Strategy"].tolist()
        self.assertTrue(any("Selling Volatility" in s for s in strategies))
        self.assertTrue(any("Cross-Sectional Momentum" in s for s in strategies))
        self.assertTrue(any("Market Making" in s for s in strategies))
        self.assertTrue(any("FORTS Basis Arbitrage" in s for s in strategies))

        # Проверка создания файлов
        self.assertTrue(os.path.exists("quantt_strategies_metrics.csv"))
        self.assertTrue(os.path.exists("quantt_strategies_equity.csv"))
        self.assertTrue(os.path.exists("quantt_strategies_chart.png"))


if __name__ == "__main__":
    unittest.main()
