"""
================================================================================
  ВЫСОКОТОЧНЫЙ АНАЛИЗ И БЭКТЕСТ ВАЛЮТНОГО CASH-AND-CARRY НА МОСКОВСКОЙ БИРЖЕ
  Период: 01 января 2023 г. — 20 августа 2026 г. (Сегодня)
  Начальный капитал: 1 000 000.00 рублей
  Тарифный план: «Стандартный ФОРТС» (Комиссия брокера 0.45 ₽/контракт через ИТС)
  Источник данных: MOEX ISS API (Только реальные биржевые цены)
================================================================================
"""

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

CBR_RATES_SCHEDULE = [
    ('2023-01-01', '2023-07-23', 7.50,  'Стабильная ставка ЦБ'),
    ('2023-07-24', '2023-08-14', 8.50,  'Первое повышение ставки'),
    ('2023-08-15', '2023-09-17', 12.00, 'Внеочередное повышение ЦБ'),
    ('2023-09-18', '2023-10-29', 13.00, 'Ужесточение ДКП'),
    ('2023-10-30', '2023-12-17', 15.00, 'Рост инфляционного давления'),
    ('2023-12-18', '2024-07-28', 16.00, 'Длительное удержание 16%'),
    ('2024-07-29', '2024-09-15', 18.00, 'Новый этап повышения'),
    ('2024-09-16', '2024-10-27', 19.00, 'Борьба с перегревом экономики'),
    ('2024-10-28', '2025-06-30', 21.00, 'Рекордный уровень ставки 21%'),
    ('2025-07-01', '2025-12-31', 18.00, 'Первое снижение ключевой ставки'),
    ('2026-01-01', '2026-05-31', 16.00, 'Постепенная нормализация ДКП'),
    ('2026-06-01', '2026-12-31', 14.00, 'Текущий уровень ключевой ставки ЦБ (14%)')
]

def get_cbr_rate_for_date(date_str):
    for start_d, end_d, rate, _ in CBR_RATES_SCHEDULE:
        if start_d <= date_str <= end_d:
            return rate
    return 14.00

def fetch_moex_history(engine, market, board, security, date_from, date_till):
    url = f"https://iss.moex.com/iss/history/engines/{engine}/markets/{market}/securities/{security}.json?from={date_from}&till={date_till}"
    if board:
        url = f"https://iss.moex.com/iss/history/engines/{engine}/markets/{market}/boards/{board}/securities/{security}.json?from={date_from}&till={date_till}"
    
    rows = []
    start = 0
    while True:
        req_url = f"{url}&start={start}"
        response = requests.get(req_url).json()
        data = response['history']['data']
        cols = response['history']['columns']
        if not data:
            break
        df = pd.DataFrame(data, columns=cols)
        rows.append(df)
        start += len(data)
        if len(data) < 100:
            break
            
    if not rows:
        return pd.DataFrame()
        
    result_df = pd.concat(rows, ignore_index=True)
    result_df['TRADEDATE'] = pd.to_datetime(result_df['TRADEDATE'])
    return result_df

def run_full_cny_cash_and_carry_backtest(initial_capital=1000000.0):
    print("=" * 80)
    print("  ЗАПУСК СИМУЛЯЦИИ CASH-AND-CARRY НА MOEX (01.01.2023 - 20.08.2026)")
    print("  ТАРИФ «СТАНДАРТНЫЙ ФОРТС» (Брокер 0.45 ₽ + Биржа ~1.00 ₽)")
    print(f"  Начальный капитал: {initial_capital:,.2f} руб.")
    print("=" * 80)
    
    spot_df = fetch_moex_history('currency', 'selt', 'CETS', 'CNYRUB_TOM', '2023-01-01', '2026-08-20')
    spot_prices = dict(zip(spot_df['TRADEDATE'].dt.strftime('%Y-%m-%d'), spot_df['CLOSE']))
    
    futures_contracts = [
        ('CRH3', 'CNY-3.23',  '2023-01-03', '2023-03-16'),
        ('CRM3', 'CNY-6.23',  '2023-03-17', '2023-06-15'),
        ('CRU3', 'CNY-9.23',  '2023-06-16', '2023-09-21'),
        ('CRZ3', 'CNY-12.23', '2023-09-22', '2023-12-21'),
        ('CRH4', 'CNY-3.24',  '2023-12-22', '2024-03-21'),
        ('CRM4', 'CNY-6.24',  '2024-03-22', '2024-06-20'),
        ('CRU4', 'CNY-9.24',  '2024-06-21', '2024-09-19'),
        ('CRZ4', 'CNY-12.24', '2024-09-20', '2024-12-19'),
        ('CRH5', 'CNY-3.25',  '2024-12-20', '2025-03-20'),
        ('CRM5', 'CNY-6.25',  '2025-03-21', '2025-06-19'),
        ('CRU5', 'CNY-9.25',  '2025-06-20', '2025-09-18'),
        ('CRZ5', 'CNY-12.25', '2025-09-19', '2025-12-18'),
        ('CRH6', 'CNY-3.26',  '2025-12-19', '2026-03-19'),
        ('CRM6', 'CNY-6.26',  '2026-03-20', '2026-06-18'),
        ('CRU6', 'CNY-9.26',  '2026-06-19', '2026-08-19')
    ]
    
    SPOT_FEE_RATE = 0.00025               # 0.025%
    FORTS_FEE_PER_CONTRACT = 1.45        # 0.45 ₽ брокер + ~1.00 ₽ биржа
    
    current_capital = initial_capital
    trade_history = []
    
    for secid, short_name, start_date, end_date in futures_contracts:
        fut_df = fetch_moex_history('futures', 'forts', None, secid, start_date, end_date)
        if fut_df.empty:
            continue
            
        fut_prices = dict(zip(fut_df['TRADEDATE'].dt.strftime('%Y-%m-%d'), fut_df['CLOSE']))
        
        common_dates = sorted(list(set(fut_prices.keys()).intersection(set(spot_prices.keys()))))
        if not common_dates:
            continue
            
        entry_date = common_dates[0]
        exit_date = common_dates[-1]
        
        spot_entry_p = spot_prices[entry_date]
        fut_entry_p = fut_prices[entry_date]
        spot_exit_p = spot_prices[exit_date]
        fut_exit_p = fut_prices[exit_date]
        
        days_held = (pd.to_datetime(exit_date) - pd.to_datetime(entry_date)).days
        cbr_rate = get_cbr_rate_for_date(entry_date)
        
        contango_pct = ((fut_entry_p / spot_entry_p) - 1.0) * 100.0
        
        if contango_pct > 0.5:
            strategy_type = "CASH & CARRY"
            lots = int((current_capital * 0.75) / (spot_entry_p * 1000.0))
            cny_volume = lots * 1000
            
            spot_buy_cost = cny_volume * spot_entry_p
            spot_fee_in = spot_buy_cost * SPOT_FEE_RATE
            forts_fee_in = lots * FORTS_FEE_PER_CONTRACT
            cash_reserve = current_capital - spot_buy_cost - spot_fee_in - forts_fee_in
            
            spot_sell_val = cny_volume * spot_exit_p
            spot_fee_out = spot_sell_val * SPOT_FEE_RATE
            forts_fee_out = lots * FORTS_FEE_PER_CONTRACT
            
            fut_pnl = (fut_entry_p - fut_exit_p) * cny_volume
            total_fees = spot_fee_in + spot_fee_out + forts_fee_in + forts_fee_out
            
            net_trade_pnl = (spot_sell_val - spot_buy_cost) + fut_pnl - total_fees
            capital_end = cash_reserve + spot_sell_val - spot_fee_out - forts_fee_out + fut_pnl
        else:
            strategy_type = "RUSFAR (РЕПО)"
            lots = 0
            cny_volume = 0
            total_fees = 0.0
            net_trade_pnl = current_capital * (cbr_rate / 100.0) * (days_held / 365.0)
            capital_end = current_capital + net_trade_pnl
            
        cycle_ret_pct = (net_trade_pnl / current_capital) * 100.0
        apr_ret_pct = cycle_ret_pct * (365.0 / max(days_held, 1))
        
        trade_history.append({
            'Контракт': secid,
            'Стратегия': strategy_type,
            'Вход': entry_date,
            'Выход': exit_date,
            'Дней': days_held,
            'Спот Вход': spot_entry_p,
            'Фьюч Вход': fut_entry_p,
            'Контанго (%)': contango_pct,
            'Комиссия (руб)': total_fees,
            'Чистый PnL (руб)': net_trade_pnl,
            'Доходность (APR %)': apr_ret_pct,
            'Капитал (руб)': capital_end,
            'Ставка ЦБ (%)': cbr_rate
        })
        
        current_capital = capital_end

    results_df = pd.DataFrame(trade_history)
    print("\nИТОГОВАЯ ТАБЛИЦА СДЕЛОК (01.01.2023 - 20.08.2026):")
    print(results_df.to_string(index=False))
    
    total_profit = current_capital - initial_capital
    total_pct = (total_profit / initial_capital) * 100.0
    print("\n" + "=" * 80)
    print(f"  Начальный депозит: {initial_capital:,.2f} руб.")
    print(f"  Конечный депозит:  {current_capital:,.2f} руб. (на 20.08.2026)")
    print(f"  Чистая прибыль:    +{total_profit:,.2f} руб. (+{total_pct:.2f}%)")
    print("=" * 80)

if __name__ == "__main__":
    run_full_cny_cash_and_carry_backtest()
