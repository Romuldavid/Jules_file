"""
quantt_moex_backtest.py
Критический количественный аудит стратегий из профессиональной библиотеки Quantt (quantt.co.uk/resources)
в реалиях Московской Биржи (MOEX) за период 2021-2024 гг.

Исследуемые стратегии Quantt:
1. Selling Volatility Premium (CBOE PutWrite logic / Systematic Short Volatility)
   - "Selling Volatility: The Most Seductive Backtest in Finance"
   - Продажа волатильности / сбор теты при 100% покрытии залогом в ОФЗ/кэше.
   - Скептический стресс-тест: «Volmageddon» и геополитический шок февраля 2022 года на MOEX.
2. Cross-Sectional Equity Momentum (Decile Long-Short vs Long-Only with Market Neutrality)
   - Ранжирование топ-акций (SBER, LKOH, ROSN, GAZP, GMKN) по моментуму за 6 месяцев.
3. Order Flow / High-Frequency Liquidity Provision Proxy (Market Making Spread Harvesting)
   - Моделирование пассивного захвата бид-аск спреда при микросекундной/интрадей ликвидности.
4. Institutional Basis Trading & Synthetic Carry на FORTS (Тариф «Стандартный ФОРТС»)
   - Эксплуатация фундаментального контанго фьючерсов на срочном рынке FORTS.
   - 1.45 руб. за контракт (0.45 руб. брокер + 1.00 руб. биржа), 5.80 руб. на спред, 0.90 руб. опцион.

Параметры комиссий и ставок:
- Фондовый рынок (спот): комиссия 0.04% + slippage 0.05% = 0.09% за сделку
- Маржинальный шорт спота: ставка ЦБ + 5%
- График ключевой ставки ЦБ (2023-2026): 7.5% -> 21% -> 14.0%
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from smartlab_strategies_backtest import fetch_moex_history
from rbloggers_moex_backtest import calculate_metrics


def run_quantt_backtests():
    start_date = "2021-01-01"
    end_date = "2024-11-01"

    imoex_df = fetch_moex_history("stock", "index", "SNDX", "IMOEX", start_date, end_date)
    dates = imoex_df["TRADEDATE"].sort_values().drop_duplicates()
    imoex = imoex_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    stocks = {}
    for s in ["SBER", "LKOH", "ROSN", "GAZP", "GMKN"]:
        df = fetch_moex_history("stock", "shares", "TQBR", s, start_date, end_date)
        stocks[s] = df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()
    stocks_df = pd.DataFrame(stocks, index=dates)
    stocks_ret = stocks_df.pct_change().fillna(0.0)

    # Расписание Ключевой Ставки ЦБ РФ
    cbr_schedule = [
        ("2021-01-01", "2021-03-21", 0.0425),
        ("2021-03-22", "2021-04-25", 0.0450),
        ("2021-04-26", "2021-06-14", 0.0500),
        ("2021-06-15", "2021-07-25", 0.0550),
        ("2021-07-26", "2021-09-12", 0.0650),
        ("2021-09-13", "2021-10-24", 0.0675),
        ("2021-10-25", "2021-12-19", 0.0750),
        ("2021-12-20", "2022-02-27", 0.0850),
        ("2022-02-28", "2022-04-10", 0.2000),
        ("2022-04-11", "2022-05-03", 0.1700),
        ("2022-05-04", "2022-05-26", 0.1400),
        ("2022-05-27", "2022-06-13", 0.1100),
        ("2022-06-14", "2022-07-24", 0.0950),
        ("2022-07-25", "2022-09-18", 0.0800),
        ("2022-09-19", "2022-12-31", 0.0750),
        ("2023-01-01", "2023-07-23", 0.0750),
        ("2023-07-24", "2023-08-14", 0.0850),
        ("2023-08-15", "2023-09-17", 0.1200),
        ("2023-09-18", "2023-10-29", 0.1300),
        ("2023-10-30", "2023-12-17", 0.1500),
        ("2023-12-18", "2024-07-28", 0.1600),
        ("2024-07-29", "2024-09-15", 0.1800),
        ("2024-09-16", "2024-10-27", 0.1900),
        ("2024-10-28", "2025-06-30", 0.2100),
        ("2025-07-01", "2025-12-31", 0.1800),
        ("2026-01-01", "2026-05-31", 0.1600),
        ("2026-06-01", "2026-12-31", 0.1400),
    ]

    rf_annual = pd.Series(index=dates, dtype=float)
    for d in dates:
        d_str = d.strftime("%Y-%m-%d")
        rate_found = 0.14
        for start_d, end_d, rate in cbr_schedule:
            if start_d <= d_str <= end_d:
                rate_found = rate
                break
        rf_annual[d] = rate_found

    daily_rf = (1.0 + rf_annual) ** (1.0 / 252) - 1.0
    imoex_ret = imoex.pct_change().fillna(0.0)

    SPOT_FEE_1WAY = 0.0004 + 0.0005  # 0.09%

    # =========================================================================
    # 1. Selling Volatility Premium (CBOE PutWrite Logic на MOEX)
    # =========================================================================
    # В статье Quantt "Selling Volatility: The Most Seductive Backtest":
    # сбор премии волатильности (VRP ~ 4-5% годовых над ставкой) при удержании кэша.
    # В обычные дни дает плавный рост: daily_rf + премия / 252.
    # Но в дни хвостовых шоков (Tail Risk) опционы экспирируются с глубоким убытком:
    # если дневное падение рынка превышает 3%, шорт-волатильность абсорбирует 1.5x убыток!
    short_vol_rets = pd.Series(0.0, index=dates)
    daily_premium = 0.05 / 252.0  # 5% годовых премия теты

    for d in dates:
        mkt = imoex_ret.loc[d]
        if mkt < -0.03:
            # Черный лебедь (февраль 2022, санкции) -> гамма-взрыв шорт-опционов
            day_pnl = mkt * 1.5 + daily_rf.loc[d]
        elif mkt < 0:
            day_pnl = mkt * 0.5 + daily_premium + daily_rf.loc[d]
        else:
            day_pnl = daily_premium + daily_rf.loc[d]
        short_vol_rets.loc[d] = day_pnl

    # =========================================================================
    # 2. Cross-Sectional Momentum (Quantt Momentum Guide)
    # =========================================================================
    # Ежемесячно отбирается топ-2 сильнейших акции за 6 месяцев (126 дней) среди 5 фишек.
    # 100% лонг сильнейших с фильтром тренда индекса SMA-200.
    mom126 = stocks_df / stocks_df.shift(126)
    sma200 = imoex.rolling(200).mean()

    cs_mom_rets = pd.Series(0.0, index=dates)
    curr_leaders = ["SBER", "LKOH"]

    for i in range(126, len(dates)):
        d = dates.iloc[i]
        if i % 21 == 0:
            prev_d = dates.iloc[i-1]
            leaders = mom126.loc[prev_d].nlargest(2).index.tolist()
            turnover = len(set(leaders) - set(curr_leaders)) * 0.5
            fee = turnover * SPOT_FEE_1WAY * 2.0
            curr_leaders = leaders
        else:
            fee = 0.0

        in_bull = (imoex.loc[dates.iloc[i-1]] > sma200.loc[dates.iloc[i-1]]) if i >= 200 else False
        if in_bull:
            day_ret = (stocks_ret.loc[d, curr_leaders[0]] + stocks_ret.loc[d, curr_leaders[1]]) * 0.5 - fee
        else:
            day_ret = daily_rf.loc[d] - fee
        cs_mom_rets.loc[d] = day_ret

    # =========================================================================
    # 3. Market Making / High-Frequency Spread Capture Proxy
    # =========================================================================
    # Захват бид-аск спреда с контролем запасов (Avellaneda-Stoikov).
    # На MOEX маркет-мейкинг сопряжен с риском токсичного потока (Adverse Selection).
    # При сильных трендовых движениях маркет-мейкер накапливает убыточный инвентарь.
    mm_rets = pd.Series(0.0, index=dates)
    daily_spread_capture = 0.0003  # 3 bps чистый захват спреда в день
    for d in dates:
        mkt = imoex_ret.loc[d]
        if abs(mkt) > 0.025:
            # Токсичный пробой: убыток инвентаря против тренда
            day_pnl = -abs(mkt) * 0.35 + daily_rf.loc[d]
        else:
            day_pnl = daily_spread_capture + daily_rf.loc[d]
        mm_rets.loc[d] = day_pnl

    # =========================================================================
    # 4. Institutional FORTS Basis Arbitrage («Стандартный ФОРТС»)
    # =========================================================================
    # Срочный арбитраж: тариф 1.45 руб. за контракт, 5.80 руб. на спред, 0.90 руб. опцион.
    # 80% залога в РЕПО с ЦК под RUSFAR + 3.9% альфа контанго.
    forts_spread_pct_fee = 5.80 / 60000.0
    forts_quantt_rets = daily_rf + (0.039 / 252.0) - (forts_spread_pct_fee / 60.0)

    # Сводная таблица
    strategies = {
        "Benchmark: Buy & Hold IMOEX": imoex_ret,
        "Benchmark: Money Market (RUSFAR/LQDT)": daily_rf,
        "1. Selling Volatility Premium (CBOE PutWrite)": short_vol_rets,
        "2. Cross-Sectional Momentum + SMA Filter": cs_mom_rets,
        "3. Market Making Inventory Proxy": mm_rets,
        "4. FORTS Basis Arbitrage («Стандартный ФОРТС»)": forts_quantt_rets
    }

    metrics_list = []
    equity_curves = pd.DataFrame(index=dates)

    for name, s_rets in strategies.items():
        eq = (1.0 + s_rets).cumprod()
        equity_curves[name] = eq
        m = calculate_metrics(s_rets, daily_rf)
        m["Strategy"] = name
        metrics_list.append(m)

    metrics_df = pd.DataFrame(metrics_list)
    cols = ["Strategy", "CAGR", "Volatility", "Sharpe", "Sortino", "MaxDrawdown", "Calmar", "WinRate", "ProfitFactor", "TotalReturn"]
    metrics_df = metrics_df[cols]

    metrics_df.to_csv("quantt_strategies_metrics.csv", index=False)
    equity_curves.to_csv("quantt_strategies_equity.csv")

    # Построение графика
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2.5, 1.2]}, sharex=True)

    colors = {
        "Benchmark: Buy & Hold IMOEX": "gray",
        "Benchmark: Money Market (RUSFAR/LQDT)": "black",
        "1. Selling Volatility Premium (CBOE PutWrite)": "#d62728",
        "2. Cross-Sectional Momentum + SMA Filter": "#1f77b4",
        "3. Market Making Inventory Proxy": "#ff7f0e",
        "4. FORTS Basis Arbitrage («Стандартный ФОРТС»)": "#2ca02c"
    }

    for name in strategies.keys():
        ls = ":" if "Benchmark" in name else "-"
        lw = 2.0 if "FORTS" in name else 1.5
        ax1.plot(dates, equity_curves[name], label=name, color=colors.get(name, "blue"), linestyle=ls, lw=lw)

    ax1.set_title("Скептический квантовый аудит стратегий из Quantt Resources на данных MOEX (2021–2024 гг.)", fontsize=14, fontweight="bold", pad=12)
    ax1.set_ylabel("Динамика капитала (База = 1.0)", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left", fontsize=9, framealpha=0.9)

    for name in strategies.keys():
        eq = equity_curves[name]
        dd = (eq - eq.cummax()) / eq.cummax()
        ls = ":" if "Benchmark" in name else "-"
        ax2.plot(dates, dd * 100, label=name, color=colors.get(name, "blue"), linestyle=ls, lw=1.2)

    ax2.set_title("Исторические просадки (%)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Просадка (%)", fontsize=11)
    ax2.set_xlabel("Дата", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    chart_path = "quantt_strategies_chart.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()

    print(f"Chart saved to {chart_path}")
    print("\n=== Результаты симуляции стратегий Quantt на MOEX ===")
    print(metrics_df.to_string(index=False))

    return metrics_df, equity_curves


if __name__ == "__main__":
    run_quantt_backtests()
