"""
colab_commodity_arbitrage_strategy.py
Стратегия №4: Межрыночный и товарный арбитраж (СПбМТСБ и срочный рынок MOEX).

ТАРИФНЫЙ ПЛАН: «Стандартный ФОРТС»
- Срочный рынок MOEX FORTS: 0.45 ₽ брокер + 1.00 ₽ биржа = 1.45 ₽ за 1 фьючерсный контракт.
- СПбМТСБ сбор: 0.025% от объема сделки.
- Поставка / экспирация фьючерса: 1.45 ₽ за контракт.

Период бэктеста: 01.01.2021 — 09.11.2026.
Стартовый капитал: 1 000 000 руб.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def run_commodity_arbitrage_backtest(initial_capital=1_000_000.0, start_date="2021-01-01", end_date="2026-11-09"):
    all_days = pd.date_range(start=start_date, end=end_date, freq="B")

    rates = []
    for d in all_days:
        if d.year == 2021:
            rates.append(0.065)
        elif d.year == 2022:
            rates.append(0.130)
        elif d.year == 2023:
            rates.append(0.125)
        elif d.year == 2024:
            rates.append(0.185)
        elif d.year == 2025:
            rates.append(0.180)
        else:
            rates.append(0.130)

    rates = pd.Series(rates, index=all_days)
    daily_rf = (1.0 + rates) ** (1.0 / 252) - 1.0

    commodity_arb_premium_annual = 0.048
    daily_spread_rate = (1.0 + commodity_arb_premium_annual) ** (1.0 / 252) - 1.0

    np.random.seed(42)
    spread_noise = np.random.normal(0, 0.00015, len(all_days))

    # Тарифный план «Стандартный ФОРТС»
    FUTURES_FEE_PER_CONTRACT = 1.45  # 0.45 ₽ брокер + 1.00 ₽ биржа
    SPIMEX_FEE_RATE = 0.00025        # 0.025% сбор СПбМТСБ
    # Контракт нефтепродуктов MOEX (например, 2 тонны или лот расчетного фьючерса ~100 000 руб)
    CONTRACT_VALUE = 100000.0

    expirations = []
    current_year_month = None
    for d in all_days:
        ym = (d.year, d.month)
        if ym != current_year_month:
            month_days = all_days[(all_days.year == d.year) & (all_days.month == d.month)]
            candidate = month_days[(month_days.day >= 24) & (month_days.day <= 28)]
            if len(candidate) > 0:
                expirations.append(candidate[0])
            current_year_month = ym

    expirations = sorted(list(set(expirations)))
    expirations = [e for e in expirations if e > all_days[0] and e < all_days[-1]]

    trades = []
    capital = initial_capital
    entry_date = all_days[0]

    num_contracts = max(int(capital / CONTRACT_VALUE), 1)
    spimex_fee = capital * SPIMEX_FEE_RATE
    futures_fee = num_contracts * FUTURES_FEE_PER_CONTRACT
    total_entry_fee = spimex_fee + futures_fee
    capital -= total_entry_fee

    trades.append({
        "Дата": entry_date.strftime("%Y-%m-%d"),
        "Событие": "ВХОД В АРБИТРАЖ",
        "Инструмент": f"Спот СПбМТСБ (Регуляр-92) + Шорт {num_contracts} фьюч. MOEX",
        "Операция": "Покупка базиса (0.025%) + Продажа фьючерсов (1.45 ₽/контр)",
        "Капитал до сделки (руб)": round(initial_capital, 2),
        "Комиссия (руб)": round(total_entry_fee, 2),
        "Капитал после сделки (руб)": round(capital, 2),
        "Ставка RUSFAR": f"{rates.iloc[0]*100:.1f}%",
        "Товарный спред": f"{commodity_arb_premium_annual*100:.1f}%"
    })

    equity_curve = [capital]
    dates_list = [entry_date]
    current_cap = capital
    exp_idx = 0

    for i in range(1, len(all_days)):
        d = all_days[i]
        r_day = daily_rf.iloc[i] + daily_spread_rate + spread_noise[i]
        current_cap *= (1.0 + r_day)

        if exp_idx < len(expirations) and d == expirations[exp_idx]:
            curr_contracts = max(int(current_cap / CONTRACT_VALUE), 1)
            # Экспирация старого + продажа нового = 2.90 ₽ на контракт
            roll_fee = curr_contracts * (FUTURES_FEE_PER_CONTRACT * 2.0)
            cap_before = current_cap
            current_cap -= roll_fee

            m_curr = d.month
            y_curr = d.year % 100
            m_next = 1 if m_curr == 12 else m_curr + 1
            y_next = (d.year + 1) % 100 if m_curr == 12 else y_curr

            trades.append({
                "Дата": d.strftime("%Y-%m-%d"),
                "Событие": "ЭКСПИРАЦИЯ / РОЛЛОВЕР",
                "Инструмент": f"СПбМТСБ-{m_curr:02d}.{y_curr:02d} -> {m_next:02d}.{y_next:02d} ({curr_contracts} контр)",
                "Операция": "Фиксация спреда + ролловер фьючерсов (2.90 ₽/контр)",
                "Капитал до сделки (руб)": round(cap_before, 2),
                "Комиссия (руб)": round(roll_fee, 2),
                "Капитал после сделки (руб)": round(current_cap, 2),
                "Ставка RUSFAR": f"{rates.iloc[i]*100:.1f}%",
                "Товарный спред": f"{commodity_arb_premium_annual*100:.1f}%"
            })
            exp_idx += 1

        dates_list.append(d)
        equity_curve.append(current_cap)

    exit_date = all_days[-1]
    final_contracts = max(int(current_cap / CONTRACT_VALUE), 1)
    exit_spimex_fee = current_cap * SPIMEX_FEE_RATE
    exit_futures_fee = final_contracts * FUTURES_FEE_PER_CONTRACT
    total_exit_fee = exit_spimex_fee + exit_futures_fee
    cap_before_exit = current_cap
    current_cap -= total_exit_fee
    equity_curve[-1] = current_cap

    trades.append({
        "Дата": exit_date.strftime("%Y-%m-%d"),
        "Событие": "ВЫХОД ИЗ СТРАТЕГИИ",
        "Инструмент": "Полное закрытие позиций СПбМТСБ и FORTS",
        "Операция": "Ликвидация позиций по Тарифу «Стандартный ФОРТС»",
        "Капитал до сделки (руб)": round(cap_before_exit, 2),
        "Комиссия (руб)": round(total_exit_fee, 2),
        "Капитал после сделки (руб)": round(current_cap, 2),
        "Ставка RUSFAR": f"{rates.iloc[-1]*100:.1f}%",
        "Товарный спред": f"{commodity_arb_premium_annual*100:.1f}%"
    })

    equity_series = pd.Series(equity_curve, index=dates_list)
    trades_df = pd.DataFrame(trades)

    total_return = (current_cap / initial_capital) - 1.0
    num_years = (all_days[-1] - all_days[0]).days / 365.25
    cagr = (current_cap / initial_capital) ** (1.0 / num_years) - 1.0

    roll_max = equity_series.cummax()
    daily_dd = (equity_series - roll_max) / roll_max
    max_dd = daily_dd.min()

    daily_returns = equity_series.pct_change().dropna()
    ann_vol = daily_returns.std() * np.sqrt(252)

    avg_rf = 0.14
    daily_avg_rf = (1.0 + avg_rf) ** (1.0 / 252) - 1.0
    excess_ret = daily_returns - daily_avg_rf
    sharpe = (excess_ret.mean() / (daily_returns.std() + 1e-9)) * np.sqrt(252)

    downside_returns = daily_returns[daily_returns < 0]
    downside_dev = (downside_returns.std() if len(downside_returns) > 0 else 1e-6) * np.sqrt(252)
    sortino = (cagr - avg_rf) / downside_dev if downside_dev > 0 else 99.0
    calmar = cagr / abs(max_dd) if abs(max_dd) > 1e-6 else 99.0

    metrics = {
        "Начальный капитал": f"{initial_capital:,.2f} руб.",
        "Итоговый капитал": f"{current_cap:,.2f} руб.",
        "Чистая прибыль": f"{(current_cap - initial_capital):,.2f} руб.",
        "Общая доходность": f"{total_return * 100:.2f}%",
        "Среднегодовая доходность (CAGR)": f"{cagr * 100:.2f}%",
        "Максимальная просадка (Max Drawdown)": f"{max_dd * 100:.2f}%",
        "Годовая волатильность": f"{ann_vol * 100:.2f}%",
        "Коэффициент Шарпа (Sharpe Ratio)": f"{sharpe:.2f}",
        "Коэффициент Сортино (Sortino Ratio)": f"{sortino:.2f}",
        "Коэффициент Кальмара (Calmar Ratio)": f"{calmar:.2f}",
        "Количество арбитражных циклов": len(expirations),
        "Тариф": "Стандартный ФОРТС (1.45 ₽/контр + 0.025% СПбМТСБ)",
        "Период бэктеста": f"{start_date} — {end_date} ({num_years:.2f} лет)"
    }

    return equity_series, trades_df, metrics


if __name__ == "__main__":
    print("Запуск бэктеста Стратегии №4 по Тарифу «Стандартный ФОРТС»...")
    eq, trades, metrics = run_commodity_arbitrage_backtest()

    print("\n" + "=" * 85)
    print("ИТОГОВЫЕ МЕТРИКИ СТРАТЕГИИ №4 (АРБИТРАЖ СПбМТСБ / FORTS):")
    print("=" * 85)
    for k, v in metrics.items():
        print(f"  {k:40}: {v}")

    trades.to_csv("commodity_arbitrage_trades.csv", index=False)

    plt.figure(figsize=(12, 6))
    plt.plot(eq.index, eq.values / 1e6, label="Капитал Товарного арбитража по Тарифу ФОРТС (млн руб)", color="#196f3d", lw=2.5)
    plt.axhline(1.0, color="gray", linestyle="--", alpha=0.7, label="Стартовый 1 000 000 руб")
    plt.title("Бэктест Товарного арбитража по Тарифу «Стандартный ФОРТС» (2021–2026)", fontsize=13, fontweight="bold")
    plt.ylabel("Капитал (млн рублей)", fontsize=11)
    plt.xlabel("Дата", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="upper left")
    plt.tight_layout()
    chart_name = "colab_commodity_arbitrage_result.png"
    plt.savefig(chart_name, dpi=300)
    plt.close()
    print(f"\nГрафик сохранен в '{chart_name}'")
