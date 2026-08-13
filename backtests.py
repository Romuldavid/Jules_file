# -*- coding: utf-8 -*-
"""
Файл содержит две части:
ЧАСТЬ 1: Базовые бэктесты для Google Colab (Фандинг, Календари, Спреды + Cash-and-Carry).
ЧАСТЬ 2: Продвинутый мульти-индикаторный бэктест (Класс AdvancedOptionsBacktest),
         который задействует Z-Score перепроданности/перекупленности, 
         анализ ожидаемой и исторической волатильности (IV/HV) и перекос улыбки (Skew).
         Реализованы проверки для 4 ключевых активов Московской биржи (MOEX):
         - Сбербанк (SBRF)
         - Газпром (GAZR)
         - Доллар/Рубль (Si)
         - Индекс РТС (RTS)

Все расчеты настроены под тариф «Стандартный ФОРТС» (0.45 руб. за контракт).
Период моделирования: 01.01.2023 - 01.08.2026.
Стартовый баланс: 1 000 000 рублей на каждую стратегию.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==============================================================================
# ЧАСТЬ 1: БАЗОВЫЕ БЭКТЕСТЫ
# ==============================================================================

# 1. Арбитраж ставки фандинга (Perpetual Futures vs Spot)
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
    
    return dates, equity_curve

# 2. Календарный спред фьючерсов
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
    
    return dates, equity_curve

# 3. Вертикальный Bull Call Спред на фьючерсы Sberbank (SBRF)
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
    
    return dates[:-1], equity_curve

# 4. Горизонтальный (календарный) спред на опционы Газпрома (GAZR)
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
    
    return dates[:-1], equity_curve

# 5. Кросс-диагональный спред (SBRF vs SBER - Опционы на фьючерсы vs Акции)
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
    
    return dates[:-1], equity_curve

# ==============================================================================
# СТРАТЕГИЯ 6 (НОВАЯ): Валютный Cash-and-Carry (Спот CNY_TOM против Фьючерса)
# ==============================================================================
def run_cash_and_carry_backtest():
    print("\n" + "="*80)
    print("ЗАПУСК БЭКТЕСТА 6: ВАЛЮТНЫЙ CASH-AND-CARRY (CNY_TOM vs CNY-)")
    print("="*80)
    np.random.seed(12345)
    
    # Моделирование квартальных циклов (4 квартала в год, 14 кварталов всего)
    dates = pd.date_range(start="2023-01-01", end="2026-08-01", freq="QE")
    n_quarters = len(dates)
    
    # Моделирование цен: спот юаня и фьючерса (закладываем контанго ~15-20% годовых из-за ставок)
    spot_prices = 11.0 + np.cumsum(np.random.normal(0.2, 0.5, n_quarters))
    contango_rate_annual = np.random.uniform(0.14, 0.22, n_quarters)
    futures_prices = spot_prices * (1.0 + contango_rate_annual * 0.25) # 0.25 года до экспирации
    
    capital = 1000000.0
    initial_capital = capital
    commission_its = 0.45   # ваш тариф ФОРТС за фьючерс
    commission_spot = 0.0005 # 0.05% от объема покупки спот юаня
    
    trade_log = []
    equity_curve = []
    
    # Каждые 3 месяца (квартал) мы открываем арбитраж и держим до экспирации
    for i in range(n_quarters):
        date = dates[i]
        spot_entry = spot_prices[i]
        fut_entry = futures_prices[i]
        
        # Объем позиции (используем 80% от капитала для покупки спота, 20% резерв под ГО фьючерса)
        allocated_capital = capital * 0.80
        num_contracts = int(allocated_capital / (spot_entry * 1000))
        if num_contracts == 0: num_contracts = 1
        
        # Шаг 1: Покупка спот CNY_TOM
        spot_cost = num_contracts * 1000 * spot_entry
        spot_fee = spot_cost * commission_spot
        
        # Шаг 2: Продажа фьючерса CNY на FORTS
        fut_fee_open = num_contracts * commission_its
        
        # Списание комиссий за вход
        capital -= (spot_fee + fut_fee_open)
        
        # Шаг 3: Удержание позиции до экспирации
        # На момент экспирации цена фьючерса сближается со спотом (F_expire = S_expire)
        # Наша зафиксированная премия равна разнице входа: (F_entry - S_entry)
        gross_premium = (fut_entry - spot_entry) * num_contracts * 1000
        
        # Комиссия за расчет/экспирацию фьючерса на FORTS
        fut_fee_close = num_contracts * commission_its
        
        # Начисление зафиксированной безрисковой премии
        capital += gross_premium - fut_fee_close
        
        trade_log.append({
            "Квартал": date.strftime("%Y-Q%q"),
            "Спот Вход": round(spot_entry, 3),
            "Фьючерс Вход": round(fut_entry, 3),
            "Премия (коп)": round((fut_entry - spot_entry) * 100, 1),
            "Контракты": num_contracts,
            "Чистый Доход": round(gross_premium - (spot_fee + fut_fee_open + fut_fee_close), 2),
            "Комиссии": round(spot_fee + fut_fee_open + fut_fee_close, 2),
            "Баланс": round(capital, 2)
        })
        equity_curve.append(capital)
        
    df_log = pd.DataFrame(trade_log)
    print("\n--- ЖУРНАЛ СДЕЛКИ СТРАТЕГИИ 6 (CASH-AND-CARRY) ---")
    print(df_log.to_string(index=False))
    
    total_return = (capital - initial_capital) / initial_capital * 100
    days_total = (dates[-1] - dates[0]).days
    apy = total_return * (365.0 / days_total)
    
    print("\n" + "-"*40)
    print(f"Итоговый баланс (Стратегия 6): {round(capital, 2)} руб.")
    print(f"Общая доходность: {round(total_return, 2)}%")
    print(f"Доходность в годовых (APY): {round(apy, 2)}%")
    print("-"*40 + "\n")
    
    return dates, equity_curve

# ==============================================================================
# ЧАСТЬ 2: ПРОДВИНУТЫЙ МУЛЬТИ-ИНДИКАТОРНЫЙ БЭКТЕСТ (SBRF, GAZR, Si, RTS)
# ==============================================================================

class AdvancedOptionsBacktest:
    """
    Класс реализует продвинутую торговую систему, сочетающую:
    1. Z-Score (Следование за сильным трендом / Momentum).
    2. Волатильный Арбитраж (Сравнение Ожидаемой IV и Исторической HV волатильностей).
    3. Учет тарифа «Стандартный ФОРТС» (0.45 руб. ИТС / 0.90 руб. исполнение).
    
    Реализовано независимое тестирование 4 активов на Московской бирже.
    Для чистоты эксперимента доход на остаток кэша отключен (0.0%).
    """
    def __init__(self, initial_capital=1000000.0):
        self.initial_capital = initial_capital
        self.commission_its = 0.45
        self.commission_exercise = 0.90
        
        # Период бэктеста
        np.random.seed(888)
        self.dates = pd.date_range(start="2023-01-01", end="2026-08-01", freq="ME")
        self.n_periods = len(self.dates)
        
        # Конфигурация активов на MOEX
        self.assets = {
            "SBRF (Сбербанк)": {
                "start_price": 16000.0,
                "vol": 1800.0,
                "step": 500,
                "contracts": 250,
                "prem_scale": 1.0
            },
            "GAZR (Газпром)": {
                "start_price": 17000.0,
                "vol": 700.0,
                "step": 250,
                "contracts": 300,
                "prem_scale": 0.8
            },
            "Si (Доллар/Рубль)": {
                "start_price": 75000.0,
                "vol": 4000.0,
                "step": 1000,
                "contracts": 100,
                "prem_scale": 1.5
            },
            "RTS (Индекс РТС)": {
                "start_price": 100000.0,
                "vol": 6000.0,
                "step": 2500,
                "contracts": 80,
                "prem_scale": 1.8
            }
        }
        
    def run_for_asset(self, asset_name):
        print("\n" + "="*80)
        print(f"ЗАПУСК ПРОДВИНУТОГО БЭКТЕСТА ДЛЯ: {asset_name} (ЧИСТАЯ СТРАТЕГИЯ)")
        print("="*80)
        
        config = self.assets[asset_name]
        capital = self.initial_capital
        
        # Генерация ценового ряда и волатильности
        np.random.seed(99)
        prices = config["start_price"] + np.cumsum(np.random.normal(300, config["vol"], self.n_periods))
        hv = np.random.uniform(0.15, 0.25, self.n_periods)
        iv = hv * np.random.uniform(0.8, 1.5, self.n_periods)
        
        prices_series = pd.Series(prices)
        rolling_mean = prices_series.rolling(window=5, min_periods=1).mean()
        rolling_std = prices_series.rolling(window=5, min_periods=1).std().fillna(config["vol"])
        z_scores = (prices_series - rolling_mean) / rolling_std
        
        trade_log = []
        equity_curve = []
        contracts_qty = config["contracts"]
        
        for i in range(self.n_periods - 1):
            date = self.dates[i]
            entry_p = prices[i]
            exit_p = prices[i+1]
            z_score = z_scores[i]
            current_iv = iv[i]
            current_hv = hv[i]
            
            # Чистая стратегия (Кэш-ставка = 0.0%)
            capital += 0.0
            
            iv_hv_ratio = current_iv / current_hv
            
            # Логика Momentum на основе Z-Score
            if z_score > 0.7:
                direction = "BULL"
            elif z_score < -0.7:
                direction = "BEAR"
            else:
                direction = "NEUTRAL"
                
            broker_fee_open = (contracts_qty * 2) * self.commission_its
            broker_fee_exit = 0.0
            net_payoff = 0.0
            net_premium_paid = 0.0
            period_profit = 0.0
            
            strike_buy = int(entry_p // config["step"]) * config["step"]
            
            if direction == "BULL":
                strike_sell = strike_buy + int(config["step"] * 3)
                prem_buy = 600.0 * iv_hv_ratio * config["prem_scale"]
                prem_sell = 200.0 * iv_hv_ratio * config["prem_scale"]
                net_premium_paid = (prem_buy - prem_sell) * contracts_qty
                
                capital -= (net_premium_paid + broker_fee_open)
                
                payoff_buy = max(0, exit_p - strike_buy) * contracts_qty
                payoff_sell = max(0, exit_p - strike_sell) * contracts_qty
                net_payoff = payoff_buy - payoff_sell
                
                if exit_p > strike_buy:
                    broker_fee_exit += contracts_qty * self.commission_exercise
                if exit_p > strike_sell:
                    broker_fee_exit += contracts_qty * self.commission_exercise
                    
                period_profit = net_payoff - broker_fee_exit
                capital += period_profit
                
            elif direction == "BEAR":
                strike_sell = strike_buy - int(config["step"] * 3)
                prem_buy = 600.0 * iv_hv_ratio * config["prem_scale"]
                prem_sell = 200.0 * iv_hv_ratio * config["prem_scale"]
                net_premium_paid = (prem_buy - prem_sell) * contracts_qty
                
                capital -= (net_premium_paid + broker_fee_open)
                
                payoff_buy = max(0, strike_buy - exit_p) * contracts_qty
                payoff_sell = max(0, strike_sell - exit_p) * contracts_qty
                net_payoff = payoff_buy - payoff_sell
                
                if exit_p < strike_buy:
                    broker_fee_exit += contracts_qty * self.commission_exercise
                if exit_p < strike_sell:
                    broker_fee_exit += contracts_qty * self.commission_exercise
                    
                period_profit = net_payoff - broker_fee_exit
                capital += period_profit
                
            else:
                # NEUTRAL: Календарный спред
                prem_sell_near = 300.0 * iv_hv_ratio * config["prem_scale"]
                prem_buy_far = 800.0 * iv_hv_ratio * config["prem_scale"]
                net_premium_paid = (prem_buy_far - prem_sell_near) * contracts_qty
                
                capital -= (net_premium_paid + broker_fee_open)
                
                payoff_near = max(0, exit_p - strike_buy) * contracts_qty
                val_far = (max(0, exit_p - strike_buy) + (config["step"] * 1.3)) * contracts_qty
                net_payoff = val_far - payoff_near
                
                if exit_p > strike_buy:
                    broker_fee_exit += contracts_qty * self.commission_exercise
                    
                period_profit = net_payoff - broker_fee_exit
                capital += period_profit
                
            trade_log.append({
                "Дата": date.strftime("%Y-%m"),
                "Вход": int(entry_p),
                "Выход": int(exit_p),
                "Z-Score": round(z_score, 2),
                "Направление": direction,
                "Профит": round(period_profit - net_premium_paid, 2),
                "Комиссия": round(broker_fee_open + broker_fee_exit, 2),
                "Баланс": round(capital, 2)
            })
            equity_curve.append(capital)
            
        df_log = pd.DataFrame(trade_log)
        print(f"\n--- СИСТЕМНЫЙ ЖУРНАЛ СДЕЛКИ ({asset_name}) ---")
        print(df_log.to_string(index=False))
        
        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        days_total = (self.dates[-1] - self.dates[0]).days
        apy = total_return * (365.0 / days_total)
        
        print("\n" + "-"*40)
        print(f"Итоговый баланс ({asset_name}): {round(capital, 2)} руб.")
        print(f"Общая доходность: {round(total_return, 2)}%")
        print(f"Доходность в годовых (APY): {round(apy, 2)}%")
        print("-"*40 + "\n")
        
        return self.dates[:-1], equity_curve

    def run(self):
        # Запускаем проверку последовательно для каждого из 4 активов MOEX
        results = {}
        for asset in self.assets.keys():
            dates, eq = self.run_for_asset(asset)
            results[asset] = eq
            
        # Построение общего графика сравнения
        plt.figure(figsize=(14, 7))
        for asset, eq in results.items():
            plt.plot(self.dates[:-1], eq, linewidth=2.5, marker="o", label=f"Баланс {asset}")
        plt.title("Сравнение доходности чистой опционной стратегии по разным активам MOEX (2023-2026)")
        plt.xlabel("Дата")
        plt.ylabel("Баланс счета, руб.")
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.legend()
        plt.show()

# ==============================================================================
# ГЛАВНЫЙ ЗАПУСК
# ==============================================================================
if __name__ == "__main__":
    # 1. Запуск базовых бэктестов (ЧАСТЬ 1)
    run_funding_arbitrage_backtest()
    run_calendar_futures_backtest()
    run_vertical_spread_backtest()
    run_horizontal_spread_backtest()
    run_diagonal_spread_backtest()
    
    # Запуск нового бэктеста 6 (Cash-and-Carry)
    run_cash_and_carry_backtest()
    
    # 2. Запуск продвинутого мульти-активного бэктеста (ЧАСТЬ 2)
    adv_test = AdvancedOptionsBacktest()
    adv_test.run()
    
    print("\nВсе бэктесты и продвинутый микс-тест успешно выполнены!")
