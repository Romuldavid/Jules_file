import requests
import pandas as pd
import numpy as np

# 1. CBR Key Rate changes table
cbr_rates = [
    ('2023-01-01', '2023-07-23', 7.50),
    ('2023-07-24', '2023-08-14', 8.50),
    ('2023-08-15', '2023-09-17', 12.00),
    ('2023-09-18', '2023-10-29', 13.00),
    ('2023-10-30', '2023-12-17', 15.00),
    ('2023-12-18', '2024-07-28', 16.00),
    ('2024-07-29', '2024-09-15', 18.00),
    ('2024-09-16', '2024-10-27', 19.00),
    ('2024-10-28', '2025-12-31', 21.00),
]

def get_cbr_rate(date_str):
    for start_d, end_d, rate in cbr_rates:
        if start_d <= date_str <= end_d:
            return rate
    return 21.00

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

print("Fetching MOEX spot CNYRUB_TOM data...")
spot_df = fetch_moex_history('currency', 'selt', 'CETS', 'CNYRUB_TOM', '2023-01-01', '2025-12-31')
spot_dict = dict(zip(spot_df['TRADEDATE'].dt.strftime('%Y-%m-%d'), spot_df['CLOSE']))

futures_list = [
    ('CRH3', 'CNY-3.23', '2023-01-03', '2023-03-16'),
    ('CRM3', 'CNY-6.23', '2023-03-17', '2023-06-15'),
    ('CRU3', 'CNY-9.23', '2023-06-16', '2023-09-21'),
    ('CRZ3', 'CNY-12.23', '2023-09-22', '2023-12-21'),
    ('CRH4', 'CNY-3.24', '2023-12-22', '2024-03-21'),
    ('CRM4', 'CNY-6.24', '2024-03-22', '2024-06-20'),
    ('CRU4', 'CNY-9.24', '2024-06-21', '2024-09-19'),
    ('CRZ4', 'CNY-12.24', '2024-09-20', '2024-12-19'),
    ('CRH5', 'CNY-3.25', '2024-12-20', '2025-03-20')
]

initial_capital = 1000000.0
capital = initial_capital

spot_fee_rate = 0.00025  # 0.025% spot fee
forts_fee_per_contract = 2.50 # 2.50 RUB per contract FORTS fee

trade_log = []

for secid, name, start_d, end_d in futures_list:
    fut_df = fetch_moex_history('futures', 'forts', None, secid, start_d, end_d)
    if fut_df.empty:
        continue
    
    fut_dict = dict(zip(fut_df['TRADEDATE'].dt.strftime('%Y-%m-%d'), fut_df['CLOSE']))
    
    common_dates = sorted(list(set(fut_dict.keys()).intersection(set(spot_dict.keys()))))
    if not common_dates:
        continue
    entry_date = common_dates[0]
    exit_date = common_dates[-1]
        
    p_spot_entry = spot_dict[entry_date]
    p_fut_entry = fut_dict[entry_date]
    p_spot_exit = spot_dict[exit_date]
    p_fut_exit = fut_dict[exit_date]
    
    days_held = (pd.to_datetime(exit_date) - pd.to_datetime(entry_date)).days
    cbr_rate_period = get_cbr_rate(entry_date)
    
    contango_pct = ((p_fut_entry / p_spot_entry) - 1) * 100
    ann_contango_pct = contango_pct * (365.0 / max(days_held, 1))
    
    # Smart Rule: If Contango is Positive and Attractive (> 1.0% APR), execute Cash & Carry.
    # Otherwise (e.g. backwardation during sanctions), place capital in Money Market (RUSFAR / REPO) at CBR rate!
    if contango_pct > 0.5:
        action = "CASH & CARRY"
        lots = int((capital * 0.75) / (p_spot_entry * 1000))
        cny_amount = lots * 1000
        
        spot_buy_cost = cny_amount * p_spot_entry
        spot_fee_entry = spot_buy_cost * spot_fee_rate
        forts_fee_entry = lots * forts_fee_per_contract
        
        cash_left = capital - spot_buy_cost - spot_fee_entry - forts_fee_entry
        
        spot_sell_val = cny_amount * p_spot_exit
        spot_fee_exit = spot_sell_val * spot_fee_rate
        forts_fee_exit = lots * forts_fee_per_contract
        
        fut_pnl = (p_fut_entry - p_fut_exit) * cny_amount
        
        net_pnl = (spot_sell_val - spot_buy_cost) + fut_pnl - (spot_fee_entry + spot_fee_exit + forts_fee_entry + forts_fee_exit)
        capital_end = cash_left + spot_sell_val - spot_fee_exit - forts_fee_exit + fut_pnl
        fees_paid = spot_fee_entry + spot_fee_exit + forts_fee_entry + forts_fee_exit
    else:
        action = "MONEY MARKET (RUSFAR)"
        lots = 0
        cny_amount = 0
        fees_paid = 0.0
        # Earn CBR key rate on cash capital
        net_pnl = capital * (cbr_rate_period / 100.0) * (days_held / 365.0)
        capital_end = capital + net_pnl
        
    cycle_return_pct = (net_pnl / capital) * 100
    annual_return_pct = cycle_return_pct * (365.0 / max(days_held, 1))
    
    trade_log.append({
        'contract': secid,
        'name': name,
        'action': action,
        'entry_date': entry_date,
        'exit_date': exit_date,
        'days': days_held,
        'spot_entry': p_spot_entry,
        'fut_entry': p_fut_entry,
        'spot_exit': p_spot_exit,
        'fut_exit': p_fut_exit,
        'contango_pct': contango_pct,
        'ann_contango_pct': ann_contango_pct,
        'lots': lots,
        'fees_rub': fees_paid,
        'net_pnl_rub': net_pnl,
        'capital_start': capital,
        'capital_end': capital_end,
        'cycle_return_pct': cycle_return_pct,
        'annual_return_pct': annual_return_pct,
        'cbr_rate': cbr_rate_period
    })
    
    capital = capital_end

df_trades = pd.DataFrame(trade_log)
print("\n=== SMART CASH AND CARRY BACKTEST RESULTS (2023 - 2025) ===")
print(df_trades[['contract', 'action', 'entry_date', 'exit_date', 'days', 'contango_pct', 'net_pnl_rub', 'annual_return_pct', 'capital_end', 'cbr_rate']].to_string())

total_net_profit = capital - initial_capital
total_days = (pd.to_datetime(df_trades.iloc[-1]['exit_date']) - pd.to_datetime(df_trades.iloc[0]['entry_date'])).days
total_return_pct = (total_net_profit / initial_capital) * 100
cagr_pct = (((capital / initial_capital) ** (365.0 / total_days)) - 1) * 100

print(f"\nInitial Capital: {initial_capital:,.2f} RUB")
print(f"Final Capital: {capital:,.2f} RUB")
print(f"Total Profit: {total_net_profit:,.2f} RUB ({total_return_pct:.2f}%)")
print(f"Total Period: {total_days} days")
print(f"CAGR (Annualized Return): {cagr_pct:.2f}% APR")
