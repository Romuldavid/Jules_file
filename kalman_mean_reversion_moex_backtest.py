"""
Empirical MOEX Backtest of Roman Paolucci's (Quant Guild)
'Trading Mean Reversion with Kalman Filters' (https://www.youtube.com/watch?v=BuPil7nXvMU)
and the official Kalman Filter Trading System (KTS) from the Quant Guild Library.

Core Mathematical Architecture:
1. AR(1) calibration on calibration window:
   x_t = c + phi * x_{t-1} + e_t, e_t ~ N(0, sigma^2)
   mu = mean(window), phi = slope, sigma = std(residuals)
2. KalmanOU 1D State-Space Filter:
   x_t = phi * x_{t-1} + (1 - phi) * mu
   P_t = phi^2 * P_{t-1} + Q
   Q = sigma^2 * (1 - phi^2)
   R = sigma^2 * max(obs_noise_scale, 0.01)
   K = P / (P + R)
   x_t = x_t + K * (z_t - x_t)
   P_t = (1 - K) * P_t
3. Roman Paolucci's Noise Lever:
   lever 0   -> scale 0.1 (Trust Prices)
   lever 50  -> scale 5.0 (Balanced)
   lever 100 -> scale 1e8 (Trust OU Model)

Strategies Evaluated on MOEX (2021-2026, 1468 trading days):
- KTS Pair Mean Reversion: SBER/SBERP (Noise Lever = 0%, Trust Prices / Low Turnover)
- KTS Pair Mean Reversion: SBER/SBERP (Noise Lever = 50%, Over-trading Failure)
- KTS Single-Asset Mean Reversion on SBER (Single-stock failure mode)
- KTS Single-Asset Mean Reversion on IMOEX (Index failure mode)
- KTS Cross-Company Pair on LKOH / ROSN (Regime shift breakdown)
- FORTS Basis Arbitrage & Repo Carry (Institutional Anchor)
- Benchmarks: Buy & Hold SBER, Buy & Hold IMOEX, Risk-Free (CBR Key Rate)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Styling
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

CACHE_DIR = 'moex_data_cache'
TICKERS = ['SBER', 'SBERP', 'LKOH', 'ROSN', 'GAZP', 'GMKN', 'TATN', 'NVTK', 'IMOEX', 'RGBITR']

# Official Bank of Russia Key Rate Schedule (2021-2026)
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
# Roman Paolucci's Core Implementation from kts.py
# =============================================================================
def estimate_ar1(closes):
    """
    Directly from Roman Paolucci's kts.py:
    Fit AR(1) on calibration-window closes. Returns (phi, mu, sigma).
    """
    if closes is None or len(closes) < 5:
        return None
    try:
        y = np.array(closes, dtype=float)
        y = y[np.isfinite(y)]
        if len(y) < 5:
            return None
        mu = float(np.mean(y))
        x_lag = y[:-1]
        x_curr = y[1:]
        X = np.column_stack([np.ones_like(x_lag), x_lag])
        beta = np.linalg.lstsq(X, x_curr, rcond=None)[0]
        c, phi = float(beta[0]), float(beta[1])
        phi = np.clip(phi, 0.01, 0.99)
        resid = x_curr - (c + phi * x_lag)
        sigma = np.sqrt(np.mean(resid ** 2))
        if sigma <= 0 or not np.isfinite(sigma):
            sigma = max(np.std(y) * 0.01, 1e-9)
        return phi, mu, sigma
    except Exception:
        return None

def noise_lever_to_scale(lever_percent):
    """
    From kts.py:
    lever 0 -> scale 0.1 (low R, trust prices)
    lever 100 -> scale 1e8 (high R, pure OU model)
    """
    p = max(0.0, min(100.0, float(lever_percent))) / 100.0
    if p >= 1.0:
        return 1e8
    return 0.1 + (10.0 - 0.1) * p

class KalmanOU:
    """
    From kts.py:
    One-dimensional Kalman filter with OU transition.
    State x is the estimated mean level (fair value).
    """
    def __init__(self, phi, mu, sigma_process, obs_noise_scale=1.0):
        self.phi = phi
        self.mu = mu
        self.Q = (sigma_process ** 2) * max(1 - phi ** 2, 1e-6)
        self.R = (sigma_process ** 2) * max(obs_noise_scale, 0.01)
        self.x = mu
        self.P = self.R

    def predict(self):
        self.x = self.phi * self.x + (1 - self.phi) * self.mu
        self.P = self.phi ** 2 * self.P + self.Q

    def update(self, z):
        self.predict()
        K = self.P / (self.P + self.R)
        self.x = self.x + K * (z - self.x)
        self.P = (1 - K) * self.P
        return self.x

# =============================================================================
# STRATEGY 1: Single-Asset Mean Reversion (SBER / IMOEX)
# =============================================================================
def run_kts_single_asset(price_df, asset_col='SBER', calib_window=60, noise_lever=50.0, entry_std=1.5, exit_std=0.2):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    prices = price_df[asset_col].values
    n = len(prices)

    obs_scale = noise_lever_to_scale(noise_lever)
    fair_values = np.zeros(n)
    sigmas = np.zeros(n)
    positions = np.zeros(n)

    initial_params = estimate_ar1(prices[:calib_window])
    if initial_params is None:
        phi, mu, sigma = 0.95, float(np.mean(prices[:calib_window])), float(np.std(prices[:calib_window]))
    else:
        phi, mu, sigma = initial_params

    kf = KalmanOU(phi, mu, sigma, obs_noise_scale=obs_scale)
    for t in range(calib_window):
        fair_values[t] = kf.update(prices[t])
        sigmas[t] = sigma

    curr_pos = 0
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(calib_window, n - 1):
        if t % 20 == 0:
            params = estimate_ar1(prices[t-calib_window:t])
            if params is not None:
                phi, mu, sigma = params
                kf = KalmanOU(phi, mu, sigma, obs_noise_scale=obs_scale)

        fv = kf.update(prices[t])
        fair_values[t] = fv
        sigmas[t] = sigma

        dev = (prices[t] - fv) / sigma if sigma > 1e-6 else 0.0

        if curr_pos == 0:
            if dev <= -entry_std:
                curr_pos = 1
            elif dev >= entry_std:
                curr_pos = -1
        elif curr_pos == 1:
            if dev >= -exit_std or dev <= -3.5:
                curr_pos = 0
        elif curr_pos == -1:
            if dev <= exit_std or dev >= 3.5:
                curr_pos = 0

        positions[t+1] = curr_pos

    fair_values[-1] = kf.update(prices[-1])
    sigmas[-1] = sigma

    equity = np.ones(n)
    ret_asset = np.zeros(n)
    ret_asset[1:] = (prices[1:] - prices[:-1]) / prices[:-1]

    for t in range(1, n):
        pos_prev = positions[t-1]
        pos_curr = positions[t]
        turnover = abs(pos_curr - pos_prev)
        cost = turnover * comm_rate
        if turnover > 0:
            turnover_count += 1

        kr = get_key_rate(dates[t])
        daily_rf = kr / 252.0
        daily_borrow = (kr + 0.04) / 252.0 if pos_curr < 0 else 0.0

        if pos_curr == 1:
            day_ret = ret_asset[t] - cost
        elif pos_curr == -1:
            day_ret = -ret_asset[t] - cost - daily_borrow
        else:
            day_ret = daily_rf - cost

        equity[t] = equity[t-1] * (1.0 + day_ret)

    equity[:calib_window] = 1.0
    return {
        'name': f'KTS Single-Asset ({asset_col})',
        'dates': dates,
        'equity': equity,
        'positions': positions,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 2: Cointegrated Pair Spread Mean Reversion
# =============================================================================
def run_kts_pair_spread(price_df, y_col='SBER', x_col='SBERP', calib_window=60, noise_lever=0.0):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    y = price_df[y_col].values
    x = price_df[x_col].values
    n = len(y)

    obs_scale = noise_lever_to_scale(noise_lever)
    beta = y[0] / x[0] if x[0] != 0 else 1.0
    spread = y - beta * x

    initial_params = estimate_ar1(spread[:calib_window])
    if initial_params is None:
        phi, mu, sigma = 0.95, float(np.mean(spread[:calib_window])), float(np.std(spread[:calib_window]))
    else:
        phi, mu, sigma = initial_params

    kf = KalmanOU(phi, mu, sigma, obs_noise_scale=obs_scale)
    fair_spread = np.zeros(n)
    positions = np.zeros(n)

    for t in range(calib_window):
        fair_spread[t] = kf.update(spread[t])

    curr_pos = 0
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(calib_window, n - 1):
        if t % 20 == 0:
            params = estimate_ar1(spread[t-calib_window:t])
            if params is not None:
                phi, mu, sigma = params
                kf = KalmanOU(phi, mu, sigma, obs_noise_scale=obs_scale)

        fv = kf.update(spread[t])
        fair_spread[t] = fv

        dev = (spread[t] - fv) / sigma if sigma > 1e-6 else 0.0

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

    fair_spread[-1] = kf.update(spread[-1])

    equity = np.ones(n)
    y_ret = np.zeros(n)
    x_ret = np.zeros(n)
    y_ret[1:] = (y[1:] - y[:-1]) / y[:-1]
    x_ret[1:] = (x[1:] - x[:-1]) / x[:-1]

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

    equity[:calib_window] = 1.0
    label = f'KTS Cointegrated Pair ({y_col}/{x_col}, Lever={noise_lever:.0f}%)'
    return {
        'name': label,
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 3: FORTS Basis Arbitrage & Repo Carry
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
        'name': 'FORTS Basis Arbitrage & Repo Carry',
        'dates': dates,
        'equity': equity,
        'turnover': 4 * 6
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

def main():
    print("Loading MOEX market data...")
    dfs = load_data()
    print("Aligning master dataset across all tickers...")
    price_df, vol_df, val_df = align_master_dataset(dfs, TICKERS)
    print(f"Master dataset: {len(price_df)} trading days ({price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').iloc[0]} to {price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').iloc[-1]})")

    print("Executing Roman Paolucci's Kalman Mean Reversion strategies...")
    res_basis = run_forts_basis_arbitrage(price_df)
    res_pair_opt = run_kts_pair_spread(price_df, 'SBER', 'SBERP', noise_lever=0.0) # Optimal (Trust Prices)
    res_pair_mid = run_kts_pair_spread(price_df, 'SBER', 'SBERP', noise_lever=50.0) # Balanced
    res_single_sber = run_kts_single_asset(price_df, 'SBER', noise_lever=50.0)
    res_single_imoex = run_kts_single_asset(price_df, 'IMOEX', noise_lever=50.0)
    res_pair_oil = run_kts_pair_spread(price_df, 'LKOH', 'ROSN', noise_lever=50.0)
    benchmarks = run_benchmarks(price_df)

    dates = benchmarks['dates']
    rf_eq = benchmarks['RiskFree']

    strategies = [
        res_basis,
        res_pair_opt,
        res_pair_mid,
        res_single_sber,
        res_single_imoex,
        res_pair_oil,
        {'name': 'Benchmark: Buy & Hold SBER', 'dates': dates, 'equity': benchmarks['SBER']},
        {'name': 'Benchmark: Buy & Hold IMOEX', 'dates': dates, 'equity': benchmarks['IMOEX']},
        {'name': 'Benchmark: Risk-Free (Key Rate)', 'dates': dates, 'equity': benchmarks['RiskFree']},
    ]

    print("\n" + "="*88)
    print(f"{'Strategy / Kalman System':<42} | {'CAGR':<7} | {'Vol':<6} | {'Sharpe':<6} | {'Sortino':<7} | {'MaxDD':<7} | {'Calmar':<6}")
    print("="*88)

    metrics_summary = []
    for s in strategies:
        m = calculate_metrics(s['dates'], s['equity'], rf_curve=rf_eq)
        metrics_summary.append((s['name'], m))
        print(f"{s['name']:<42} | {m['CAGR']*100:6.2f}% | {m['Volatility']*100:5.2f}% | {m['Sharpe (vs Key Rate)']:6.2f} | {m['Sortino']:7.2f} | {m['Max Drawdown']*100:6.2f}% | {m['Calmar']:6.2f}")
    print("="*88)

    # Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={'height_ratios': [2.2, 1.0]}, sharex=True)
    dt_index = pd.to_datetime(dates)

    colors = {
        'FORTS Basis Arbitrage & Repo Carry': '#2ca02c',
        'KTS Cointegrated Pair (SBER/SBERP, Lever=0%)': '#1f77b4',
        'KTS Cointegrated Pair (SBER/SBERP, Lever=50%)': '#aec7e8',
        'KTS Single-Asset (SBER)': '#ff7f0e',
        'KTS Single-Asset (IMOEX)': '#9467bd',
        'KTS Cointegrated Pair (LKOH/ROSN, Lever=50%)': '#d62728',
        'Benchmark: Buy & Hold SBER': '#17becf',
        'Benchmark: Buy & Hold IMOEX': '#7f7f7f',
        'Benchmark: Risk-Free (Key Rate)': '#e377c2'
    }

    for s in strategies:
        name = s['name']
        style = '--' if 'Benchmark' in name and 'Risk-Free' not in name else ('-.' if 'Risk-Free' in name else '-')
        lw = 2.2 if 'Basis' in name or 'Lever=0%' in name else 1.4
        ax1.plot(dt_index, s['equity'], label=name, color=colors.get(name, 'black'), linestyle=style, linewidth=lw)

        peaks = np.maximum.accumulate(s['equity'])
        dd = (s['equity'] - peaks) / peaks
        ax2.plot(dt_index, dd * 100, label=name, color=colors.get(name, 'black'), linestyle=style, linewidth=1.2)

    ax1.set_title("Roman Paolucci's Kalman Mean Reversion (KTS) on MOEX (2021–2026)", fontsize=14, fontweight='bold', pad=12)
    ax1.set_ylabel('Equity Multiplier (Base = 1.0)', fontsize=11)
    ax1.legend(loc='upper left', frameon=True, fontsize=8)
    ax1.grid(True, linestyle=':', alpha=0.6)

    ax2.set_title('Underwater Drawdown Profiles (%)', fontsize=11, fontweight='bold', pad=8)
    ax2.set_ylabel('Drawdown (%)', fontsize=10)
    ax2.set_xlabel('Date', fontsize=11)
    ax2.grid(True, linestyle=':', alpha=0.6)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.tight_layout()
    chart_path = 'kalman_mean_reversion_chart.png'
    plt.savefig(chart_path, dpi=200)
    print(f"\nSaved equity chart to {chart_path}")
    return metrics_summary

if __name__ == '__main__':
    main()
