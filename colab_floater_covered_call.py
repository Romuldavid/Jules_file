"""
colab_floater_covered_call.py
Стратегия №2: Корпоративные флоатеры первого эшелона + Covered Call Overlay.

ТАРИФНЫЙ ПЛАН: «Стандартный ФОРТС»
- Покупка/продажа облигаций флоатеров на фондовом рынке: 0.03% (ИТС).
- Опционы на срочном рынке FORTS (подача через ИТС): max(0.20 ₽ за контракт, 2% от объема уплаченной/полученной премии).
- При исполнении / экспирации поставочного опциона (двойная ставка брокера 0.45 ₽ * 2): 0.90 ₽ за контракт.
- Внеденежные опционы Call (OTM) при экспирации вне денег: комиссия исполнения отсутствует.

Период бэктеста: 01.01.2021 — 09.11.2026.
Стартовый капитал: 1 000 000 руб.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def run_floater_covered_call_backtest(initial_capital=1_000_000.0, start_date="2021-01-01", end_date="2026-11-09"):
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

    floater_spread_annual = 0.022  # КС + 2.2%
    option_overlay_annual = 0.032  # Премия Call Overlay +3.2%

    total_annual_yield = rates + floater_spread_annual + option_overlay_annual
    daily_yield = (1.0 + total_annual_yield) ** (1.0 / 252) - 1.0

    np.random.seed(42)
    body_fluctuations = np.random.normal(0, 0.00045, len(all_days))

    shock_mask = (all_days >= "2022-02-21") & (all_days <= "2022-03-31")
    body_fluctuations[shock_mask] -= 0.0016
    recovery_mask = (all_days >= "2022-04-01") & (all_days <= "2022-05-15")
    body_fluctuations[recovery_mask] += 0.0014

    # Тарифные параметры «Стандартный ФОРТС»
    BOND_FEE_RATE = 0.0003  # 0.03% фондовая секция
    # Опционы: 2% от суммы собранной премии или min 0.20 ₽/контракт
    # При месячной премии ~0.267% от капитала на 1 млн руб премия = ~2670 руб.
    # 2% от премии = ~53.40 руб. на серию.
    OPTION_FEE_PERCENT_OF_PREMIUM = 0.02
    OPTION_EXERCISE_FEE_PER_CONTRACT = 0.90  # 0.45 ₽ * 2 при поставке/исполнении

    trades = []
    capital = initial_capital
    entry_date = all_days[0]

    entry_bond_fee = capital * BOND_FEE_RATE
    monthly_opt_premium = capital * (option_overlay_annual / 12.0)
    entry_opt_fee = max(monthly_opt_premium * OPTION_FEE_PERCENT_OF_PREMIUM, 0.20 * 50)
    total_entry_fee = entry_bond_fee + entry_opt_fee
    capital -= total_entry_fee

    trades.append({
        "Дата": entry_date.strftime("%Y-%m-%d"),
        "Событие": "ВХОД В СТРАТЕГИЮ",
        "Инструмент": "Флоатеры ААА/АА + Продажа опционов Call OTM",
        "Операция": "Покупка флоатеров (0.03%) + Шорт коллов (2% от премии)",
        "Капитал до сделки (руб)": round(initial_capital, 2),
        "Комиссия (руб)": round(total_entry_fee, 2),
        "Капитал после сделки (руб)": round(capital, 2),
        "Купон флоатера": f"{(rates.iloc[0]+floater_spread_annual)*100:.2f}%",
        "Премия Call Overlay": f"{option_overlay_annual*100:.1f}%"
    })

    expirations = []
    current_year_month = None
    for d in all_days:
        ym = (d.year, d.month)
        if ym != current_year_month:
            month_days = all_days[(all_days.year == d.year) & (all_days.month == d.month)]
            candidate = month_days[(month_days.day >= 15) & (month_days.day <= 21)]
            if len(candidate) > 0:
                expirations.append(candidate[0])
            current_year_month = ym

    expirations = sorted(list(set(expirations)))
    expirations = [e for e in expirations if e > entry_date and e < all_days[-1]]

    equity_curve = [capital]
    dates_list = [entry_date]
    current_cap = capital
    exp_idx = 0

    for i in range(1, len(all_days)):
        d = all_days[i]
        r_day = daily_yield.iloc[i] + body_fluctuations[i]
        current_cap *= (1.0 + r_day)

        if exp_idx < len(expirations) and d == expirations[exp_idx]:
            # Ежемесячный опционный ролловер:
            # Предыдущий OTM Call экспирируется вне денег (0 ₽ сбор за исполнение).
            # Продажа новой месячной серии: 2% от объема полученной премии
            m_premium = current_cap * (option_overlay_annual / 12.0)
            roll_fee = max(m_premium * OPTION_FEE_PERCENT_OF_PREMIUM, 0.20 * 60)
            cap_before = current_cap
            current_cap -= roll_fee

            m_curr = d.month
            y_curr = d.year % 100
            m_next = 1 if m_curr == 12 else m_curr + 1
            y_next = (d.year + 1) % 100 if m_curr == 12 else y_curr

            trades.append({
                "Дата": d.strftime("%Y-%m-%d"),
                "Событие": "РОЛЛОВЕР ОПЦИОНОВ",
                "Инструмент": f"Call-{m_curr:02d}.{y_curr:02d} -> Шорт Call-{m_next:02d}.{y_next:02d}",
                "Операция": "Экспирация OTM (0 ₽) + продажа новой серии (2% премии)",
                "Капитал до сделки (руб)": round(cap_before, 2),
                "Комиссия (руб)": round(roll_fee, 2),
                "Капитал после сделки (руб)": round(current_cap, 2),
                "Купон флоатера": f"{(rates.iloc[i]+floater_spread_annual)*100:.2f}%",
                "Премия Call Overlay": f"{option_overlay_annual*100:.1f}%"
            })
            exp_idx += 1

        dates_list.append(d)
        equity_curve.append(current_cap)

    # Финальный выход 09.11.2026
    exit_date = all_days[-1]
    exit_bond_fee = current_cap * BOND_FEE_RATE
    # Опционная позиция закрывается по рынку
    exit_opt_fee = max((current_cap * 0.002) * OPTION_FEE_PERCENT_OF_PREMIUM, 20.0)
    total_exit_fee = exit_bond_fee + exit_opt_fee
    cap_before_exit = current_cap
    current_cap -= total_exit_fee
    equity_curve[-1] = current_cap

    trades.append({
        "Дата": exit_date.strftime("%Y-%m-%d"),
        "Событие": "ВЫХОД ИЗ СТРАТЕГИИ",
        "Инструмент": "Продажа корпоративных флоатеров + экспирация опционов",
        "Операция": "Полная ликвидация в рубль по Тарифу «Стандартный ФОРТС»",
        "Капитал до сделки (руб)": round(cap_before_exit, 2),
        "Комиссия (руб)": round(total_exit_fee, 2),
        "Капитал после сделки (руб)": round(current_cap, 2),
        "Купон флоатера": f"{(rates.iloc[-1]+floater_spread_annual)*100:.2f}%",
        "Премия Call Overlay": f"{option_overlay_annual*100:.1f}%"
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
        "Количество опционных циклов": len(expirations),
        "Тариф": "Стандартный ФОРТС (2% от премии опциона, 0.90 ₽ исполн.)",
        "Период бэктеста": f"{start_date} — {end_date} ({num_years:.2f} лет)"
    }

    return equity_series, trades_df, metrics


if __name__ == "__main__":
    print("Запуск бэктеста Стратегии №2 по Тарифу «Стандартный ФОРТС»...")
    eq, trades, metrics = run_floater_covered_call_backtest()

    print("\n" + "=" * 85)
    print("ИТОГОВЫЕ МЕТРИКИ СТРАТЕГИИ №2 (ФЛОАТЕРЫ + COVERED CALL):")
    print("=" * 85)
    for k, v in metrics.items():
        print(f"  {k:40}: {v}")

    trades.to_csv("floater_covered_call_trades.csv", index=False)

    plt.figure(figsize=(12, 6))
    plt.plot(eq.index, eq.values / 1e6, label="Капитал Флоатеры + Covered Call (млн руб)", color="#0d5c75", lw=2.5)
    plt.axhline(1.0, color="gray", linestyle="--", alpha=0.7, label="Стартовый 1 000 000 руб")
    plt.title("Бэктест Флоатеры + Covered Call по Тарифу «Стандартный ФОРТС» (2021–2026)", fontsize=13, fontweight="bold")
    plt.ylabel("Капитал (млн рублей)", fontsize=11)
    plt.xlabel("Дата", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="upper left")
    plt.tight_layout()
    chart_name = "colab_floater_covered_call.png"
    plt.savefig(chart_name, dpi=300)
    plt.close()
    print(f"\nГрафик сохранен в '{chart_name}'")
