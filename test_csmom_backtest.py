"""
test_csmom_backtest.py
Модульные тесты для проверки корректности квантового бэктеста Cross-Sectional Momentum на MOEX (2021-2026).
"""

import unittest
import os
import pandas as pd
from csmom_moex_backtest import run_csmom_backtests, load_cached_series


class TestCSMOMBacktest(unittest.TestCase):
    def test_load_cached_data_until_2026(self):
        imoex = load_cached_series("IMOEX", "stock", "index", "SNDX", "2021-01-01", "2026-11-10")
        self.assertFalse(imoex.empty)
        max_date = imoex["TRADEDATE"].max()
        # Должен включать данные ноября 2026 года (06.11.2026)
        self.assertEqual(max_date.year, 2026)
        self.assertEqual(max_date.month, 11)
        self.assertGreaterEqual(max_date.day, 6)

    def test_csmom_backtest_execution(self):
        metrics_df, equity_df = run_csmom_backtests()
        self.assertIsInstance(metrics_df, pd.DataFrame)
        self.assertIsInstance(equity_df, pd.DataFrame)
        self.assertFalse(metrics_df.empty)
        self.assertGreater(len(equity_df), 1400)

        strategies = metrics_df["Strategy"].tolist()
        self.assertTrue(any("CSMOM 6M + SMA200" in s for s in strategies))
        self.assertTrue(any("CSMOM 3M + SMA200" in s for s in strategies))
        self.assertTrue(any("CSMOM Naive" in s for s in strategies))
        self.assertTrue(any("CSMOM Long/Short" in s for s in strategies))

        # Проверка создания файлов
        self.assertTrue(os.path.exists("csmom_strategies_metrics.csv"))
        self.assertTrue(os.path.exists("csmom_strategies_equity.csv"))
        self.assertTrue(os.path.exists("csmom_strategies_chart.png"))

    def test_filter_reduces_drawdown(self):
        metrics_df, _ = run_csmom_backtests()
        naive_row = metrics_df[metrics_df["Strategy"].str.contains("CSMOM Naive", regex=False)].iloc[0]
        sma_row = metrics_df[metrics_df["Strategy"].str.contains("CSMOM 6M + SMA200", regex=False)].iloc[0]

        # Фильтр SMA200 должен снижать максимальную просадку более чем в 2 раза
        self.assertLess(sma_row["MaxDrawdown"], naive_row["MaxDrawdown"])
        self.assertGreater(sma_row["CAGR"], naive_row["CAGR"])


if __name__ == "__main__":
    unittest.main()
