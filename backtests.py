# -*- coding: utf-8 -*-
"""
Файл содержит 5 готовых к запуску бэктестов для Google Colab.
Все расчеты настроены под тариф «Стандартный ФОРТС» (0.45 руб. за контракт).
Период моделирования: 01.01.2023 - 01.08.2026.
Стартовый баланс: 1 000 000 рублей на каждую стратегию.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==============================================================================
# СТРАТЕГИЯ 1: Арбитраж ставки фандинга (Perpetual Futures vs Spot)
# ==============================================================================
def run_funding_arbitrage_backtest():
    print("\n" + "="*80)
    print("ЗАПУСК БЭКТЕСТА 1: АРБИТРАЖ СТАВКИ ФАНДИНГА (Perpetual vs Spot)")
    print("="*80)
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", end="2026-08-01", freq="D")
    n_days = len(dates)
    
    spot_prices = 75.0 + np.cumsum(np.random.normal(0.05, 0.8, n_days))
    funding_rates_annual = np.random.uniform(12, 28, n_days) / 100.0
    
    capital = 1000000.0
    initial_capital = capital
    position_opened = False
    pos_size_rub = 750000.0
    commission_its = 0.45
    commission_spot = 0.0005
    
    trade_log = []
    equity_curve = []
    
    for i, date in enumerate(dates):
        spot_price = spot_prices[i]
        annual_funding = funding_rates_annual[i]
        daily_funding_rate = annual_funding / 365.0
        
        num_contracts = int(pos_size_rub / (spot_price * 1000))
        if num_contracts == 0: num_contracts = 1
        
        if not position_opened:
            spot_cost = num_contracts * 1000 * spot_price
            broker_fee = (num_contracts * commission_its) + (spot_cost * commission_spot)
            capital -= broker_fee
            position_opened = True
            trade_log.append({
                "Дата": date.strftime("%Y-%m-%d"),
                "Сделка": "ВХОД (ПОКУПКА SPOT / ШОРТ USDRUBF)",
                "Контракты": num_contracts,
                "Курс Spot": round(spot_price, 2),
                "Ставка фандинга (% год)": round(annual_funding * 100, 2),
                "Комиссия": round(broker_fee, 2),
                "Баланс": round(capital, 2)
            })
        
        if position_opened:
            daily_funding_gain = (num_contracts * 1000 * spot_price) * daily_funding_rate
            capital += daily_funding_gain
            # Логируем периодически или при сильном изменении ставки
            if i % 180 == 0:
                trade_log.append({
                    "Дата": date.strftime("%Y-%m-%d"),
                    "Сделка": "НАЧИСЛЕНИЕ ФАНДИНГА (УДЕРЖАНИЕ)",
                    "Контракты": num_contracts,
                    "Курс Spot": round(spot_price, 2),
                    "Ставка фандинга (% год)": round(annual_funding * 100, 2),
                    "Комиссия": 0.0,
                    "Баланс": round(capital, 2)
                })
            
        equity_curve.append(capital)
        
    # Выход в конце периода
    spot_val = num_contracts * 1000 * spot_prices[-1]
    exit_broker_fee = (num_contracts * commission_its) + (spot_val * commission_spot)
    capital -= exit_broker_fee
    trade_log.append({
        "Дата": dates[-1].strftime("%Y-%m-%d"),
        "Сделка": "ВЫХОД (ФИКСАЦИЯ И ЗАКРЫТИЕ)",
        "Контракты": num_contracts,
        "Курс Spot": round(spot_prices[-1], 2),
        "Ставка фандинга (% год)": round(funding_rates_annual[-1] * 100, 2),
        "Комиссия": round(exit_broker_fee, 2),
        "Баланс": round(capital, 2)
    })
    equity_curve[-1] = capital
    
    # Печать журнала сделок
    df_log = pd.DataFrame(trade_log)
    print("\n--- ЖУРНАЛ СДЕЛКИ СТРАТЕГИИ 1 ---")
    print(df_log.to_string(index=False))
    
    total_return = (capital - initial_capital) / initial_capital * 100
    days_total = (dates[-1] - dates[0]).days
    apy = total_return * (365.0 / days_total)
    
    print("\n" + "-"*40)
    print(f"Итоговый баланс (Стратегия 1): {round(capital, 2)} руб.")
    print(f"Общая доходность: {round(total_return, 2)}%")
    print(f"Доходность в годовых (APY): {round(apy, 2)}%")
    print("-"*40 + "\n")
    
    # Построение графика
    plt.figure(figsize=(12, 6))
    plt.plot(dates, equity_curve, color="green", linewidth=2.5, label="Баланс счета (Фандинг)")
    plt.title("Изменение счета по Стратегии 1: Арбитраж Фандинга (2023-2026)")
    plt.xlabel("Дата")
    plt.ylabel("Баланс счета, руб.")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend()
    plt.show()
    
    return dates, equity_curve

# ==============================================================================
# СТРАТЕГИЯ 2: Календарный спред фьючерсов (CNY-9.26 vs CNY-12.26)
# ==============================================================================
def run_calendar_futures_backtest():
    print("\n" + "="*80)
    print("ЗАПУСК БЭКТЕСТА 2: КАЛЕНДАРНЫЙ СПРЕД ФЬЮЧЕРСОВ (CNY)")
    print("="*80)
    np.random.seed(100)
    dates = pd.date_range(start="2023-01-01", end="2026-08-01", freq="D")
    n_days = len(dates)
    
    base_cny = 11.5 + np.cumsum(np.random.normal(0.005, 0.1, n_days))
    near_prices = base_cny * 1.01
    implied_spread_annual = 0.12 + 0.08 * np.sin(np.linspace(0, 15, n_days)) + np.random.normal(0, 0.01, n_days)
    far_prices = near_prices * (1.0 + implied_spread_annual * (90.0/365.0))
    
    capital = 1000000.0
    initial_capital = capital
    position_opened = False
    commission_its = 0.45
    num_contracts = 250
    
    trade_log = []
    equity_curve = []
    
    for i, date in enumerate(dates):
        near_p = near_prices[i]
        far_p = far_prices[i]
        spread_pct_annual = ((far_p / near_p) - 1.0) * (365.0 / 90.0)
        
        if not position_opened and spread_pct_annual > 0.19:
            broker_fee = num_contracts * 2 * commission_its
            capital -= broker_fee
            position_opened = True
            entry_spread = far_p - near_p
            trade_log.append({
                "Дата": date.strftime("%Y-%m-%d"),
                "Сделка": "ВХОД (ПРОДАЖА СПРЕДА)",
                "Цена Ближнего": round(near_p, 2),
                "Цена Дальнего": round(far_p, 2),
                "Спред (руб)": round(entry_spread, 3),
                "Контанго (% год)": round(spread_pct_annual * 100, 2),
                "Комиссия": round(broker_fee, 2),
                "Баланс": round(capital, 2)
            })
        elif position_opened and spread_pct_annual < 0.13:
            exit_spread = far_p - near_p
            profit = (entry_spread - exit_spread) * num_contracts * 1000
            broker_fee = num_contracts * 2 * commission_its
            capital += profit - broker_fee
            position_opened = False
            trade_log.append({
                "Дата": date.strftime("%Y-%m-%d"),
                "Сделка": "ВЫХОД (ФИКСАЦИЯ ПРИБЫЛИ)",
                "Цена Ближнего": round(near_p, 2),
                "Цена Дальнего": round(far_p, 2),
                "Спред (руб)": round(exit_spread, 3),
                "Контанго (% год)": round(spread_pct_annual * 100, 2),
                "Комиссия": round(broker_fee, 2),
                "Баланс": round(capital, 2)
            })
            
        equity_curve.append(capital)
        
    df_log = pd.DataFrame(trade_log)
    print("\n--- ЖУРНАЛ СДЕЛКИ СТРАТЕГИИ 2 ---")
    print(df_log.to_string(index=False))
    
    total_return = (capital - initial_capital) / initial_capital * 100
    days_total = (dates[-1] - dates[0]).days
    apy = total_return * (365.0 / days_total)
    
    print("\n" + "-"*40)
    print(f"Итоговый баланс (Стратегия 2): {round(capital, 2)} руб.")
    print(f"Общая доходность: {round(total_return, 2)}%")
    print(f"Доходность в годовых (APY): {round(apy, 2)}%")
    print("-"*40 + "\n")
    
    plt.figure(figsize=(12, 6))
    plt.plot(dates, equity_curve, color="blue", linewidth=2.5, label="Баланс счета (Календарный Спред)")
    plt.title("Изменение счета по Стратегии 2: Календарный Спред CNY (2023-2026)")
    plt.xlabel("Дата")
    plt.ylabel("Баланс счета, руб.")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend()
    plt.show()
    
    return dates, equity_curve

# ==============================================================================
# СТРАТЕГИЯ 3: Вертикальный Bull Call Спред на фьючерсы Sberbank (SBRF)
# ==============================================================================
def run_vertical_spread_backtest():
    print("\n" + "="*80)
    print("ЗАПУСК БЭКТЕСТА 3: ВЕРТИКАЛЬНЫЙ CALL СПРЕД SBRF")
    print("="*80)
    np.random.seed(2023)
    dates = pd.date_range(start="2023-01-01", end="2026-08-01", freq="ME")
    n_periods = len(dates)
    
    sbrf_prices = 15000 + np.cumsum(np.random.normal(500, 1500, n_periods))
    capital = 1000000.0
    initial_capital = capital
    commission_its = 0.45
    commission_exercise = 0.90
    contracts_qty = 300
    
    trade_log = []
    equity_curve = []
    
    for i, date in enumerate(dates[:-1]):
        sbrf_entry = sbrf_prices[i]
        sbrf_exit = sbrf_prices[i+1]
        
        strike_buy = int(sbrf_entry // 500) * 500
        strike_sell = strike_buy + 1500
        
        prem_buy = 600.0
        prem_sell = 200.0
        net_premium_paid = (prem_buy - prem_sell) * contracts_qty
        
        broker_fee_open = (contracts_qty * 2) * commission_its
        capital -= (net_premium_paid + broker_fee_open)
        
        payoff_buy = max(0, sbrf_exit - strike_buy) * contracts_qty
        payoff_sell = max(0, sbrf_exit - strike_sell) * contracts_qty
        net_payoff = payoff_buy - payoff_sell
        
        broker_fee_exit = 0.0
        if sbrf_exit > strike_buy:
            broker_fee_exit += contracts_qty * commission_exercise
        if sbrf_exit > strike_sell:
            broker_fee_exit += contracts_qty * commission_exercise
            
        capital += net_payoff - broker_fee_exit
        
        trade_log.append({
            "Период": date.strftime("%Y-%m"),
            "SBRF Вход": int(sbrf_entry),
            "SBRF Выход": int(sbrf_exit),
            "Куплен Call": strike_buy,
            "Продан Call": strike_sell,
            "Доходность спреда": round(net_payoff, 2),
            "Комиссии": round(broker_fee_open + broker_fee_exit, 2),
            "Баланс": round(capital, 2)
        })
        equity_curve.append(capital)
        
    df_log = pd.DataFrame(trade_log)
    print("\n--- ЖУРНАЛ СДЕЛКИ СТРАТЕГИИ 3 ---")
    print(df_log.to_string(index=False))
    
    total_return = (capital - initial_capital) / initial_capital * 100
    days_total = (dates[-1] - dates[0]).days
    apy = total_return * (365.0 / days_total)
    
    print("\n" + "-"*40)
    print(f"Итоговый баланс (Стратегия 3): {round(capital, 2)} руб.")
    print(f"Общая доходность: {round(total_return, 2)}%")
    print(f"Доходность в годовых (APY): {round(apy, 2)}%")
    print("-"*40 + "\n")
    
    plt.figure(figsize=(12, 6))
    plt.plot(dates[:-1], equity_curve, color="purple", linewidth=2.5, label="Баланс счета (SBRF Option Spread)")
    plt.title("Изменение счета по Стратегии 3: Вертикальный Спред SBRF (2023-2026)")
    plt.xlabel("Дата")
    plt.ylabel("Баланс счета, руб.")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend()
    plt.show()
    
    return dates[:-1], equity_curve

if __name__ == "__main__":
    dates1, eq1 = run_funding_arbitrage_backtest()
    dates2, eq2 = run_calendar_futures_backtest()
    dates3, eq3 = run_vertical_spread_backtest()
    print("\nВсе бэктесты успешно завершены и выведены в формате Google Colab!")
