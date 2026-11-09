"""
test_rpubs_backtest.py
Модульные тесты для проверки аудита стратегий с RPubs.
"""

import unittest
import os
import pandas as pd
from rpubs_moex_backtest import run_rpubs_backtests


class TestRPubsBacktests(unittest.TestCase):
    def test_run_rpubs_backtests(self):
        metrics_df, equity_df = run_rpubs_backtests()
        self.assertIsInstance(metrics_df, pd.DataFrame)
        self.assertIsInstance(equity_df, pd.DataFrame)
        self.assertFalse(metrics_df.empty)

        # Проверка стратегий
        strategies = metrics_df["Strategy"].tolist()
        self.assertTrue(any("GARCH" in s for s in strategies))
        self.assertTrue(any("Markowitz" in s for s in strategies))
        self.assertTrue(any("Faber" in s for s in strategies))
        self.assertTrue(any("FORTS" in s for s in strategies))

        # Проверка создания файлов
        self.assertTrue(os.path.exists("rpubs_strategies_metrics.csv"))
        self.assertTrue(os.path.exists("rpubs_strategies_equity.csv"))
        self.assertTrue(os.path.exists("rpubs_strategies_chart.png"))


if __name__ == "__main__":
    unittest.main()
