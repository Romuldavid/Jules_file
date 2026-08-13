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
            # Логируем периодически
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
    
    plt.figure(figsize=(10, 5))
    plt.plot(dates, equity_curve, color="green", linewidth=2.5, label="Баланс счета (Фандинг)")
    plt.title("Изменение счета по Стратегии 1: Арбитраж Фандинга")
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
    
    plt.figure(figsize=(10, 5))
    plt.plot(dates, equity_curve, color="blue", linewidth=2.5, label="Баланс счета (Календарный Спред)")
    plt.title("Изменение счета по Стратегии 2: Календарный Спред CNY")
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
    
    plt.figure(figsize=(10, 5))
    plt.plot(dates[:-1], equity_curve, color="purple", linewidth=2.5, label="Баланс счета (SBRF Option Spread)")
    plt.title("Изменение счета по Стратегии 3: Вертикальный Спред SBRF")
    plt.xlabel("Дата")
    plt.ylabel("Баланс счета, руб.")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend()
    plt.show()
    
    return dates[:-1], equity_curve

# ==============================================================================
# СТРАТЕГИЯ 4: Горизонтальный (календарный) спред на опционы Газпрома (GAZR)
# ==============================================================================
def run_horizontal_spread_backtest():
    print("\n" + "="*80)
    print("ЗАПУСК БЭКТЕСТА 4: ГОРИЗОНТАЛЬНЫЙ (КАЛЕНДАРНЫЙ) СПРЕД GAZR")
    print("="*80)
    np.random.seed(123)
    dates = pd.date_range(start="2023-01-01", end="2026-08-01", freq="ME")
    n_periods = len(dates)
    
    gazr_prices = 16500 + np.cumsum(np.random.normal(0, 800, n_periods))
    capital = 1000000.0
    initial_capital = capital
    commission_its = 0.45
    commission_exercise = 0.90
    contracts_qty = 150
    
    trade_log = []
    equity_curve = []
    
    for i, date in enumerate(dates[:-1]):
        gazr_entry = gazr_prices[i]
        gazr_exit = gazr_prices[i+1]
        
        strike = int(gazr_entry // 500) * 500
        
        prem_near_sell = 300.0
        prem_far_buy = 800.0
        net_cost = (prem_far_buy - prem_near_sell) * contracts_qty
        
        broker_fee_open = (contracts_qty * 2) * commission_its
        capital -= (net_cost + broker_fee_open)
        
        payoff_near_sell = max(0, gazr_exit - strike) * contracts_qty
        val_far_buy = (max(0, gazr_exit - strike) + 250.0) * contracts_qty
        
        profit = val_far_buy - payoff_near_sell
        capital += profit
        
        broker_fee_exit = 0.0
        if gazr_exit > strike:
            broker_fee_exit += contracts_qty * commission_exercise
            
        capital -= broker_fee_exit
        
        trade_log.append({
            "Период": date.strftime("%Y-%m"),
            "GAZR Вход": int(gazr_entry),
            "GAZR Выход": int(gazr_exit),
            "Страйк": strike,
            "Доходность спреда": round(profit - net_cost, 2),
            "Комиссии": round(broker_fee_open + broker_fee_exit, 2),
            "Баланс": round(capital, 2)
        })
        equity_curve.append(capital)
        
    df_log = pd.DataFrame(trade_log)
    print("\n--- ЖУРНАЛ СДЕЛКИ СТРАТЕГИИ 4 ---")
    print(df_log.to_string(index=False))
    
    total_return = (capital - initial_capital) / initial_capital * 100
    days_total = (dates[-1] - dates[0]).days
    apy = total_return * (365.0 / days_total)
    
    print("\n" + "-"*40)
    print(f"Итоговый баланс (Стратегия 4): {round(capital, 2)} руб.")
    print(f"Общая доходность: {round(total_return, 2)}%")
    print(f"Доходность в годовых (APY): {round(apy, 2)}%")
    print("-"*40 + "\n")
    
    plt.figure(figsize=(10, 5))
    plt.plot(dates[:-1], equity_curve, color="darkblue", linewidth=2.5, label="Баланс счета (GAZR Horizontal)")
    plt.title("Изменение счета по Стратегии 4: Горизонтальный Спред GAZR")
    plt.xlabel("Дата")
    plt.ylabel("Баланс счета, руб.")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend()
    plt.show()
    
    return dates[:-1], equity_curve

# ==============================================================================
# СТРАТЕГИЯ 5: Кросс-диагональный спред (SBRF vs SBER - Опционы на фьючерсы vs Акции)
# ==============================================================================
def run_diagonal_spread_backtest():
    print("\n" + "="*80)
    print("ЗАПУСК БЭКТЕСТА 5: КРОСС-ДИАГОНАЛЬНЫЙ СПРЕД SBER")
    print("="*80)
    np.random.seed(999)
    dates = pd.date_range(start="2023-01-01", end="2026-08-01", freq="ME")
    n_periods = len(dates)
    
    sber_prices = 150.0 + np.cumsum(np.random.normal(3.5, 10.0, n_periods))
    capital = 1000000.0
    initial_capital = capital
    commission_its_fut = 0.45
    
    trade_log = []
    equity_curve = []
    
    fut_opt_qty = 50
    prem_opt_qty = 500
    
    for i, date in enumerate(dates[:-1]):
        sber_entry = sber_prices[i]
        sber_exit = sber_prices[i+1]
        
        strike_fut_sell = int(sber_entry)
        strike_prem_buy = int(sber_entry + 15)
        
        prem_fut_opt = 800.0
        prem_stock_opt = 30.0
        
        total_prem_paid = prem_stock_opt * prem_opt_qty
        broker_fee_stock_opt = max(0.20 * prem_opt_qty, total_prem_paid * 0.02)
        
        broker_fee_open = (fut_opt_qty * commission_its_fut) + broker_fee_stock_opt
        
        net_inflow = (fut_opt_qty * prem_fut_opt) - total_prem_paid
        capital += net_inflow - broker_fee_open
        
        payoff_fut_sell = max(0, (sber_exit - strike_fut_sell) * 100) * fut_opt_qty
        payoff_prem_buy = max(0, (sber_exit - strike_prem_buy) * 10) * prem_opt_qty
        
        net_payoff = payoff_prem_buy - payoff_fut_sell
        capital += net_payoff
        
        trade_log.append({
            "Период": date.strftime("%Y-%m"),
            "SBER Вход": round(sber_entry, 2),
            "SBER Выход": round(sber_exit, 2),
            "Чистый Доход": round(net_payoff + net_inflow, 2),
            "Комиссии": round(broker_fee_open, 2),
            "Баланс": round(capital, 2)
        })
        equity_curve.append(capital)
        
    df_log = pd.DataFrame(trade_log)
    print("\n--- ЖУРНАЛ СДЕЛКИ СТРАТЕГИИ 5 ---")
    print(df_log.to_string(index=False))
    
    total_return = (capital - initial_capital) / initial_capital * 100
    days_total = (dates[-1] - dates[0]).days
    apy = total_return * (365.0 / days_total)
    
    print("\n" + "-"*40)
    print(f"Итоговый баланс (Стратегия 5): {round(capital, 2)} руб.")
    print(f"Общая доходность: {round(total_return, 2)}%")
    print(f"Доходность в годовых (APY): {round(apy, 2)}%")
    print("-"*40 + "\n")
    
    plt.figure(figsize=(10, 5))
    plt.plot(dates[:-1], equity_curve, color="purple", linewidth=2.5, label="Баланс счета (SBER Diagonal)")
    plt.title("Изменение счета по Стратегии 5: Кросс-Диагональный Спред SBER")
    plt.xlabel("Дата")
    plt.ylabel("Баланс счета, руб.")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend()
    plt.show()
    
    return dates[:-1], equity_curve

# ==============================================================================
# ГЛАВНЫЙ ЗАПУСК ВСЕХ 5 СТРАТЕГИЙ
# ==============================================================================
if __name__ == "__main__":
    dates1, eq1 = run_funding_arbitrage_backtest()
    dates2, eq2 = run_calendar_futures_backtest()
    dates3, eq3 = run_vertical_spread_backtest()
    dates4, eq4 = run_horizontal_spread_backtest()
    dates5, eq5 = run_diagonal_spread_backtest()
    print("\nВсе 5 бэктестов успешно завершены и выведены в формате Google Colab!")
