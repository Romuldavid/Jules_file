"""
================================================================================
  КАЛЕНДАРНЫЙ АРБИТРАЖ НА ФЬЮЧЕРСАХ АКЦИЙ МОСКОВСКОЙ БИРЖИ (MOEX)
  Период анализа: 01 января 2023 г. — 20 августа 2026 г. (Сегодня)
  Начальный капитал: 1 000 000.00 рублей
  Инструменты: Фьючерсы на акции SBER, GAZP, LKOH, GMKN, NVTK
  Тарифный план: «Стандартный ФОРТС» (Комиссия брокера 0.45 ₽/контракт через ИТС)
================================================================================
"""

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Динамика Ключевой Ставки ЦБ РФ (2023 - 2026 гг.)
CBR_RATES_SCHEDULE = [
    ('2023-01-01', '2023-07-23', 7.50,  'Стабильная ставка ЦБ'),
    ('2023-07-24', '2023-08-14', 8.50,  'Первое повышение ставки'),
    ('2023-08-15', '2023-09-17', 12.00, 'Внеочередное повышение ЦБ'),
    ('2023-09-18', '2023-10-29', 13.00, 'Ужесточение ДКП'),
    ('2023-10-30', '2023-12-17', 15.00, 'Рост инфляционного давления'),
    ('2023-12-18', '2024-07-28', 16.00, 'Длительное удержание 16%'),
    ('2024-07-29', '2024-09-15', 18.00, 'Новый этап повышения'),
    ('2024-09-16', '2024-10-27', 19.00, 'Борьба с перегревом экономики'),
    ('2024-10-28', '2025-06-30', 21.00, 'Пиковый уровень ставки 21%'),
    ('2025-07-01', '2025-12-31', 18.00, 'Первое снижение ставки ЦБ'),
    ('2026-01-01', '2026-05-31', 16.00, 'Постепенная нормализация ДКП'),
    ('2026-06-01', '2026-12-31', 14.00, 'Текущий уровень ключевой ставки ЦБ (14%)')
]

def get_cbr_rate_for_date(date_str):
    for start_d, end_d, rate, _ in CBR_RATES_SCHEDULE:
        if start_d <= date_str <= end_d:
            return rate
    return 14.00

def fetch_moex_history(engine, market, board, security, date_from, date_till):
    url = f"https://iss.moex.com/iss/history/engines/{{engine}}/markets/{{market}}/securities/{{security}}.json?from={{date_from}}&till={{date_till}}"
    if board:
        url = f"https://iss.moex.com/iss/history/engines/{{engine}}/markets/{{market}}/boards/{{board}}/securities/{{security}}.json?from={{date_from}}&till={{date_till}}"
    
    rows = []
    start = 0
    while True:
        req_url = f"{{url}}&start={{start}}"
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

def run_stock_calendar_spread_backtest(initial_capital=1000000.0):
    print("=" * 80)
    print("  БЭКТЕСТ КАЛЕНДАРНОГО АРБИТРАЖА НА ФЬЮЧЕРСАХ АКЦИЙ MOEX (01.01.2023 - 20.08.2026)")
    print("  ТАРИФ «СТАНДАРТНЫЙ ФОРТС» (Брокер 0.45 ₽ + Биржа ~1.00 ₽)")
    print(f"  Начальный капитал: {{initial_capital:,.2f}} руб.")
    print("=" * 80)
    
    stock_tickers = {{
        'SBER': 'SR',
        'GAZP': 'GZ',
        'LKOH': 'LK',
        'GMKN': 'GK',
        'NVTK': 'NK'
    }}
    
    known_dividends = {{
        ('SR', 'M3'): 2500.0,
        ('SR', 'M4'): 3330.0,
        ('SR', 'M5'): 3400.0,
        ('LK', 'M3'): 4380.0,
        ('LK', 'M4'): 4980.0,
        ('LK', 'M5'): 5200.0,
    }}
    
    quarters = [
        ('H3', 'M3', '2023-01-03', '2023-03-16'),
        ('M3', 'U3', '2023-03-17', '2023-06-15'),
        ('U3', 'Z3', '2023-06-16', '2023-09-21'),
        ('Z3', 'H4', '2023-09-22', '2023-12-21'),
        ('H4', 'M4', '2023-12-22', '2024-03-21'),
        ('M4', 'U4', '2024-03-22', '2024-06-20'),
        ('U4', 'Z4', '2024-06-21', '2024-09-19'),
        ('Z4', 'H5', '2024-09-20', '2024-12-19'),
        ('H5', 'M5', '2024-12-20', '2025-03-20'),
        ('M5', 'U5', '2025-03-21', '2025-06-19'),
        ('U5', 'Z5', '2025-06-20', '2025-09-18'),
        ('Z5', 'H6', '2025-09-19', '2025-12-18'),
        ('H6', 'M6', '2025-12-19', '2026-03-19'),
        ('M6', 'U6', '2026-03-20', '2026-06-18'),
        ('U6', 'Z6', '2026-06-19', '2026-08-19')
    ]
    
    FORTS_FEE_PER_CONTRACT = 1.45  # 0.45 ₽ брокер + ~1.00 ₽ биржа
    current_capital = initial_capital
    spread_history = []
    
    for q_near, q_far, start_d, end_d in quarters:
        cbr_rate = get_cbr_rate_for_date(start_d)
        days_held = (pd.to_datetime(end_d) - pd.to_datetime(start_d)).days
        
        cycle_pnl = 0.0
        asset_breakdown = []
        
        for stock_name, prefix in stock_tickers.items():
            near_secid = f"{{prefix}}{{q_near}}"
            far_secid = f"{{prefix}}{{q_far}}"
            
            df_near = fetch_moex_history('futures', 'forts', None, near_secid, start_d, end_d)
            df_far = fetch_moex_history('futures', 'forts', None, far_secid, start_d, end_d)
            
            if df_near.empty or df_far.empty:
                continue
                
            dict_near = dict(zip(df_near['TRADEDATE'].dt.strftime('%Y-%m-%d'), df_near['CLOSE']))
            dict_far = dict(zip(df_far['TRADEDATE'].dt.strftime('%Y-%m-%d'), df_far['CLOSE']))
            
            common_dates = sorted(list(set(dict_near.keys()).intersection(set(dict_far.keys()))))
            if not common_dates:
                continue
                
            e_date = common_dates[0]
            x_date = common_dates[-1]
            
            p_near_in = dict_near[e_date]
            p_far_in = dict_far[e_date]
            p_near_out = dict_near[x_date]
            p_far_out = dict_far[x_date]
            
            if pd.isna(p_near_in) or pd.isna(p_far_in) or pd.isna(p_near_out) or pd.isna(p_far_out):
                continue
                
            spread_in = p_far_in - p_near_in
            spread_out = p_far_out - p_near_out
            
            expected_div = known_dividends.get((prefix, q_far), 0.0)
            fair_spread = (p_near_in * (cbr_rate / 100.0) * (days_held / 365.0)) - expected_div
            
            capital_per_asset = current_capital * 0.20
            contracts = int(capital_per_asset / (p_near_in * 0.15))
            if contracts < 1:
                contracts = 1
                
            if spread_in > fair_spread:
                raw_pnl = (spread_in - spread_out) * contracts
            else:
                raw_pnl = (spread_out - spread_in) * contracts
                
            total_fees = contracts * 2 * FORTS_FEE_PER_CONTRACT * 2
            net_asset_pnl = raw_pnl - total_fees
            
            cycle_pnl += net_asset_pnl
            asset_breakdown.append(f"{{prefix}}({{contracts}}к): {{net_asset_pnl:+,.0f}}₽")
            
        capital_end = current_capital + cycle_pnl
        ret_pct = (cycle_pnl / current_capital) * 100.0
        apr_pct = ret_pct * (365.0 / max(days_held, 1))
        
        spread_history.append({{
            'Цикл': f"{{q_near}}-{{q_far}}",
            'Старт': start_d,
            'Конец': end_d,
            'Дней': days_held,
            'Ставка ЦБ (%)': cbr_rate,
            'PnL (руб)': cycle_pnl,
            'Доходность (%)': ret_pct,
            'Доходность (APR %)': apr_pct,
            'Капитал (руб)': capital_end
        }})
        
        current_capital = capital_end

    results_df = pd.DataFrame(spread_history)
    print("\nИТОГОВАЯ ТАБЛИЦА СДЕЛОК КАЛЕНДАРНОГО АРБИТРАЖА:")
    print(results_df.to_string(index=False))
    
    total_profit = current_capital - initial_capital
    total_pct = (total_profit / initial_capital) * 100.0
    print("\n" + "=" * 80)
    print(f"  Начальный депозит: {{initial_capital:,.2f}} руб.")
    print(f"  Конечный депозит:  {{current_capital:,.2f}} руб. (на 20.08.2026)")
    print(f"  Чистая прибыль:    +{{total_profit:,.2f}} руб. (+{{total_pct:.2f}}%)")
    print("=" * 80)

if __name__ == "__main__":
    run_stock_calendar_spread_backtest()
