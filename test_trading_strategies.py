import unittest
import numpy as np
import pandas as pd
from trading_strategies_engine import (
    DonchianTrendFollowing,
    RsiPullbackMeanReversion,
    DividendMomentumStrategy,
    TacticalAssetAllocation,
    CashAndCarryArbitrage,
)


class TestTradingStrategiesEngine(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2023-01-01", periods=100, freq="B")
        self.prices = pd.Series(np.linspace(100, 200, 100), index=self.dates)
        self.rf = pd.Series(0.10 / 252, index=self.dates)

    def test_donchian_trend_following(self):
        strat = DonchianTrendFollowing(upper_window=10, lower_window=5)
        eq = strat.run(self.prices, self.rf)
        metrics = strat.evaluate()

        self.assertGreater(eq.iloc[-1], 1.0)
        self.assertIn("CAGR", metrics)
        self.assertIn("Sharpe Ratio", metrics)

    def test_rsi_pullback(self):
        # Создаем колеблющийся ряд цен
        osc_prices = pd.Series(100 + 10 * np.sin(np.linspace(0, 10, 100)), index=self.dates)
        strat = RsiPullbackMeanReversion(rsi_period=2, oversold=30, overbought=70)
        eq = strat.run(osc_prices, self.rf)
        metrics = strat.evaluate()

        self.assertEqual(len(eq), 100)
        self.assertIn("Total Return", metrics)

    def test_dividend_momentum(self):
        basket = pd.DataFrame({
            "A": np.linspace(100, 120, 100),
            "B": np.linspace(50, 70, 100)
        }, index=self.dates)
        strat = DividendMomentumStrategy(ann_div_yield=0.08)
        eq = strat.run(basket)
        metrics = strat.evaluate()

        self.assertGreater(eq.iloc[-1], 1.10)
        self.assertIn("CAGR", metrics)

    def test_tactical_allocation(self):
        gold = pd.Series(np.linspace(5000, 6000, 100), index=self.dates)
        strat = TacticalAssetAllocation(stock_weight=0.4, gold_weight=0.3, sma_filter=20)
        eq = strat.run(self.prices, gold, self.rf)
        metrics = strat.evaluate()

        self.assertGreater(eq.iloc[-1], 1.0)
        self.assertLess(metrics["Max Drawdown"], 0.15)

    def test_cash_and_carry(self):
        strat = CashAndCarryArbitrage(contango_premium_ann=0.03)
        eq = strat.run(self.rf)
        metrics = strat.evaluate()

        self.assertGreater(eq.iloc[-1], 1.0)
        self.assertAlmostEqual(metrics["Max Drawdown"], 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
