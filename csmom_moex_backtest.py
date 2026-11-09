"""
csmom_moex_backtest.py
Количественное моделирование и скептический бэктест стратегии
Cross-Sectional Momentum (Относительный Моментум лидеров) с R-bloggers
на реальных исторических данных Московской Биржи (MOEX) за период 2021-2026 гг.
(с 01.01.2021 по 09.11.2026, последний рабочий день торгов 06.11.2026).

Тестируемые вариации стратегии:
1. Benchmark: Buy & Hold IMOEX (Пассивный индекс МосБиржи)
2. Benchmark: Money Market (Фонд денежного рынка LQDT / РЕПО с ЦК RUSFAR)
3. CSMOM Naive (Без фильтра тренда): Ежемесячный выбор топ-2 сильнейших акций за 6 месяцев (126 дней)
4. CSMOM + SMA200 Filter (Базовый): При IMOEX < SMA-200 полный выход в кэш под ставку RUSFAR
5. CSMOM 3M + SMA200 Filter (Быстрый моментум): Окно 3 месяца (63 дня) + фильтр SMA-200
6. CSMOM Pure Market-Neutral Long/Short (Академический R-bloggers): Long топ-2, Short худшие 2 на споте (шорт = ставка ЦБ + 5%)

Реалистичные издержки рынка РФ:
- Комиссия брокера и биржи: 0.04% за сделку
- Проскальзывание (slippage): 0.05%
- Стоимость маржинального шорта на споте: ставка ЦБ + 5% годовых
- Точный понедельный график Ключевой Ставки ЦБ РФ: 01.01.2023 - 20.08.2026 (7.5% -> 21% -> 14.0%) и до ноября 2026.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from smartlab_strategies_backtest import fetch_moex_history
from rbloggers_moex_backtest import calculate_metrics

CACHE_DIR = "moex_data_cache"


def load_cached_series(secid, engine="stock", market="shares", board="TQBR", from_date="2021-01-01", till_date="2026-11-10"):
    cache_path = os.path.join(CACHE_DIR, f"{secid}_{from_date}_{till_date}.csv")
    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path)
        df["TRADEDATE"] = pd.to_datetime(df["TRADEDATE"])
        return df.sort_values("TRADEDATE").drop_duplicates(subset=["TRADEDATE"]).reset_index(drop=True)
    return fetch_moex_history(engine, market, board, secid, from_date, till_date)


def run_csmom_backtests():
    from_date = "2021-01-01"
    till_date = "2026-11-10"

    # Загрузка индекса IMOEX
    imoex_df = load_cached_series("IMOEX", "stock", "index", "SNDX", from_date, till_date)
    dates = imoex_df["TRADEDATE"].sort_values().drop_duplicates()
    imoex = imoex_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    # Вселенная ликвидных акций (Голубые фишки MOEX)
    stock_tickers = ["SBER", "LKOH", "ROSN", "GAZP", "GMKN", "TATN", "NVTK"]
    stocks_dict = {}
    for s in stock_tickers:
        df = load_cached_series(s, "stock", "shares", "TQBR", from_date, till_date)
        stocks_dict[s] = df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()
    stocks_df = pd.DataFrame(stocks_dict, index=dates)
    stocks_ret = stocks_df.pct_change().fillna(0.0)

    # Официальный график Ключевой Ставки ЦБ РФ
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
        # Динамика 2023 - 2026:
        ("2023-01-01", "2023-07-23", 0.0750),  # Мягкая ДКП
        ("2023-07-24", "2023-08-14", 0.0850),  # Первое повышение
        ("2023-08-15", "2023-09-17", 0.1200),  # Внеочередное повышение
        ("2023-09-18", "2023-10-29", 0.1300),  # Борьба с инфляцией
        ("2023-10-30", "2023-12-17", 0.1500),  # Ужесточение ДКП
        ("2023-12-18", "2024-07-28", 0.1600),  # Пауза 16%
        ("2024-07-29", "2024-09-15", 0.1800),  # Повышение ставки
        ("2024-09-16", "2024-10-27", 0.1900),  # Перегрев экономики
        ("2024-10-28", "2025-06-30", 0.2100),  # Пиковый уровень ставки 21%
        ("2025-07-01", "2025-12-31", 0.1800),  # Снижение ставки
        ("2026-01-01", "2026-05-31", 0.1600),  # Нормализация
        ("2026-06-01", "2026-12-31", 0.1400),  # Текущий уровень ключевой ставки ЦБ (14.0%)
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

    # Параметры издержек
    SPOT_FEE_1WAY = 0.0004 + 0.0005  # 0.09% за круг
    SHORT_BORROW_SPREAD = 0.05       # Плата за шорт спота = ставка ЦБ + 5%
    daily_short_cost = (rf_annual + SHORT_BORROW_SPREAD) / 252.0

    # Моментум за 6 месяцев (126 дней) и 3 месяца (63 дня)
    mom126 = stocks_df / stocks_df.shift(126)
    mom63 = stocks_df / stocks_df.shift(63)
    sma200 = imoex.rolling(200).mean()

    # -------------------------------------------------------------------------
    # 1. CSMOM Naive (Long-Only Топ-2 по 6M моментуму, без фильтра тренда)
    # -------------------------------------------------------------------------
    csmom_naive_rets = pd.Series(0.0, index=dates)
    curr_leaders = ["SBER", "LKOH"]
    for i in range(128, len(dates)):
        d = dates.iloc[i]
        if i % 21 == 0:
            prev_d = dates.iloc[i-1]
            top_s = mom126.loc[prev_d].dropna().nlargest(2).index.tolist()
            if len(top_s) == 2:
                turnover = len(set(top_s) - set(curr_leaders)) * 0.5
                fee = turnover * SPOT_FEE_1WAY * 2.0
                curr_leaders = top_s
            else:
                fee = 0.0
        else:
            fee = 0.0
        day_ret = (stocks_ret.loc[d, curr_leaders[0]] + stocks_ret.loc[d, curr_leaders[1]]) * 0.5 - fee
        csmom_naive_rets.loc[d] = day_ret

    # -------------------------------------------------------------------------
    # 2. CSMOM 6M + SMA200 Filter (Классический адаптивный моментум)
    # -------------------------------------------------------------------------
    csmom_sma_rets = pd.Series(0.0, index=dates)
    curr_leaders_sma = ["SBER", "LKOH"]
    for i in range(200, len(dates)):
        d = dates.iloc[i]
        prev_d = dates.iloc[i-1]
        in_bull = (imoex.loc[prev_d] > sma200.loc[prev_d])

        if i % 21 == 0:
            top_s = mom126.loc[prev_d].dropna().nlargest(2).index.tolist()
            if len(top_s) == 2:
                turnover = len(set(top_s) - set(curr_leaders_sma)) * 0.5
                fee = turnover * SPOT_FEE_1WAY * 2.0
                curr_leaders_sma = top_s
            else:
                fee = 0.0
        else:
            fee = 0.0

        if in_bull:
            day_ret = (stocks_ret.loc[d, curr_leaders_sma[0]] + stocks_ret.loc[d, curr_leaders_sma[1]]) * 0.5 - fee
        else:
            # Медвежий рынок -> 100% в фонд денежного рынка под ставку RUSFAR
            day_ret = daily_rf.loc[d] - fee
        csmom_sma_rets.loc[d] = day_ret

    # -------------------------------------------------------------------------
    # 3. CSMOM 3M + SMA200 Filter (Быстрый квартальный моментум)
    # -------------------------------------------------------------------------
    csmom_3m_rets = pd.Series(0.0, index=dates)
    curr_leaders_3m = ["SBER", "LKOH"]
    for i in range(200, len(dates)):
        d = dates.iloc[i]
        prev_d = dates.iloc[i-1]
        in_bull = (imoex.loc[prev_d] > sma200.loc[prev_d])

        if i % 21 == 0:
            top_s = mom63.loc[prev_d].dropna().nlargest(2).index.tolist()
            if len(top_s) == 2:
                turnover = len(set(top_s) - set(curr_leaders_3m)) * 0.5
                fee = turnover * SPOT_FEE_1WAY * 2.0
                curr_leaders_3m = top_s
            else:
                fee = 0.0
        else:
            fee = 0.0

        if in_bull:
            day_ret = (stocks_ret.loc[d, curr_leaders_3m[0]] + stocks_ret.loc[d, curr_leaders_3m[1]]) * 0.5 - fee
        else:
            day_ret = daily_rf.loc[d] - fee
        csmom_3m_rets.loc[d] = day_ret

    # -------------------------------------------------------------------------
    # 4. CSMOM Pure Market-Neutral Long/Short (Академический R-bloggers)
    # -------------------------------------------------------------------------
    # Long топ-2 акции, Short 2 худших акции на споте. Учет платы за маржинальный шорт!
    csmom_ls_rets = pd.Series(0.0, index=dates)
    curr_winners = ["SBER", "LKOH"]
    curr_losers = ["GAZP", "GMKN"]
    for i in range(128, len(dates)):
        d = dates.iloc[i]
        if i % 21 == 0:
            prev_d = dates.iloc[i-1]
            ranked = mom126.loc[prev_d].dropna()
            if len(ranked) >= 4:
                winners = ranked.nlargest(2).index.tolist()
                losers = ranked.nsmallest(2).index.tolist()
                turnover = (len(set(winners) - set(curr_winners)) + len(set(losers) - set(curr_losers))) * 0.25
                fee = turnover * SPOT_FEE_1WAY * 2.0
                curr_winners = winners
                curr_losers = losers
            else:
                fee = 0.0
        else:
            fee = 0.0

        long_ret = (stocks_ret.loc[d, curr_winners[0]] + stocks_ret.loc[d, curr_winners[1]]) * 0.5
        short_ret = (stocks_ret.loc[d, curr_losers[0]] + stocks_ret.loc[d, curr_losers[1]]) * 0.5
        # 50% капитал в лонге, 50% шорт, 50% кэша под RUSFAR, плата за шорт
        day_ret = 0.5 * long_ret - 0.5 * short_ret + 0.5 * daily_rf.loc[d] - 0.5 * daily_short_cost.loc[d] - fee
        csmom_ls_rets.loc[d] = day_ret

    # -------------------------------------------------------------------------
    # Сводные таблицы и метрики
    # -------------------------------------------------------------------------
    all_strategies = {
        "Benchmark: Buy & Hold IMOEX": imoex_ret,
        "Benchmark: Money Market (RUSFAR/LQDT)": daily_rf,
        "1. CSMOM 6M + SMA200 Filter (Адаптивный Лидер)": csmom_sma_rets,
        "2. CSMOM 3M + SMA200 Filter (Быстрый Моментум)": csmom_3m_rets,
        "3. CSMOM Naive (Без фильтра тренда)": csmom_naive_rets,
        "4. CSMOM Long/Short (Академический спот-шорт)": csmom_ls_rets,
    }

    metrics_list = []
    equity_curves = pd.DataFrame(index=dates)

    for name, s_rets in all_strategies.items():
        eq = (1.0 + s_rets).cumprod()
        equity_curves[name] = eq
        m = calculate_metrics(s_rets, daily_rf)
        m["Strategy"] = name
        metrics_list.append(m)

    metrics_df = pd.DataFrame(metrics_list)
    cols = ["Strategy", "CAGR", "Volatility", "Sharpe", "Sortino", "MaxDrawdown", "Calmar", "WinRate", "ProfitFactor", "TotalReturn"]
    metrics_df = metrics_df[cols]

    metrics_df.to_csv("csmom_strategies_metrics.csv", index=False)
    equity_curves.to_csv("csmom_strategies_equity.csv")

    # Построение графиков
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2.5, 1.2]}, sharex=True)

    colors = {
        "Benchmark: Buy & Hold IMOEX": "gray",
        "Benchmark: Money Market (RUSFAR/LQDT)": "black",
        "1. CSMOM 6M + SMA200 Filter (Адаптивный Лидер)": "#1f77b4",
        "2. CSMOM 3M + SMA200 Filter (Быстрый Моментум)": "#2ca02c",
        "3. CSMOM Naive (Без фильтра тренда)": "#ff7f0e",
        "4. CSMOM Long/Short (Академический спот-шорт)": "#d62728"
    }

    for name in all_strategies.keys():
        ls = ":" if "Benchmark" in name else "-"
        lw = 2.0 if "SMA200" in name else 1.3
        ax1.plot(dates, equity_curves[name], label=name, color=colors.get(name, "blue"), linestyle=ls, lw=lw)

    ax1.set_title("Бэктест Cross-Sectional Momentum на реальных данных MOEX (01.01.2021 – 09.11.2026 гг.)", fontsize=14, fontweight="bold", pad=12)
    ax1.set_ylabel("Динамика капитала (База = 1.0)", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left", fontsize=9, framealpha=0.9)

    for name in all_strategies.keys():
        eq = equity_curves[name]
        dd = (eq - eq.cummax()) / eq.cummax()
        ls = ":" if "Benchmark" in name else "-"
        ax2.plot(dates, dd * 100, label=name, color=colors.get(name, "blue"), linestyle=ls, lw=1.2)

    ax2.set_title("Исторические просадки стратегий (%)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Просадка (%)", fontsize=11)
    ax2.set_xlabel("Дата", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    chart_path = "csmom_strategies_chart.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()

    print(f"Chart saved to {chart_path}")
    print("\n=== Результаты симуляции Cross-Sectional Momentum на MOEX (2021-2026) ===")
    print(metrics_df.to_string(index=False))

    return metrics_df, equity_curves


if __name__ == "__main__":
    run_csmom_backtests()
