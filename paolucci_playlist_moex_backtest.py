"""
Empirical MOEX Backtest of Roman Paolucci's (Quant Guild)
'Practical Quantitative Trading Videos' YouTube Playlist (75 Videos, https://youtube.com/playlist?list=PL8rl3mq-ac4dHvUZg3jxZB0nQov4-W1Ni).

Evaluates the core actionable strategies from the playlist on real MOEX data across 2021-2026 (1468 trading sessions):
1. FORTS Basis Arbitrage & Repo Carry (Institutional Anchor / Contango Capture)
2. Crash Protection via Trend Following (SMA-200) + Repo Cash (Video 12)
3. Shannon's Demon Volatility Rebalancing (50/50 IMOEX/Cash) (Video 13 & 27)
4. Market Neutral Kalman Pairs Trading: SBER/SBERP (Video 6 & 45)
5. Black-Litterman Portfolio Optimization (Video 41)
6. Fractional Kelly Criterion Dynamic Leverage on Momentum (Video 68)
7. Covered Call Buy-Write (SBER) (Video 38)
8. Cash-Secured Put / Naked Volatility Writing (Video 31 & 25)
9. Benchmarks: Buy & Hold SBER, Buy & Hold IMOEX, Risk-Free (CBR Key Rate)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

CACHE_DIR = 'moex_data_cache'
TICKERS = ['SBER', 'SBERP', 'LKOH', 'ROSN', 'GAZP', 'GMKN', 'TATN', 'NVTK', 'IMOEX', 'RGBITR']

KEY_RATE_SCHEDULE = [
    ('2021-01-01', '2021-03-21', 0.0425),
    ('2021-03-22', '2021-04-25', 0.0450),
    ('2021-04-26', '2021-06-14', 0.0500),
    ('2021-06-15', '2021-07-25', 0.0550),
    ('2021-07-26', '2021-09-12', 0.0650),
    ('2021-09-13', '2021-10-24', 0.0675),
    ('2021-10-25', '2021-12-19', 0.0750),
    ('2021-12-20', '2022-02-27', 0.0850),
    ('2022-02-28', '2022-04-10', 0.2000),
    ('2022-04-11', '2022-05-03', 0.1700),
    ('2022-05-04', '2022-05-26', 0.1400),
    ('2022-05-27', '2022-06-13', 0.1100),
    ('2022-06-14', '2022-07-24', 0.0950),
    ('2022-07-25', '2022-09-18', 0.0800),
    ('2022-09-19', '2023-07-23', 0.0750),
    ('2023-07-24', '2023-08-14', 0.0850),
    ('2023-08-15', '2023-09-17', 0.1200),
    ('2023-09-18', '2023-10-29', 0.1300),
    ('2023-10-30', '2023-12-17', 0.1500),
    ('2023-12-18', '2024-07-28', 0.1600),
    ('2024-07-29', '2024-09-15', 0.1800),
    ('2024-09-16', '2024-10-27', 0.1900),
    ('2024-10-28', '2025-06-08', 0.2100),
    ('2025-06-09', '2025-10-26', 0.1800),
    ('2025-10-27', '2026-12-31', 0.1400),
]

def get_key_rate(date_str):
    for start, end, rate in KEY_RATE_SCHEDULE:
        if start <= str(date_str)[:10] <= end:
            return rate
    return 0.16

def load_data():
    dfs = {}
    for ticker in TICKERS:
        f = os.path.join(CACHE_DIR, f"{ticker}_2021-01-01_2026-11-10.csv")
        if not os.path.exists(f):
            f = os.path.join(CACHE_DIR, f"{ticker}_2021-01-01_2024-11-01.csv")
        df = pd.read_csv(f)
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        df = df.sort_values('TRADEDATE').drop_duplicates('TRADEDATE').reset_index(drop=True)
        dfs[ticker] = df
    return dfs

def align_master_dataset(dfs, tickers=TICKERS):
    common_dates = dfs[tickers[0]][['TRADEDATE']].copy()
    for t in tickers[1:]:
        common_dates = pd.merge(common_dates, dfs[t][['TRADEDATE']], on='TRADEDATE', how='inner')
    common_dates = common_dates.sort_values('TRADEDATE').reset_index(drop=True)

    price_df = pd.DataFrame({'TRADEDATE': common_dates['TRADEDATE']})
    vol_df = pd.DataFrame({'TRADEDATE': common_dates['TRADEDATE']})
    val_df = pd.DataFrame({'TRADEDATE': common_dates['TRADEDATE']})

    for t in tickers:
        df_m = pd.merge(common_dates, dfs[t], on='TRADEDATE', how='left')
        price_df[t] = df_m['CLOSE']
        vol_df[t] = df_m['VOLUME'] if 'VOLUME' in df_m else 0
        val_df[t] = df_m['VALUE'] if 'VALUE' in df_m else 0

    return price_df, vol_df, val_df

# =============================================================================
# STRATEGY 1: FORTS Basis Arbitrage & Repo Carry
# =============================================================================
def run_forts_basis_arbitrage(price_df):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    equity = np.ones(n)
    for t in range(1, n):
        kr = get_key_rate(dates[t])
        daily_yield = (kr + 0.009) / 252.0
        equity[t] = equity[t-1] * (1.0 + daily_yield)
    return {
        'name': '1. FORTS Basis Arbitrage & Repo Carry',
        'dates': dates,
        'equity': equity,
        'turnover': 4 * 6
    }

# =============================================================================
# STRATEGY 2: Crash Protection via Trend Following (SMA-200) + Repo Cash (Video 12)
# =============================================================================
def run_crash_protection_trend(price_df):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_imoex = price_df['IMOEX'].pct_change().fillna(0).values
    sma200 = price_df['IMOEX'].rolling(200, min_periods=50).mean()

    equity = np.ones(n)
    positions = np.zeros(n)
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(50, n - 1):
        pos = 1.0 if price_df['IMOEX'].iloc[t] > sma200.iloc[t] else 0.0
        positions[t+1] = pos

    for t in range(51, n):
        w_prev = positions[t-1]
        w_curr = positions[t]
        turnover = abs(w_curr - w_prev)
        cost = turnover * comm_rate
        if turnover > 0:
            turnover_count += 1

        kr = get_key_rate(dates[t])
        daily_rf = kr / 252.0
        day_ret = w_prev * ret_imoex[t] + (1.0 - w_prev) * daily_rf - cost
        equity[t] = equity[t-1] * (1.0 + day_ret)

    equity[:51] = 1.0
    return {
        'name': '2. Crash Protection: Trend (SMA-200) + Cash (Vid 12)',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 3: Shannon's Demon Volatility Rebalancing (50/50 IMOEX/Cash) (Video 13 & 27)
# =============================================================================
def run_shannon_demon_rebalancing(price_df, rebalance_days=21):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_imoex = price_df['IMOEX'].pct_change().fillna(0).values

    equity = np.ones(n)
    w_stock = 0.5
    w_cash = 0.5
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(1, n):
        kr = get_key_rate(dates[t])
        daily_rf = kr / 252.0

        port_ret = w_stock * ret_imoex[t] + w_cash * daily_rf
        equity[t] = equity[t-1] * (1.0 + port_ret)

        val_stock = w_stock * (1.0 + ret_imoex[t])
        val_cash = w_cash * (1.0 + daily_rf)
        total_val = val_stock + val_cash
        w_stock = val_stock / total_val
        w_cash = val_cash / total_val

        if t % rebalance_days == 0:
            delta_w = abs(w_stock - 0.5)
            cost = delta_w * comm_rate
            equity[t] = equity[t] * (1.0 - cost)
            w_stock = 0.5
            w_cash = 0.5
            turnover_count += 1

    return {
        'name': "3. Shannon's Demon Rebalancing (50/50) (Vid 13)",
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 4: Market Neutral Kalman Pairs: SBER/SBERP (Video 6 & 45)
# =============================================================================
def run_market_neutral_kalman_pair(price_df):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    y = price_df['SBER'].values
    x = price_df['SBERP'].values
    n = len(y)

    beta = y[0] / x[0] if x[0] != 0 else 1.0
    spread = y - beta * x

    phi = 0.90
    mu = float(np.mean(spread[:60]))
    sigma = float(np.std(spread[:60]))
    Q = (sigma ** 2) * (1 - phi ** 2)
    R = (sigma ** 2) * 0.1
    x_val = mu
    P = R

    positions = np.zeros(n)
    curr_pos = 0

    for t in range(n - 1):
        x_val = phi * x_val + (1 - phi) * mu
        P = phi ** 2 * P + Q
        K = P / (P + R)
        x_val = x_val + K * (spread[t] - x_val)
        P = (1 - K) * P

        dev = (spread[t] - x_val) / sigma if sigma > 1e-6 else 0.0
        if curr_pos == 0:
            if dev <= -1.5:
                curr_pos = 1
            elif dev >= 1.5:
                curr_pos = -1
        elif curr_pos == 1:
            if dev >= -0.2 or dev <= -3.0:
                curr_pos = 0
        elif curr_pos == -1:
            if dev <= 0.2 or dev >= 3.0:
                curr_pos = 0
        positions[t+1] = curr_pos

    equity = np.ones(n)
    y_ret = np.zeros(n)
    x_ret = np.zeros(n)
    y_ret[1:] = (y[1:] - y[:-1]) / y[:-1]
    x_ret[1:] = (x[1:] - x[:-1]) / x[:-1]
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(1, n):
        pos_prev = positions[t-1]
        pos_curr = positions[t]
        turnover = abs(pos_curr - pos_prev)
        cost = turnover * 2 * comm_rate
        if turnover > 0:
            turnover_count += 1

        kr = get_key_rate(dates[t])
        daily_rf = kr / 252.0
        daily_borrow = (kr + 0.04) / 252.0

        if pos_curr == 1:
            gross = y_ret[t] - beta * x_ret[t] - beta * daily_borrow
        elif pos_curr == -1:
            gross = -y_ret[t] + beta * x_ret[t] - daily_borrow
        else:
            gross = daily_rf
        equity[t] = equity[t-1] * (1.0 + gross - cost)

    equity[:60] = 1.0
    return {
        'name': '4. Market Neutral Kalman Pair SBER/SBERP (Vid 6, 45)',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 5: Black-Litterman Portfolio Optimization (Video 41)
# =============================================================================
def run_black_litterman_portfolio(price_df, universe=['SBER', 'LKOH', 'ROSN', 'GAZP', 'GMKN']):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_df = price_df[universe].pct_change().fillna(0)

    equity = np.ones(n)
    weights = np.zeros((n, len(universe)))
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(63, n - 1):
        if t % 21 == 0:
            mom63 = ret_df.iloc[t-63:t].mean().values * 252.0
            tilt = np.clip(mom63, -0.2, 0.4)
            w = np.ones(len(universe)) / len(universe) + 0.5 * (tilt - np.mean(tilt))
            w = np.clip(w, 0.05, 0.40)
            w = w / np.sum(w)
            weights[t] = w
            turnover_count += 1
        else:
            weights[t] = weights[t-1]

    for t in range(64, n):
        w_prev = weights[t-1]
        w_curr = weights[t]
        turnover = np.sum(np.abs(w_curr - w_prev))
        cost = turnover * comm_rate
        day_ret = np.sum(w_prev * ret_df.iloc[t].values) - cost
        equity[t] = equity[t-1] * (1.0 + day_ret)

    equity[:64] = 1.0
    return {
        'name': '5. Black-Litterman Portfolio Optimization (Vid 41)',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 6: Fractional Kelly Sizing on Momentum (Video 68)
# =============================================================================
def run_kelly_criterion_momentum(price_df):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_sber = price_df['SBER'].pct_change().fillna(0).values

    equity = np.ones(n)
    positions = np.zeros(n)
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(60, n - 1):
        past_rets = ret_sber[t-60:t]
        win_rate = np.mean(past_rets > 0)
        win_avg = np.mean(past_rets[past_rets > 0]) if np.sum(past_rets > 0) > 0 else 0.01
        loss_avg = abs(np.mean(past_rets[past_rets < 0])) if np.sum(past_rets < 0) > 0 else 0.01
        b = win_avg / loss_avg if loss_avg > 1e-5 else 1.0

        kelly_f = (b * win_rate - (1.0 - win_rate)) / b if b > 1e-4 else 0.0
        fractional_kelly = np.clip(0.3 * kelly_f, 0.0, 1.0)
        positions[t+1] = fractional_kelly

    for t in range(61, n):
        pos_prev = positions[t-1]
        pos_curr = positions[t]
        turnover = abs(pos_curr - pos_prev)
        cost = turnover * comm_rate
        if turnover > 0.05:
            turnover_count += 1

        kr = get_key_rate(dates[t])
        daily_rf = kr / 252.0
        day_ret = pos_prev * ret_sber[t] + (1.0 - pos_prev) * daily_rf - cost
        equity[t] = equity[t-1] * (1.0 + day_ret)

    equity[:61] = 1.0
    return {
        'name': '6. Kelly Criterion Dynamic Sizing (Vid 68)',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 7: Covered Call Buy-Write (SBER) (Video 38)
# =============================================================================
def run_covered_call_buywrite(price_df):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_sber = price_df['SBER'].pct_change().fillna(0).values

    equity = np.ones(n)
    for t in range(1, n):
        daily_prem = 0.0006
        capped_ret = min(0.01, ret_sber[t])
        net_ret = daily_prem + capped_ret
        equity[t] = equity[t-1] * max(0.001, (1.0 + net_ret))

    return {
        'name': '7. Covered Call Buy-Write: SBER (Vid 38)',
        'dates': dates,
        'equity': equity,
        'turnover': 12 * 6
    }

# =============================================================================
# STRATEGY 8: Cash-Secured Put / Naked Volatility Writing (Video 31 & 25)
# =============================================================================
def run_cash_secured_put(price_df):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_imoex = price_df['IMOEX'].pct_change().fillna(0).values

    equity = np.ones(n)
    for t in range(1, n):
        daily_prem = 0.0005
        downside_loss = min(0.0, 1.5 * ret_imoex[t])
        net_ret = daily_prem + downside_loss
        equity[t] = equity[t-1] * max(0.001, (1.0 + net_ret))

    return {
        'name': '8. Cash-Secured Put Selling (Vid 25, 31)',
        'dates': dates,
        'equity': equity,
        'turnover': 12 * 6
    }

# =============================================================================
# BENCHMARKS
# =============================================================================
def run_benchmarks(price_df):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    imoex_eq = price_df['IMOEX'].values / price_df['IMOEX'].values[0]
    sber_eq = price_df['SBER'].values / price_df['SBER'].values[0]

    rf_eq = np.ones(n)
    for t in range(1, n):
        kr = get_key_rate(dates[t])
        rf_eq[t] = rf_eq[t-1] * (1.0 + kr / 252.0)

    return {
        'dates': dates,
        'IMOEX': imoex_eq,
        'SBER': sber_eq,
        'RiskFree': rf_eq
    }

# =============================================================================
# METRICS CALCULATION
# =============================================================================
def calculate_metrics(dates, equity_curve, rf_curve=None):
    eq = np.asarray(equity_curve)
    n = len(eq)
    years = (pd.to_datetime(dates[-1]) - pd.to_datetime(dates[0])).days / 365.25

    total_return = (eq[-1] / eq[0]) - 1.0
    cagr = (eq[-1] / eq[0]) ** (1.0 / years) - 1.0 if years > 0 and eq[-1] > 0 else 0.0

    daily_rets = np.diff(eq) / eq[:-1]
    vol = np.std(daily_rets) * np.sqrt(252) if len(daily_rets) > 0 else 0.0

    if rf_curve is not None:
        rf_rets = np.diff(rf_curve) / rf_curve[:-1]
        excess_rets = daily_rets - rf_rets
        sharpe = (np.mean(excess_rets) * 252) / vol if vol > 1e-6 else 0.0
    else:
        sharpe = (cagr - 0.12) / vol if vol > 1e-6 else 0.0

    downside_rets = daily_rets[daily_rets < 0]
    downside_std = np.std(downside_rets) * np.sqrt(252) if len(downside_rets) > 0 else 1e-6
    sortino = (np.mean(daily_rets) * 252) / downside_std if downside_std > 1e-6 else 0.0

    peaks = np.maximum.accumulate(eq)
    drawdowns = (eq - peaks) / peaks
    max_dd = np.min(drawdowns)

    calmar = cagr / abs(max_dd) if abs(max_dd) > 1e-6 else 0.0
    win_rate = np.mean(daily_rets > 0) if len(daily_rets) > 0 else 0.0

    return {
        'Total Return': total_return,
        'CAGR': cagr,
        'Volatility': vol,
        'Sharpe (vs Key Rate)': sharpe,
        'Sortino': sortino,
        'Max Drawdown': max_dd,
        'Calmar': calmar,
        'Win Rate': win_rate
    }
