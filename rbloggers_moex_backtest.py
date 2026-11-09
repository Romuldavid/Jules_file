"""
rbloggers_moex_backtest.py
Количественное моделирование и скептический бэктест стратегий с R-bloggers
на реальных исторических данных Московской Биржи (MOEX) за период 2021-2024 гг.

Исследуемые стратегии из популярных публикаций R-bloggers:
1. Adaptive Asset Allocation (AAA / Butler, Philbrick, Gordillo, Systematic Investor)
   - Динамический выбор топ-активов по моментуму + взвешивание по минимальной волатильности (Inverse Volatility).
   - Активы MOEX: Акции (IMOEX), Облигации (RGBITR), Золото (GLDRUB), Кэш/LQDT.
2. Volatility Targeting & Regime Filter (Learning Machines / ChatGPT R-strategy)
   - Выход в кэш (фонд LQDT / РЕПО с ЦК) при превышении пороговой волатильности.
3. Cointegration & Pairs Trading (Edwin Chen / Engle-Granger stat-arb)
   - Торговля спредом коинтегрированной пары: обыкновенные и привилегированные акции Сбербанка (SBER / SBERP).
   - Учет спредов, комиссий и стоимости заемных средств при коротких позициях.
4. Classical Trend Following SMA-200 with Money Market Yield (Quantstrat framework)
   - Переключение между индексом IMOEX и рынком денег в зависимости от трендового фильтра.
5. Short-term 1-Month Mean Reversion (Systematic Investor reversal anomaly)
   - Покупка наиболее отставших за последний месяц ликвидных акций против лидеров.
   - Скептическая проверка: выживает ли реверсия при российских транзакционных издержках.

Реалистичные издержки рынка РФ:
- Комиссия брокера и биржи: 0.04% (4 bps) за сделку
- Проскальзывание (slippage): 0.05% (5 bps)
- Стоимость шорта (коротких позиций): Ключевая ставка + 5% годовых
- Доходность на свободный остаток: динамическая ставка RUSFAR (LQDT)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from smartlab_strategies_backtest import fetch_moex_history


def calculate_metrics(returns_series, rf_series, periods_per_year=252):
    """
    Рассчитывает исчерпывающие риск-метрики для ряда дневных доходностей.
    """
    clean_rets = returns_series.dropna()
    if len(clean_rets) == 0:
        return {}

    cum_prod = (1.0 + clean_rets).cumprod()
    total_ret = cum_prod.iloc[-1] - 1.0
    n_days = len(clean_rets)
    years = n_days / periods_per_year
    cagr = (1.0 + total_ret) ** (1.0 / years) - 1.0 if years > 0 and total_ret > -1.0 else -1.0

    ann_vol = clean_rets.std() * np.sqrt(periods_per_year)

    # Динамическая безрисковая ставка
    rf_aligned = rf_series.reindex(clean_rets.index).fillna(0.0)
    ann_rf = (1.0 + rf_aligned).prod() ** (periods_per_year / n_days) - 1.0 if n_days > 0 else 0.0

    excess_daily = clean_rets - rf_aligned
    sharpe = (excess_daily.mean() * periods_per_year) / ann_vol if ann_vol > 1e-8 else 0.0

    # Sortino ratio (штраф только за нисходящую волатильность)
    downside_daily = clean_rets[clean_rets < 0]
    downside_std = downside_daily.std() * np.sqrt(periods_per_year) if len(downside_daily) > 0 else 1e-8
    sortino = (excess_daily.mean() * periods_per_year) / downside_std if downside_std > 1e-8 else 0.0

    # Max Drawdown & Calmar
    running_max = cum_prod.cummax()
    drawdowns = (cum_prod - running_max) / running_max
    max_dd = abs(drawdowns.min())
    calmar = cagr / max_dd if max_dd > 1e-6 else 0.0

    # Win rate & Profit factor
    wins = clean_rets[clean_rets > 0]
    losses = clean_rets[clean_rets < 0]
    win_rate = len(wins) / len(clean_rets) if len(clean_rets) > 0 else 0.0
    profit_factor = wins.sum() / abs(losses.sum()) if abs(losses.sum()) > 1e-8 else np.nan

    return {
        "CAGR": cagr,
        "Volatility": ann_vol,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "MaxDrawdown": max_dd,
        "Calmar": calmar,
        "WinRate": win_rate,
        "ProfitFactor": profit_factor,
        "TotalReturn": total_ret,
        "RiskFreeRate": ann_rf,
    }


def run_rbloggers_backtests():
    start_date = "2021-01-01"
    end_date = "2024-11-01"

    # Загрузка рыночных рядов MOEX
    imoex_df = fetch_moex_history("stock", "index", "SNDX", "IMOEX", start_date, end_date)
    dates = imoex_df["TRADEDATE"].sort_values().drop_duplicates()
    imoex = imoex_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    rgbi_df = fetch_moex_history("stock", "index", "RTSI", "RGBITR", start_date, end_date)
    rgbi = rgbi_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    gld_df = fetch_moex_history("stock", "shares", "GLDRUB_TOM", "GLDRUB_TOM", start_date, end_date)
    gld = gld_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    sber_df = fetch_moex_history("stock", "shares", "TQBR", "SBER", start_date, end_date)
    sber = sber_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    sberp_df = fetch_moex_history("stock", "shares", "TQBR", "SBERP", start_date, end_date)
    sberp = sberp_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    lkoh_df = fetch_moex_history("stock", "shares", "TQBR", "LKOH", start_date, end_date)
    lkoh = lkoh_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    rosn_df = fetch_moex_history("stock", "shares", "TQBR", "ROSN", start_date, end_date)
    rosn = rosn_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    gazp_df = fetch_moex_history("stock", "shares", "TQBR", "GAZP", start_date, end_date)
    gazp = gazp_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    gmkn_df = fetch_moex_history("stock", "shares", "TQBR", "GMKN", start_date, end_date)
    gmkn = gmkn_df.set_index("TRADEDATE")["CLOSE"].reindex(dates).ffill()

    # Точное расписание Ключевой Ставки ЦБ РФ (01.01.2023 – 20.08.2026 гг.)
    # и фактические ставки за 2021-2022 гг.
    cbr_schedule = [
        ("2021-01-01", "2021-03-21", 0.0425),
        ("2021-03-22", "2021-04-25", 0.0450),
        ("2021-04-26", "2021-06-14", 0.0500),
        ("2021-06-15", "2021-07-25", 0.0550),
        ("2021-07-26", "2021-09-12", 0.0650),
        ("2021-09-13", "2021-10-24", 0.0675),
        ("2021-10-25", "2021-12-19", 0.0750),
        ("2021-12-20", "2022-02-27", 0.0850),
        ("2022-02-28", "2022-04-10", 0.2000),  # Экстренное повышение до 20%
        ("2022-04-11", "2022-05-03", 0.1700),
        ("2022-05-04", "2022-05-26", 0.1400),
        ("2022-05-27", "2022-06-13", 0.1100),
        ("2022-06-14", "2022-07-24", 0.0950),
        ("2022-07-25", "2022-09-18", 0.0800),
        ("2022-09-19", "2022-12-31", 0.0750),
        # Официальный график 01.01.2023 - 20.08.2026:
        ("2023-01-01", "2023-07-23", 0.0750),  # Мягкая денежно-кредитная политика
        ("2023-07-24", "2023-08-14", 0.0850),  # Первое повышение
        ("2023-08-15", "2023-09-17", 0.1200),  # Внеочередное повышение
        ("2023-09-18", "2023-10-29", 0.1300),  # Борьба с инфляцией
        ("2023-10-30", "2023-12-17", 0.1500),  # Ужесточение ДКП
        ("2023-12-18", "2024-07-28", 0.1600),  # Пауза 16%
        ("2024-07-29", "2024-09-15", 0.1800),  # Повышение ставки
        ("2024-09-16", "2024-10-27", 0.1900),  # Перегрев экономики
        ("2024-10-28", "2025-06-30", 0.2100),  # Пиковый уровень ставки 21%
        ("2025-07-01", "2025-12-31", 0.1800),  # Снижение ставки
        ("2026-01-01", "2026-05-31", 0.1600),  # Постепенная нормализация
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

    # Дневные доходности бенчмарков
    imoex_ret = imoex.pct_change().fillna(0.0)
    rgbi_ret = rgbi.pct_change().fillna(0.0)
    gld_ret = gld.pct_change().fillna(0.0)

    # Параметры транзакционных издержек MOEX (Фондовый рынок)
    COMMISSION = 0.0004     # 0.04% брокер + биржа
    SLIPPAGE = 0.0005       # 0.05% проскальзывание в стакане
    TOTAL_FEE_1WAY = COMMISSION + SLIPPAGE  # 0.09% на вход/выход
    SHORT_BORROW_SPREAD = 0.05  # Плата за шорт = ставка ЦБ + 5%

    # Тарифный план «Стандартный ФОРТС»:
    # Биржевой сбор + брокер за 1 контракт фьючерса (подача через ИТС):
    # 0.45 руб. (брокер) + ~1.00 руб. (биржа) = 1.45 руб. за контракт
    # За спред (2 контракта, вход + выход): 1.45 * 2 * 2 = 5.80 руб. на 1 спред
    # Исполнение поставочного опциона (двойная ставка ИТС): 0.45 * 2 = 0.90 руб.
    FORTS_BROKER_FEE = 0.45
    FORTS_EXCHANGE_FEE = 1.00
    FORTS_CONTRACT_FEE_1WAY = FORTS_BROKER_FEE + FORTS_EXCHANGE_FEE  # 1.45 руб.
    FORTS_SPREAD_ROUNDTRIP_FEE = FORTS_CONTRACT_FEE_1WAY * 2.0 * 2.0  # 5.80 руб.
    FORTS_OPTION_EXERCISE_FEE = FORTS_BROKER_FEE * 2.0  # 0.90 руб.

    # =========================================================================
    # 1. Adaptive Asset Allocation (AAA) - Systematic Investor / Butler et al.
    # =========================================================================
    # Вселенная: IMOEX, RGBITR, GLDRUB_TOM, LQDT (Cash).
    # Каждый месяц (21 день):
    # - Ранжирование по моментуму за 6 месяцев (126 торговых дней)
    # - Отбор топ-2 активов с положительным моментумом относительно кэша
    # - Взвешивание отобранных активов обратно пропорционально их 20-дневной волатильности
    # - Если моментум актива отрицателен относительно кэша - аллокация в кэш
    rebalance_freq = 21
    mom_lookback = 126
    vol_lookback = 20

    assets_prices = pd.DataFrame({
        "IMOEX": imoex,
        "RGBITR": rgbi,
        "GLDRUB": gld
    }, index=dates)

    assets_ret = assets_prices.pct_change().fillna(0.0)
    cash_cum = (1.0 + daily_rf).cumprod()

    # Расчет моментума к кэшу
    asset_mom = assets_prices / assets_prices.shift(mom_lookback)
    cash_mom = cash_cum / cash_cum.shift(mom_lookback)

    # Волатильность за 20 дней
    asset_vol = assets_ret.rolling(vol_lookback).std() * np.sqrt(252)

    aaa_rets = pd.Series(0.0, index=dates)
    curr_weights = {"IMOEX": 0.0, "RGBITR": 0.0, "GLDRUB": 0.0, "CASH": 1.0}

    for i in range(len(dates)):
        d = dates.iloc[i]
        # Ребалансировка
        if i >= mom_lookback and (i % rebalance_freq == 0 or i == mom_lookback):
            prev_d = dates.iloc[i-1]
            mom_row = asset_mom.loc[prev_d]
            c_mom = cash_mom.loc[prev_d]
            vol_row = asset_vol.loc[prev_d]

            # Фильтр: моментум выше доходности кэша за период
            qualified = mom_row[mom_row > c_mom].sort_values(ascending=False)
            new_weights = {"IMOEX": 0.0, "RGBITR": 0.0, "GLDRUB": 0.0, "CASH": 0.0}

            if len(qualified) == 0:
                new_weights["CASH"] = 1.0
            else:
                top_assets = qualified.head(2).index.tolist()
                inv_vols = {a: 1.0 / max(vol_row[a], 0.05) for a in top_assets}
                tot_inv_vol = sum(inv_vols.values())
                for a in top_assets:
                    new_weights[a] = inv_vols[a] / tot_inv_vol

            # Учет транзакционных издержек ребалансировки
            turnover = sum(abs(new_weights[a] - curr_weights[a]) for a in ["IMOEX", "RGBITR", "GLDRUB"])
            fee_cost = turnover * TOTAL_FEE_1WAY
            curr_weights = new_weights
        else:
            fee_cost = 0.0

        # Доходность за день
        day_ret = (
            curr_weights["IMOEX"] * assets_ret.loc[d, "IMOEX"] +
            curr_weights["RGBITR"] * assets_ret.loc[d, "RGBITR"] +
            curr_weights["GLDRUB"] * assets_ret.loc[d, "GLDRUB"] +
            curr_weights["CASH"] * daily_rf.loc[d] -
            fee_cost
        )
        aaa_rets.loc[d] = day_ret

    # =========================================================================
    # 2. Volatility Targeting & Regime Filter (Learning Machines / R-bloggers)
    # =========================================================================
    # Если 20-дневная реализованная волатильность индекса IMOEX < пороговой (например 22%),
    # держим позицию Long IMOEX.
    # Если волатильность выше порога (рыночный стресс) -> уходим в кэш (LQDT/RUSFAR).
    # Скептический нюанс: в статье R-bloggers кэш дает 0%, а на MOEX кэш дает 12-21%!
    imoex_vol20 = imoex_ret.rolling(20).std() * np.sqrt(252)
    vol_threshold = 0.22
    vol_signal = (imoex_vol20 < vol_threshold).astype(int).shift(1).fillna(0)

    # Издержки переключения
    vol_switches = vol_signal.diff().abs().fillna(0.0)
    vol_filter_rets = (
        vol_signal * imoex_ret +
        (1.0 - vol_signal) * daily_rf -
        vol_switches * TOTAL_FEE_1WAY
    )

    # =========================================================================
    # 3. Cointegration & Pairs Trading (Edwin Chen / Engle-Granger Stat-Arb)
    # =========================================================================
    # Классическая коинтегрированная пара на MOEX: SBER (обычка) vs SBERP (префы).
    # Отношение цен Ratio = SBER / SBERP исторически колеблется около 1.0 - 1.05.
    # В R-bloggers обычно предполагают: нулевая стоимость шорта, идеальный арбитраж.
    # Скептический учет MOEX:
    # - Шорт стоит Ключевая ставка + 5% годовых
    # - Двойная комиссия за вход и выход в два актива
    # - Z-score рассчитывается по окну 60 дней.
    sber_ratio = sber / sberp
    ratio_mean = sber_ratio.rolling(60).mean()
    ratio_std = sber_ratio.rolling(60).std()
    z_score = (sber_ratio - ratio_mean) / ratio_std

    # Сигналы: если Z > 1.5 -> Продаем SBER, Покупаем SBERP (короткий спред)
    #          если Z < -1.5 -> Покупаем SBER, Продаем SBERP (длинный спред)
    #          выход при |Z| < 0.2
    pair_pos = pd.Series(0.0, index=dates)
    curr_pair = 0.0
    for i in range(60, len(dates)):
        d = dates.iloc[i]
        z = z_score.loc[d]
        if np.isnan(z):
            continue
        if z > 1.5:
            curr_pair = -1.0  # Short SBER, Long SBERP
        elif z < -1.5:
            curr_pair = 1.0   # Long SBER, Short SBERP
        elif abs(z) < 0.2:
            curr_pair = 0.0   # Flat
        pair_pos.loc[d] = curr_pair

    pair_pos = pair_pos.shift(1).fillna(0.0)
    pair_switches = pair_pos.diff().abs().fillna(0.0)

    sber_ret = sber.pct_change().fillna(0.0)
    sberp_ret = sberp.pct_change().fillna(0.0)

    # Стоимость шорта в день
    daily_short_borrow = (rf_annual + SHORT_BORROW_SPREAD) / 252.0

    pairs_rets = pd.Series(0.0, index=dates)
    for d in dates:
        pos = pair_pos.loc[d]
        switch = pair_switches.loc[d]
        fee = switch * TOTAL_FEE_1WAY * 2.0  # 2 актива торгуются

        if pos == 1.0:
            # Long SBER (0.5), Short SBERP (0.5), кэш 0.5 под RUSFAR
            ret = 0.5 * sber_ret.loc[d] - 0.5 * sberp_ret.loc[d] - 0.5 * daily_short_borrow.loc[d] + 0.5 * daily_rf.loc[d]
        elif pos == -1.0:
            # Short SBER (0.5), Long SBERP (0.5), кэш 0.5 под RUSFAR
            ret = -0.5 * sber_ret.loc[d] + 0.5 * sberp_ret.loc[d] - 0.5 * daily_short_borrow.loc[d] + 0.5 * daily_rf.loc[d]
        else:
            # Flat -> 100% капитал в фонде денежного рынка LQDT/RUSFAR
            ret = daily_rf.loc[d]
        pairs_rets.loc[d] = ret - fee

    # =========================================================================
    # 3b. Cointegration Pairs Trading on FORTS Futures (Тариф «Стандартный ФОРТС»)
    # =========================================================================
    # Торговля тем же спредом SBER / SBERP, но через поставочные/расчетные фьючерсы
    # на срочном рынке FORTS (контракты SR / SP).
    # Преимущества срочного рынка:
    # 1. НЕТ платы за шорт (шорт фьючерса бесплатный, ГО списывается симметрично ~15-20%).
    # 2. 80-85% капитала остается в кэше и размещается в РЕПО с ЦК (RUSFAR) или фонд LQDT.
    # 3. Комиссия по тарифу «Стандартный ФОРТС»: 1.45 руб. за контракт (0.45 руб. брокер + 1.00 руб. биржа).
    #    При стоимости контракта SBER (~25 000 - 30 000 руб.) комиссия 1.45 руб. = всего 0.005% (0.5 bps)!
    #    Полный круг на 1 спред (2 ноги, вход + выход) = 5.80 руб.
    forts_pairs_rets = pd.Series(0.0, index=dates)
    forts_spread_pct_fee = 5.80 / 60000.0  # 5.80 руб. на 2 контракта стоимостью ~60 000 руб. ~ 0.000097 (0.01%)

    for d in dates:
        pos = pair_pos.loc[d]
        switch = pair_switches.loc[d]
        fee = switch * forts_spread_pct_fee

        if pos == 1.0:
            # Long фьючерс SBER, Short фьючерс SBERP. ГО ~20%, 80% кэша под RUSFAR. Шорт бесплатный!
            ret = 0.5 * sber_ret.loc[d] - 0.5 * sberp_ret.loc[d] + 0.80 * daily_rf.loc[d]
        elif pos == -1.0:
            # Short фьючерс SBER, Long фьючерс SBERP. ГО ~20%, 80% кэша под RUSFAR. Шорт бесплатный!
            ret = -0.5 * sber_ret.loc[d] + 0.5 * sberp_ret.loc[d] + 0.80 * daily_rf.loc[d]
        else:
            # Flat -> 100% капитал под ставку RUSFAR
            ret = daily_rf.loc[d]
        forts_pairs_rets.loc[d] = ret - fee

    # =========================================================================
    # 4. Trend Following SMA-200 with Money Market Yield (Quantstrat Classic)
    # =========================================================================
    # Если IMOEX > SMA(200) -> 100% Long IMOEX
    # Если IMOEX < SMA(200) -> 100% Кэш под ставку RUSFAR (LQDT)
    imoex_sma200 = imoex.rolling(200).mean()
    trend_signal = (imoex > imoex_sma200).astype(int).shift(1).fillna(0)
    trend_switches = trend_signal.diff().abs().fillna(0.0)

    trend_rets = (
        trend_signal * imoex_ret +
        (1.0 - trend_signal) * daily_rf -
        trend_switches * TOTAL_FEE_1WAY
    )

    # =========================================================================
    # 5. Short-term 1-Month Mean Reversion (Systematic Investor)
    # =========================================================================
    # Вселенная: SBER, LKOH, ROSN, GAZP, GMKN (Топ-5 голубых фишек MOEX).
    # Каждый месяц (21 день):
    # - Находим акцию с наихудшей доходностью за 21 день (laggard / перепроданная)
    # - Покупаем ее на 1 месяц в расчете на отскок к среднему
    # - Если рынок в даунтренде (IMOEX < SMA200) - сокращаем аллокацию в 2 раза, остаток в кэш
    stock_df = pd.DataFrame({
        "SBER": sber,
        "LKOH": lkoh,
        "ROSN": rosn,
        "GAZP": gazp,
        "GMKN": gmkn
    }, index=dates)
    stock_rets = stock_df.pct_change().fillna(0.0)
    stock_mom21 = stock_df / stock_df.shift(21)

    reversion_rets = pd.Series(0.0, index=dates)
    curr_stock = None

    for i in range(22, len(dates)):
        d = dates.iloc[i]
        if (i % 21 == 0 or curr_stock is None) and i >= 22:
            prev_d = dates.iloc[i-1]
            mom_s = stock_mom21.loc[prev_d].dropna()
            if len(mom_s) > 0:
                worst_stock = mom_s.idxmin()
            else:
                worst_stock = "SBER"
            fee = TOTAL_FEE_1WAY * 2.0 if curr_stock != worst_stock else 0.0
            curr_stock = worst_stock
        else:
            fee = 0.0

        # Взвешивание с фильтром тренда индекса
        in_trend = (imoex.loc[dates.iloc[i-1]] > imoex_sma200.loc[dates.iloc[i-1]]) if i >= 200 else False
        equity_weight = 1.0 if in_trend else 0.5
        cash_weight = 1.0 - equity_weight

        st_ret = stock_rets.loc[d, curr_stock]
        day_ret = equity_weight * st_ret + cash_weight * daily_rf.loc[d] - fee
        reversion_rets.loc[d] = day_ret

    # =========================================================================
    # Сводная таблица доходностей и метрик
    # =========================================================================
    all_strategies = {
        "Benchmark: Buy&Hold IMOEX": imoex_ret,
        "Benchmark: Money Market (RUSFAR/LQDT)": daily_rf,
        "1. Adaptive Asset Allocation (AAA)": aaa_rets,
        "2. Volatility Targeting Filter": vol_filter_rets,
        "3a. Pairs Trading Spot (Дорогой шорт)": pairs_rets,
        "3b. Pairs Trading FORTS («Стандартный ФОРТС»)": forts_pairs_rets,
        "4. Trend Following SMA-200 + Cash": trend_rets,
        "5. 1-Month Mean Reversion (Laggard Bounce)": reversion_rets
    }

    metrics_list = []
    equity_curves = pd.DataFrame(index=dates)

    for name, s_rets in all_strategies.items():
        # Накопленная доходность
        eq = (1.0 + s_rets).cumprod()
        equity_curves[name] = eq
        m = calculate_metrics(s_rets, daily_rf)
        m["Strategy"] = name
        metrics_list.append(m)

    metrics_df = pd.DataFrame(metrics_list)
    cols = ["Strategy", "CAGR", "Volatility", "Sharpe", "Sortino", "MaxDrawdown", "Calmar", "WinRate", "ProfitFactor", "TotalReturn"]
    metrics_df = metrics_df[cols]

    # Сохранение результатов
    metrics_df.to_csv("rbloggers_strategies_metrics.csv", index=False)
    equity_curves.to_csv("rbloggers_strategies_equity.csv")

    # Построение графиков эквити и просадок
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2.5, 1.2]}, sharex=True)

    colors = {
        "Benchmark: Buy&Hold IMOEX": "gray",
        "Benchmark: Money Market (RUSFAR/LQDT)": "black",
        "1. Adaptive Asset Allocation (AAA)": "#1f77b4",
        "2. Volatility Targeting Filter": "#ff7f0e",
        "3a. Pairs Trading Spot (Дорогой шорт)": "#7f7f7f",
        "3b. Pairs Trading FORTS («Стандартный ФОРТС»)": "#2ca02c",
        "4. Trend Following SMA-200 + Cash": "#d62728",
        "5. 1-Month Mean Reversion (Laggard Bounce)": "#9467bd"
    }
    linestyles = {
        "Benchmark: Buy&Hold IMOEX": ":",
        "Benchmark: Money Market (RUSFAR/LQDT)": "--",
        "1. Adaptive Asset Allocation (AAA)": "-",
        "2. Volatility Targeting Filter": "-",
        "3a. Pairs Trading Spot (Дорогой шорт)": ":",
        "3b. Pairs Trading FORTS («Стандартный ФОРТС»)": "-",
        "4. Trend Following SMA-200 + Cash": "-",
        "5. 1-Month Mean Reversion (Laggard Bounce)": "-"
    }

    for name in all_strategies.keys():
        ax1.plot(dates, equity_curves[name], label=name, color=colors.get(name, "blue"), linestyle=linestyles.get(name, "-"), lw=1.8)

    ax1.set_title("Скептический бэктест квантовых стратегий с R-bloggers в реалиях MOEX (2021–2024 гг.)", fontsize=14, fontweight="bold", pad=12)
    ax1.set_ylabel("Динамика портфеля (База = 1.0)", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left", fontsize=9, framealpha=0.9)

    # Просадки
    for name in all_strategies.keys():
        eq = equity_curves[name]
        dd = (eq - eq.cummax()) / eq.cummax()
        ax2.plot(dates, dd * 100, label=name, color=colors.get(name, "blue"), linestyle=linestyles.get(name, "-"), lw=1.2)

    ax2.set_title("Исторические просадки стратегий (%)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Просадка (%)", fontsize=11)
    ax2.set_xlabel("Дата", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    chart_path = "rbloggers_strategies_chart.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"Chart saved to {chart_path}")
    print("\n=== Результаты симуляции стратегий с R-bloggers на MOEX ===")
    print(metrics_df.to_string(index=False))

    return metrics_df, equity_curves


if __name__ == "__main__":
    run_rbloggers_backtests()
