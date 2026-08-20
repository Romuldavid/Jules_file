import requests
import pandas as pd
import numpy as np

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

print("Downloading spot CNYRUB_TOM data...")
spot_df = fetch_moex_history('currency', 'selt', 'CETS', 'CNYRUB_TOM', '2023-01-01', '2025-12-31')
print(f"Spot rows: {len(spot_df)}")

# List of quarterly futures
futures_secids = [
    ('CRH3', '2023-01-03', '2023-03-16'),
    ('CRM3', '2023-03-17', '2023-06-15'),
    ('CRU3', '2023-06-16', '2023-09-21'),
    ('CRZ3', '2023-09-22', '2023-12-21'),
    ('CRH4', '2023-12-22', '2024-03-21'),
    ('CRM4', '2024-03-22', '2024-06-20'),
    ('CRU4', '2024-06-21', '2024-09-19'),
    ('CRZ4', '2024-09-20', '2024-12-19'),
    ('CRH5', '2024-12-20', '2025-03-20')
]

fut_dfs = {}
for secid, start_d, end_d in futures_secids:
    print(f"Downloading {secid}...")
    df = fetch_moex_history('futures', 'forts', None, secid, start_d, end_d)
    fut_dfs[secid] = df
    print(f"  {secid} rows: {len(df)}")

print("Done downloading data.")
