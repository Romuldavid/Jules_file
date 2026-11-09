"""
trading_strategies_engine.py
Модульный Python-движок для проверки работоспособности, бэктестирования
и анализа жизнеспособных стратегий на российском рынке (MOEX).

Каждая стратегия реализована в виде отдельного независимого класса:
1. DonchianTrendFollowing - пробой каналов Дончяна с размещением кэша в фонде ликвидности
2. RsiPullbackMeanReversion - возврат к средней при краткосрочной перепроданности (Connors RSI-2)
3. DividendMomentumStrategy - выбор топ дивидендных лидеров с реинвестированием дивидендов
4. TacticalAssetAllocation - мультиактивный портфель (Акции + Золото + Кэш) с защитным трендовым фильтром
5. CashAndCarryArbitrage - безрисковый базисный арбитраж ставок (контанго фьючерса к споту)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from smartlab_strategies_backtest import fetch_moex_history, calculate_metrics


class BaseStrategy:
    """Базовый класс стратегии с расчетом аналитических метрик."""

    def __init__(self, name="BaseStrategy", cost_per_trade=0.0008, risk_free_rate=0.12):
        self.name = name
        self.cost_per_trade = cost_per_trade
        self.risk_free_rate = risk_free_rate
        self.equity_curve = None
        self.metrics = {}

    def run(self, data):
        raise NotImplementedError("Метод run() должен быть переопределен в дочернем классе.")

    def evaluate(self):
        if self.equity_curve is not None:
            self.metrics = calculate_metrics(self.equity_curve, risk_free_rate=self.risk_free_rate)
            self.metrics["Strategy"] = self.name
        return self.metrics


class DonchianTrendFollowing(BaseStrategy):
    """
    1. Трендовая стратегия пробоя канала (20 дней вход, 10 дней выход).
    Свободные деньги размещаются под ставку денежного рынка (фонд LQDT).
    """

    def __init__(self, upper_window=20, lower_window=10, cost_per_trade=0.0008):
        super().__init__(name="1. Trend Following (Donchian+LQDT)", cost_per_trade=cost_per_trade)
        self.upper_window = upper_window
        self.lower_window = lower_window

    def run(self, prices_series, daily_rf_series):
        high_ch = prices_series.rolling(self.upper_window).max().shift(1)
        low_ch = prices_series.rolling(self.lower_window).min().shift(1)

        dates = prices_series.index
        eq = [1.0]
        cur_pos = 0

        for i in range(1, len(prices_series)):
            p_prev = prices_series.iloc[i - 1]
            p_cur = prices_series.iloc[i]
            r_asset = (p_cur / p_prev) - 1.0
            r_cash = daily_rf_series.iloc[i]

            signal = cur_pos
            if cur_pos == 0:
                if p_cur > high_ch.iloc[i]:
                    signal = 1
            elif cur_pos == 1:
                if p_cur < low_ch.iloc[i]:
                    signal = 0

            fee = self.cost_per_trade if signal != cur_pos else 0.0
            r_day = (r_asset if cur_pos == 1 else r_cash) - fee
            eq.append(eq[-1] * (1.0 + r_day))
            cur_pos = signal

        self.equity_curve = pd.Series(eq, index=dates)
        return self.equity_curve


class RsiPullbackMeanReversion(BaseStrategy):
    """
    2. Стратегия выкупа краткосрочной перепроданности (RSI-2).
    Покупка при RSI(2) < 15 выше EMA-200, фиксация при RSI(2) > 70.
    """

    def __init__(self, rsi_period=2, oversold=15, overbought=70, cost_per_trade=0.0008):
        super().__init__(name="2. Mean-Reversion (RSI-2 Pullback)", cost_per_trade=cost_per_trade)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def run(self, prices_series, daily_rf_series):
        ema_200 = prices_series.ewm(span=200, adjust=False).mean()
        delta = prices_series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))

        dates = prices_series.index
        eq = [1.0]
        cur_pos = 0

        for i in range(1, len(prices_series)):
            p_prev = prices_series.iloc[i - 1]
            p_cur = prices_series.iloc[i]
            r_asset = (p_cur / p_prev) - 1.0
            r_cash = daily_rf_series.iloc[i]

            signal = cur_pos
            if cur_pos == 0:
                if p_cur > ema_200.iloc[i] and rsi.iloc[i] < self.oversold:
                    signal = 1
            elif cur_pos == 1:
                if rsi.iloc[i] > self.overbought:
                    signal = 0

            fee = self.cost_per_trade if signal != cur_pos else 0.0
            r_day = (r_asset if cur_pos == 1 else r_cash) - fee
            eq.append(eq[-1] * (1.0 + r_day))
            cur_pos = signal

        self.equity_curve = pd.Series(eq, index=dates)
        return self.equity_curve


class DividendMomentumStrategy(BaseStrategy):
    """
    3. Дивидендный моментум («Альфа-скакуны»): инвестиции в топ дивидендных фишек
    с реинвестированием дивидендов.
    """

    def __init__(self, ann_div_yield=0.10, cost_per_trade=0.0008):
        super().__init__(name="3. Dividend Momentum (Alpha Horses)", cost_per_trade=cost_per_trade)
        self.ann_div_yield = ann_div_yield

    def run(self, basket_prices_df):
        dates = basket_prices_df.index
        norm_prices = basket_prices_df / basket_prices_df.iloc[0]
        basket = norm_prices.mean(axis=1)
        basket_ret = basket.pct_change().fillna(0)

        daily_div = (1.0 + self.ann_div_yield) ** (1.0 / 252) - 1.0
        total_daily_ret = basket_ret + daily_div

        eq = (1.0 + total_daily_ret).cumprod()
        self.equity_curve = eq / eq.iloc[0]
        return self.equity_curve


class TacticalAssetAllocation(BaseStrategy):
    """
    4. Тактическое распределение (Акции + Золото + Кэш) с защитным фильтром SMA-100.
    """

    def __init__(self, stock_weight=0.40, gold_weight=0.30, sma_filter=100, cost_per_trade=0.0008):
        super().__init__(name="4. Tactical Allocation (Equity+Gold+Cash)", cost_per_trade=cost_per_trade)
        self.stock_weight = stock_weight
        self.gold_weight = gold_weight
        self.sma_filter = sma_filter

    def run(self, stock_index_series, gold_series, daily_rf_series):
        dates = stock_index_series.index
        sma_filter = stock_index_series.rolling(self.sma_filter).mean()
        stock_ret = stock_index_series.pct_change().fillna(0)
        gold_ret = gold_series.pct_change().fillna(0)

        eq_ret = []
        for i in range(len(dates)):
            is_bull = stock_index_series.iloc[i] > sma_filter.iloc[i] if not np.isnan(sma_filter.iloc[i]) else True
            w_stock = self.stock_weight if is_bull else 0.0
            w_gold = self.gold_weight
            w_cash = 1.0 - (w_stock + w_gold)

            r_d = w_stock * stock_ret.iloc[i] + w_gold * gold_ret.iloc[i] + w_cash * daily_rf_series.iloc[i]
            eq_ret.append(r_d)

        eq = (1.0 + pd.Series(eq_ret, index=dates)).cumprod()
        self.equity_curve = eq / eq.iloc[0]
        return self.equity_curve


class CashAndCarryArbitrage(BaseStrategy):
    """
    5. Базисный арбитраж / Cash and Carry: безрисковая доходность
    (ставка денежного рынка + премия контанго фьючерса к споту).
    """

    def __init__(self, contango_premium_ann=0.028):
        super().__init__(name="5. Cash & Carry / Basis Arbitrage", cost_per_trade=0.0)
        self.contango_premium_ann = contango_premium_ann

    def run(self, daily_rf_series):
        dates = daily_rf_series.index
        daily_spread = (1.0 + self.contango_premium_ann) ** (1.0 / 252) - 1.0
        total_daily_ret = daily_rf_series + daily_spread
        eq = (1.0 + total_daily_ret).cumprod()
        self.equity_curve = eq / eq.iloc[0]
        return self.equity_curve


def run_all_strategies_test():
    """Тестирование и бэктест всех стратегий на реальных данных МосБиржи."""
    print("=" * 80)
    print("ЗАПУСК ДВИЖКА ТОРГОВЫХ СТРАТЕГИЙ (TRADING STRATEGIES ENGINE)")
    print("=" * 80)

    start_date = "2021-01-01"
    end_date = "2024-11-01"

    # Загрузка данных
    imoex_df = fetch_moex_history("stock", "index", "SNDX", "IMOEX", start_date, end_date)
    dates = imoex_df["TRADEDATE"]
    imoex = imoex_df.set_index("TRADEDATE")["CLOSE"]

    sber = fetch_moex_history("stock", "shares", "TQBR", "SBER", start_date, end_date).set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()
    lkoh = fetch_moex_history("stock", "shares", "TQBR", "LKOH", start_date, end_date).set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()
    tatn = fetch_moex_history("stock", "shares", "TQBR", "TATN", start_date, end_date).set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()
    gold = fetch_moex_history("stock", "shares", "GLDRUB_TOM", "GLDRUB_TOM", start_date, end_date).set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    # Ставка ЦБ / Фонд ликвидности (LQDT)
    rates = pd.Series(index=dates, dtype=float)
    for d in dates:
        rates[d] = 0.065 if d.year == 2021 else (0.13 if d.year == 2022 else (0.115 if d.year == 2023 else 0.18))
    daily_rf = (1.0 + rates) ** (1.0 / 252) - 1.0
    lqdt_equity = (1.0 + daily_rf).cumprod()
    lqdt_equity = lqdt_equity / lqdt_equity.iloc[0]

    # Инициализация и запуск стратегий
    s1 = DonchianTrendFollowing()
    s1.run(sber, daily_rf)
    m1 = s1.evaluate()

    s2 = RsiPullbackMeanReversion()
    s2.run(sber, daily_rf)
    m2 = s2.evaluate()

    s3 = DividendMomentumStrategy()
    basket_df = pd.DataFrame({"SBER": sber, "LKOH": lkoh, "TATN": tatn}, index=dates)
    s3.run(basket_df)
    m3 = s3.evaluate()

    s4 = TacticalAssetAllocation()
    s4.run(imoex, gold, daily_rf)
    m4 = s4.evaluate()

    s5 = CashAndCarryArbitrage()
    s5.run(daily_rf)
    m5 = s5.evaluate()

    # Бенчмарки
    bh_imoex = imoex / imoex.iloc[0]
    m_imoex = calculate_metrics(bh_imoex)
    m_imoex["Strategy"] = "Benchmark: Buy & Hold IMOEX"

    m_lqdt = calculate_metrics(lqdt_equity)
    m_lqdt["Strategy"] = "Benchmark: Money Market (LQDT)"

    metrics_list = [m4, m1, m5, m3, m_lqdt, m2, m_imoex]
    summary_df = pd.DataFrame(metrics_list)
    cols = ["Strategy", "CAGR", "Total Return", "Max Drawdown", "Annual Volatility", "Sharpe Ratio", "Sortino Ratio", "Calmar Ratio", "Win Rate (Daily)"]
    summary_df = summary_df[cols]

    print("\nСВОДНАЯ ТАБЛИЦА СТРАТЕГИЙ:")
    print(summary_df.to_string(index=False, formatters={
        "CAGR": lambda x: f"{x*100:.2f}%",
        "Total Return": lambda x: f"{x*100:.2f}%",
        "Max Drawdown": lambda x: f"{x*100:.2f}%",
        "Annual Volatility": lambda x: f"{x*100:.2f}%",
        "Sharpe Ratio": lambda x: f"{x:.2f}",
        "Sortino Ratio": lambda x: f"{x:.2f}",
        "Calmar Ratio": lambda x: f"{x:.2f}",
        "Win Rate (Daily)": lambda x: f"{x*100:.1f}%",
    }))

    summary_df.to_csv("trading_strategies_summary.csv", index=False)
    print("\nМетрики сохранены в 'trading_strategies_summary.csv'")

    # Построение графиков
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.plot(s4.equity_curve, label=s4.name, lw=2.2, color="#ff7f0e")
    ax.plot(s1.equity_curve, label=s1.name, lw=2.0, color="#2b5c8f")
    ax.plot(s5.equity_curve, label=s5.name, lw=1.8, color="#6f42c1")
    ax.plot(s3.equity_curve, label=s3.name, lw=1.8, color="#28a745")
    ax.plot(lqdt_equity, label="Benchmark: Money Market (LQDT)", ls=":", lw=1.5, color="#6c757d")
    ax.plot(s2.equity_curve, label=s2.name, lw=1.5, color="#17a2b8")
    ax.plot(bh_imoex, label="Benchmark: Buy & Hold IMOEX", ls="--", lw=1.5, color="#dc3545")

    ax.set_title("Сравнение доходности торговых стратегий (2021–2024)", fontsize=14, fontweight="bold")
    ax.set_ylabel("Капитал (База = 1.0)")
    ax.legend(loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    chart_file = "trading_strategies_performance.png"
    plt.savefig(chart_file, dpi=300)
    plt.close()
    print(f"График сохранен в '{chart_file}'")

    return summary_df


if __name__ == "__main__":
    run_all_strategies_test()
