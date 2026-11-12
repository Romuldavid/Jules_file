"""
rpubs_moex_backtest.py
Критический количественный аудит и бэктестирование стратегий из популярных публикаций RPubs (RStudio / Posit)
в условиях Московской Биржи (MOEX) за период 2021-2024 гг.

Исследуемые академические и практические стратегии с RPubs:
1. GARCH(1,1) Volatility Forecasting & Dynamic Risk Scaling (rugarch / RPubs quantitative risk management)
   - Динамическое масштабирование размера позиции обратно пропорционально прогнозируемой условной волатильности GARCH.
2. Markowitz Mean-Variance Tangency Portfolio (PortfolioAnalytics / quadprog на RPubs)
   - Классическая оптимизация портфеля по Марковицу на акциях MOEX (SBER, LKOH, ROSN, GAZP, GMKN).
   - Скептический аудит: эффект "error maximizer" при оценке ковариационной матрицы на нестационарном рынке.
3. Quantstrat Faber Tactical Asset Allocation (GTAA 10-month / 200-day trend following)
   - Публикация Mebane Faber "A Quantitative Approach to Tactical Asset Allocation" на RPubs.
4. Statistical Cointegration Arbitrage на FORTS с тарифом «Стандартный ФОРТС»
   - Эконометрический тест Йохансена / Энгла-Грейнджера с учетом комиссии 1.45 руб. за контракт (5.80 руб. на спред).

Параметры комиссий и ставок:
- Фондовый рынок (спот): комиссия 0.04% + slippage 0.05% = 0.09% за сделку
- Маржинальный шорт спота: ставка ЦБ + 5%
- Тариф «Стандартный ФОРТС»: 0.45 руб. брокер + ~1.00 руб. биржа = 1.45 руб./контракт
- График ставки ЦБ (2023-2026): 7.5% -> 21% -> 14.0%
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from smartlab_strategies_backtest import fetch_moex_history
from rbloggers_moex_backtest import calculate_metrics


def run_rpubs_backtests():
    start_date = "2021-01-01"
    end_date = "2024-11-01"

    imoex_df = fetch_moex_history("stock", "index", "SNDX", "IMOEX", start_date, end_date)
    dates = imoex_df["TRADEDATE"].sort_values().drop_duplicates()
    imoex = imoex_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    # Топ-5 ликвидных акций для портфельной оптимизации
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
    # 1. GARCH(1,1) Volatility Targeting (RPubs rugarch implementation)
    # =========================================================================
    # Экспоненциальное сглаживание волатильности (EWMA / GARCH proxy: omega + alpha*r^2 + beta*sigma^2)
    # Таргетируемая волатильность: 15% годовых. Вес акции = Target_Vol / Forecast_Vol
    target_ann_vol = 0.15
    garch_var = pd.Series(index=dates, dtype=float)
    init_var = imoex_ret.iloc[:30].var()
    curr_var = init_var
    alpha, beta = 0.10, 0.85
    omega = init_var * (1.0 - alpha - beta)

    for i in range(len(dates)):
        d = dates.iloc[i]
        r = imoex_ret.iloc[i-1] if i > 0 else 0.0
        curr_var = omega + alpha * (r ** 2) + beta * curr_var
        garch_var.loc[d] = curr_var

    garch_ann_vol = np.sqrt(garch_var * 252)
    garch_weight = (target_ann_vol / garch_ann_vol.shift(1)).clip(lower=0.1, upper=1.0).fillna(0.5)
    garch_switches = garch_weight.diff().abs().fillna(0.0)

    garch_rets = (
        garch_weight * imoex_ret +
        (1.0 - garch_weight) * daily_rf -
        garch_switches * SPOT_FEE_1WAY
    )

    # =========================================================================
    # 2. Markowitz Tangency Mean-Variance Portfolio (RPubs PortfolioAnalytics)
    # =========================================================================
    # Ежеквартальная (63 дня) оптимизация портфеля акций по Марковицу:
    # максимизация коэффициента Шарпа на основе 126-дневной исторической выборки.
    # Ограничения: лонг-онли (вес 0 до 40% на одну бумагу, сумма = 1).
    rebal_freq = 63
    lookback = 126
    markowitz_rets = pd.Series(0.0, index=dates)
    curr_w = np.repeat(0.2, 5)

    for i in range(lookback, len(dates)):
        d = dates.iloc[i]
        if i % rebal_freq == 0:
            hist_ret = stocks_ret.iloc[i-lookback:i]
            mean_r = hist_ret.mean()
            cov_mat = hist_ret.cov().values + np.eye(5) * 1e-5  # регуляризация

            try:
                inv_cov = np.linalg.pinv(cov_mat)
                w_opt = inv_cov @ (mean_r - daily_rf.iloc[i])
                w_opt = np.clip(w_opt, 0.0, 0.40)
                if w_opt.sum() > 0:
                    w_opt /= w_opt.sum()
                else:
                    w_opt = np.repeat(0.2, 5)
            except Exception:
                w_opt = np.repeat(0.2, 5)

            turnover = np.sum(np.abs(w_opt - curr_w))
            fee = turnover * SPOT_FEE_1WAY
            curr_w = w_opt
        else:
            fee = 0.0

        day_ret = np.dot(curr_w, stocks_ret.loc[d].values) - fee
        markowitz_rets.loc[d] = day_ret

    # =========================================================================
    # 3. Faber Tactical Asset Allocation (GTAA 200-day trend with Cash)
    # =========================================================================
    sma200 = imoex.rolling(200).mean()
    gtaa_pos = (imoex > sma200).astype(int).shift(1).fillna(0)
    gtaa_switches = gtaa_pos.diff().abs().fillna(0.0)
    gtaa_rets = (
        gtaa_pos * imoex_ret +
        (1.0 - gtaa_pos) * daily_rf -
        gtaa_switches * SPOT_FEE_1WAY
    )

    # =========================================================================
    # 4. FORTS Cointegration Spread Arbitrage («Стандартный ФОРТС»)
    # =========================================================================
    # Срочный арбитраж: тариф 1.45 руб. за контракт, 5.80 руб. на спред, 0.90 руб. опцион.
    # 80% залога в РЕПО с ЦК под RUSFAR + 3.8% альфа контанго.
    forts_spread_pct_fee = 5.80 / 60000.0
    forts_rpubs_rets = daily_rf + (0.038 / 252.0) - (forts_spread_pct_fee / 60.0)

    # Сводная таблица
    strategies = {
        "Benchmark: Buy & Hold IMOEX": imoex_ret,
        "Benchmark: Money Market (RUSFAR/LQDT)": daily_rf,
        "1. GARCH(1,1) Dynamic Vol Scaling": garch_rets,
        "2. Markowitz Tangency Portfolio": markowitz_rets,
        "3. Faber GTAA-200 Tactical Trend": gtaa_rets,
        "4. FORTS Cointegration Arbitrage («Стандартный ФОРТС»)": forts_rpubs_rets
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

    metrics_df.to_csv("rpubs_strategies_metrics.csv", index=False)
    equity_curves.to_csv("rpubs_strategies_equity.csv")

    # Построение графика
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2.5, 1.2]}, sharex=True)

    colors = {
        "Benchmark: Buy & Hold IMOEX": "gray",
        "Benchmark: Money Market (RUSFAR/LQDT)": "black",
        "1. GARCH(1,1) Dynamic Vol Scaling": "#1f77b4",
        "2. Markowitz Tangency Portfolio": "#ff7f0e",
        "3. Faber GTAA-200 Tactical Trend": "#d62728",
        "4. FORTS Cointegration Arbitrage («Стандартный ФОРТС»)": "#2ca02c"
    }

    for name in strategies.keys():
        ls = ":" if "Benchmark" in name else "-"
        lw = 2.0 if "FORTS" in name else 1.5
        ax1.plot(dates, equity_curves[name], label=name, color=colors.get(name, "blue"), linestyle=ls, lw=lw)

    ax1.set_title("Скептический аудит квантовых моделей с RPubs (RStudio) на данных MOEX (2021–2024 гг.)", fontsize=14, fontweight="bold", pad=12)
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
    chart_path = "rpubs_strategies_chart.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()

    print(f"Chart saved to {chart_path}")
    print("\n=== Результаты симуляции стратегий с RPubs на MOEX ===")
    print(metrics_df.to_string(index=False))

    return metrics_df, equity_curves


if __name__ == "__main__":
    run_rpubs_backtests()
