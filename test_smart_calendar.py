import requests
import pandas as pd
import numpy as np

cbr_rates = [
    ('2023-01-01', '2023-07-23', 7.50),
    ('2023-07-24', '2023-08-14', 8.50),
    ('2023-08-15', '2023-09-17', 12.00),
    ('2023-09-18', '2023-10-29', 13.00),
    ('2023-10-30', '2023-12-17', 15.00),
    ('2023-12-18', '2024-07-28', 16.00),
    ('2024-07-29', '2024-09-15', 18.00),
    ('2024-09-16', '2024-10-27', 19.00),
    ('2024-10-28', '2025-06-30', 21.00),
    ('2025-07-01', '2025-12-31', 18.00),
    ('2026-01-01', '2026-05-31', 16.00),
    ('2026-06-01', '2026-12-31', 14.00),
]

def get_cbr_rate(date_str):
    for start_d, end_d, rate in cbr_rates:
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
        r = requests.get(req_url).json()
        data = r['history']['data']
        cols = r['history']['columns']
        if not data:
            break
        df = pd.DataFrame(data, columns=cols)
        rows.append(df)
        start += len(data)
        if len(data) < 100:
            break
    if not rows:
        return pd.DataFrame()
    res = pd.concat(rows, ignore_index=True)
    res['TRADEDATE'] = pd.to_datetime(res['TRADEDATE'])
    return res

tickers = {
    'SBER': 'SR',
    'GAZP': 'GZ',
    'LKOH': 'LK',
    'GMKN': 'GK',
    'NVTK': 'NK'
}

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

initial_capital = 1000000.0
capital = initial_capital

# Tariff «Стандартный ФОРТС»: 0.45 RUB broker fee + ~1.00 RUB exchange fee per contract
# Total per spread leg pair (2 contracts) = 2.90 RUB entry + 2.90 RUB exit = 5.80 RUB round-trip
forts_fee_per_contract = 1.45 # 1.45 RUB per contract

spread_results = []

for q_near, q_far, start_d, end_d in quarters:
    cbr_rate = get_cbr_rate(start_d)
    
    cycle_pnl = 0.0
    asset_details = []
    
    for stock_name, prefix in tickers.items():
        near_secid = f"{prefix}{q_near}"
        far_secid = f"{prefix}{q_far}"
        
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
        
        days = (pd.to_datetime(x_date) - pd.to_datetime(e_date)).days
        
        capital_per_asset = capital * 0.20
        contracts = int(capital_per_asset / (p_near_in * 0.15))
        if contracts < 1:
            contracts = 1
            
        # Direction: If spread_in < 0 (Backwardation due to dividend or market distortion),
        # execute Long Far / Short Near (capture spread expansion upon dividend realization/expiration)
        # If spread_in > 0 (Contango), execute Long Near / Short Far (capture contango decay)
        if spread_in < 0:
            direction = 1 # Long Far / Short Near
            raw_pnl = (spread_out - spread_in) * contracts
        else:
            direction = -1 # Short Far / Long Near
            raw_pnl = (spread_in - spread_out) * contracts
            
        fees = contracts * 2 * forts_fee_per_contract * 2 # 2 contracts (near+far), entry + exit
        net_asset_pnl = raw_pnl - fees
        
        cycle_pnl += net_asset_pnl
        asset_details.append(f"{stock_name}({contracts}к): {net_asset_pnl:+,.0f}₽")
        
    capital_end = capital + cycle_pnl
    days_held = (pd.to_datetime(end_d) - pd.to_datetime(start_d)).days
    ret_pct = (cycle_pnl / capital) * 100
    apr_pct = ret_pct * (365.0 / max(days_held, 1))
    
    spread_results.append({
        'cycle': f"{q_near}-{q_far}",
        'start_date': start_d,
        'end_date': end_d,
        'days': days_held,
        'cbr_rate': cbr_rate,
        'pnl_rub': cycle_pnl,
        'return_pct': ret_pct,
        'apr_pct': apr_pct,
        'capital_end': capital_end,
        'details': ", ".join(asset_details)
    })
    
    capital = capital_end

df_res = pd.DataFrame(spread_results)
print("\n=== SMART CALENDAR SPREAD ARBITRAGE RESULTS (01.01.2023 - 20.08.2026) ===")
print(df_res[['cycle', 'start_date', 'end_date', 'cbr_rate', 'pnl_rub', 'apr_pct', 'capital_end']].to_string())

tot_profit = capital - initial_capital
tot_ret = (tot_profit / initial_capital) * 100
cagr = (((capital / initial_capital) ** (365.0 / (365 * 3.63))) - 1) * 100
print(f"\nInitial Capital: {initial_capital:,.2f} RUB")
print(f"Final Capital: {capital:,.2f} RUB")
print(f"Total Net Profit: {tot_profit:,.2f} RUB ({tot_ret:.2f}%)")
