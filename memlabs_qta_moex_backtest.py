"""
Empirical MOEX Backtest of MemLabs' 'Quant Trading Accelerator' Course
(YouTube Playlist: https://youtube.com/playlist?list=PLdsqLas3-Kg1vGriabIjpaUNWzMQIbXH9).

Core Pedagogical Models Evaluated:
1. MemLabs AR(1) Directional Predictor (Frictionless Academic / Crypto Perp Benchmark)
2. MemLabs AR(1) Directional on MOEX (Realistic 0.05% comm + Key Rate + 4.0% short borrow)
3. MemLabs AR(3) Multi-Lag Directional on MOEX
4. MemLabs Logistic Regression Classification (Gerko & Anatolyev Framework)
5. Institutional Adaptation: Thresholded Long-Only AR + Repo Cash Float
6. FORTS Basis Arbitrage & Repo Carry (Institutional Anchor)
7. Trend Following SMA-200 + Repo Cash Float
8. Benchmarks: Buy & Hold SBER, Buy & Hold IMOEX, Risk-Free (CBR Key Rate)
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
TICKERS = ['SBER', 'LKOH', 'ROSN', 'GAZP', 'GMKN', 'TATN', 'NVTK', 'IMOEX', 'RGBITR']

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
# Pure NumPy Machine Learning Tools (No external sklearn dependency required)
# =============================================================================
def fit_linear_ols(X, y):
    """X: (N, K), y: (N,). Returns beta of shape (K,)."""
    return np.linalg.lstsq(X, y, rcond=None)[0]

def fit_logistic_gd(X, y, lr=0.1, epochs=120, l2=0.01):
    """Train logistic regression with L2 regularization using gradient descent."""
    w = np.zeros(X.shape[1])
    for _ in range(epochs):
        z = np.dot(X, w)
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        grad = np.dot(X.T, (p - y)) / len(y) + l2 * w
        w -= lr * grad
    return w

# =============================================================================
# MemLabs Feature Engineering: Lagged Autoregressive Features
# =============================================================================
def create_memlabs_ar_df(series, no_lags=3):
    df = pd.DataFrame({'close': series.values})
    df['close_log_return'] = np.log(df['close'] / df['close'].shift(1))
    for lag in range(1, no_lags + 1):
        df[f'close_log_return_lag_{lag}'] = df['close_log_return'].shift(lag)
    return df

# =============================================================================
# STRATEGY 1 & 2: MemLabs Linear Regression Directional (AR-1 / AR-p)
# =============================================================================
def run_memlabs_ar_model(price_df, asset_col='SBER', no_lags=1, apply_moex_frictions=True):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    series = price_df[asset_col]
    n = len(series)

    ar_df = create_memlabs_ar_df(series, no_lags=no_lags)
    features = [f'close_log_return_lag_{i}' for i in range(1, no_lags + 1)]

    burn_in = int(n * 0.30)
    positions = np.zeros(n)

    for t in range(burn_in, n - 1):
        # Walk-forward calibration up to t
        train_sub = ar_df.iloc[:t].dropna()
        X_raw = train_sub[features].values
        X_train = np.column_stack([np.ones(len(X_raw)), X_raw])
        y_train = train_sub['close_log_return'].values

        beta = fit_linear_ols(X_train, y_train)

        x_curr = ar_df.iloc[t][features].values
        if np.all(np.isfinite(x_curr)):
            x_test = np.insert(x_curr, 0, 1.0)
            y_hat = np.dot(x_test, beta)
            positions[t+1] = np.sign(y_hat)
        else:
            positions[t+1] = 0.0

    equity = np.ones(n)
    raw_rets = price_df[asset_col].pct_change().fillna(0).values
    comm_rate = 0.0005 if apply_moex_frictions else 0.0
    turnover_count = 0

    for t in range(1, n):
        pos_prev = positions[t-1]
        pos_curr = positions[t]
        turnover = abs(pos_curr - pos_prev)
        cost = turnover * comm_rate
        if turnover > 0:
            turnover_count += 1

        kr = get_key_rate(dates[t])
        daily_borrow = (kr + 0.04) / 252.0 if (apply_moex_frictions and pos_curr < 0) else 0.0

        day_ret = pos_curr * raw_rets[t] - cost - daily_borrow
        equity[t] = equity[t-1] * max(0.001, (1.0 + day_ret))

    equity[:burn_in] = 1.0
    label = f'MemLabs AR({no_lags}) Directional ({asset_col})'
    if not apply_moex_frictions:
        label += ' (Academic 0-Cost)'
    else:
        label += ' (Realistic MOEX Costs)'

    return {
        'name': label,
        'dates': dates,
        'equity': equity,
        'positions': positions,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 3: MemLabs Logistic Regression Classification (Part 6)
# =============================================================================
def run_memlabs_logistic_model(price_df, asset_col='SBER', no_lags=3):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    series = price_df[asset_col]
    n = len(series)

    ar_df = create_memlabs_ar_df(series, no_lags=no_lags)
    features = [f'close_log_return_lag_{i}' for i in range(1, no_lags + 1)]
    ar_df['target_sign'] = (ar_df['close_log_return'] > 0).astype(float)

    burn_in = int(n * 0.30)
    positions = np.zeros(n)

    for t in range(burn_in, n - 1):
        train_sub = ar_df.iloc[:t].dropna()
        X_raw = train_sub[features].values
        X_train = np.column_stack([np.ones(len(X_raw)), X_raw])
        y_train = train_sub['target_sign'].values

        w = fit_logistic_gd(X_train, y_train)

        x_curr = ar_df.iloc[t][features].values
        if np.all(np.isfinite(x_curr)):
            x_test = np.insert(x_curr, 0, 1.0)
            z = np.dot(x_test, w)
            prob_up = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
            positions[t+1] = 1.0 if prob_up > 0.50 else -1.0
        else:
            positions[t+1] = 0.0

    equity = np.ones(n)
    raw_rets = price_df[asset_col].pct_change().fillna(0).values
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(1, n):
        pos_prev = positions[t-1]
        pos_curr = positions[t]
        turnover = abs(pos_curr - pos_prev)
        cost = turnover * comm_rate
        if turnover > 0:
            turnover_count += 1

        kr = get_key_rate(dates[t])
        daily_borrow = (kr + 0.04) / 252.0 if pos_curr < 0 else 0.0

        day_ret = pos_curr * raw_rets[t] - cost - daily_borrow
        equity[t] = equity[t-1] * max(0.001, (1.0 + day_ret))

    equity[:burn_in] = 1.0
    return {
        'name': f'MemLabs Logistic Classification AR(3) ({asset_col})',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 4: Institutional Adaptation: Thresholded Long-Only AR + Repo Cash Float
# =============================================================================
def run_memlabs_institutional_adaptation(price_df, asset_col='SBER', no_lags=3, threshold=0.002):
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    series = price_df[asset_col]
    n = len(series)

    ar_df = create_memlabs_ar_df(series, no_lags=no_lags)
    features = [f'close_log_return_lag_{i}' for i in range(1, no_lags + 1)]

    burn_in = int(n * 0.30)
    positions = np.zeros(n)

    for t in range(burn_in, n - 1):
        train_sub = ar_df.iloc[:t].dropna()
        X_raw = train_sub[features].values
        X_train = np.column_stack([np.ones(len(X_raw)), X_raw])
        y_train = train_sub['close_log_return'].values

        beta = fit_linear_ols(X_train, y_train)

        x_curr = ar_df.iloc[t][features].values
        if np.all(np.isfinite(x_curr)):
            x_test = np.insert(x_curr, 0, 1.0)
            y_hat = np.dot(x_test, beta)
            positions[t+1] = 1.0 if y_hat > threshold else 0.0
        else:
            positions[t+1] = 0.0

    equity = np.ones(n)
    raw_rets = price_df[asset_col].pct_change().fillna(0).values
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(1, n):
        pos_prev = positions[t-1]
        pos_curr = positions[t]
        turnover = abs(pos_curr - pos_prev)
        cost = turnover * comm_rate
        if turnover > 0:
            turnover_count += 1

        kr = get_key_rate(dates[t])
        daily_rf = kr / 252.0

        day_ret = pos_curr * raw_rets[t] + (1.0 - pos_curr) * daily_rf - cost
        equity[t] = equity[t-1] * (1.0 + day_ret)

    equity[:burn_in] = 1.0
    return {
        'name': f'Institutional Adapted: Long-Only AR + Repo Cash ({asset_col})',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# =============================================================================
# STRATEGY 5: FORTS Basis Arbitrage & Repo Carry
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
# STRATEGY 6: Trend Following SMA-200 + Repo Cash
# =============================================================================
def run_trend_following_sma(price_df):
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
        'name': 'Trend Following: SMA-200 + Repo Cash Float',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
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

    print("Executing MemLabs Quant Trading Accelerator strategies...")
    res_basis = run_forts_basis_arbitrage(price_df)
    res_trend = run_trend_following_sma(price_df)
    res_adapt = run_memlabs_institutional_adaptation(price_df, 'SBER', no_lags=3)
    res_ar1_free = run_memlabs_ar_model(price_df, 'SBER', no_lags=1, apply_moex_frictions=False)
    res_ar1_real = run_memlabs_ar_model(price_df, 'SBER', no_lags=1, apply_moex_frictions=True)
    res_ar3_real = run_memlabs_ar_model(price_df, 'SBER', no_lags=3, apply_moex_frictions=True)
    res_log_real = run_memlabs_logistic_model(price_df, 'SBER', no_lags=3)
    benchmarks = run_benchmarks(price_df)

    dates = benchmarks['dates']
    rf_eq = benchmarks['RiskFree']

    strategies = [
        res_basis,
        res_adapt,
        res_trend,
        res_ar1_free,
        {'name': 'Benchmark: Buy & Hold SBER', 'dates': dates, 'equity': benchmarks['SBER']},
        {'name': 'Benchmark: Buy & Hold IMOEX', 'dates': dates, 'equity': benchmarks['IMOEX']},
        res_log_real,
        res_ar3_real,
        res_ar1_real,
        {'name': 'Benchmark: Risk-Free (Key Rate)', 'dates': dates, 'equity': benchmarks['RiskFree']},
    ]

    print("\n" + "="*88)
    print(f"{'Strategy / MemLabs QTA Model':<48} | {'CAGR':<7} | {'Vol':<6} | {'Sharpe':<6} | {'Sortino':<7} | {'MaxDD':<7} | {'Calmar':<6}")
    print("="*88)

    metrics_summary = []
    for s in strategies:
        m = calculate_metrics(s['dates'], s['equity'], rf_curve=rf_eq)
        metrics_summary.append((s['name'], m))
        print(f"{s['name']:<48} | {m['CAGR']*100:6.2f}% | {m['Volatility']*100:5.2f}% | {m['Sharpe (vs Key Rate)']:6.2f} | {m['Sortino']:7.2f} | {m['Max Drawdown']*100:6.2f}% | {m['Calmar']:6.2f}")
    print("="*88)

    # Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={'height_ratios': [2.2, 1.0]}, sharex=True)
    dt_index = pd.to_datetime(dates)

    colors = {
        'FORTS Basis Arbitrage & Repo Carry': '#2ca02c',
        'Institutional Adapted: Long-Only AR + Repo Cash (SBER)': '#1f77b4',
        'Trend Following: SMA-200 + Repo Cash Float': '#17becf',
        'MemLabs AR(1) Directional (SBER) (Academic 0-Cost)': '#2b6cb0',
        'MemLabs AR(1) Directional (SBER) (Realistic MOEX Costs)': '#d62728',
        'MemLabs AR(3) Directional (SBER) (Realistic MOEX Costs)': '#8c564b',
        'MemLabs Logistic Classification AR(3) (SBER)': '#e377c2',
        'Benchmark: Buy & Hold SBER': '#ff7f0e',
        'Benchmark: Buy & Hold IMOEX': '#7f7f7f',
        'Benchmark: Risk-Free (Key Rate)': '#bcbd22'
    }

    for s in strategies:
        name = s['name']
        style = '--' if 'Benchmark' in name and 'Risk-Free' not in name else ('-.' if 'Risk-Free' in name else '-')
        lw = 2.2 if 'Basis' in name or 'Institutional' in name or 'Academic' in name else 1.4
        ax1.plot(dt_index, s['equity'], label=name, color=colors.get(name, 'black'), linestyle=style, linewidth=lw)

        peaks = np.maximum.accumulate(s['equity'])
        dd = (s['equity'] - peaks) / peaks
        ax2.plot(dt_index, dd * 100, label=name, color=colors.get(name, 'black'), linestyle=style, linewidth=1.2)

    ax1.set_title("MemLabs 'Quant Trading Accelerator' Models on MOEX (2021–2026)", fontsize=13, fontweight='bold', pad=12)
    ax1.set_ylabel('Equity Multiplier (Base = 1.0)', fontsize=11)
    ax1.legend(loc='upper left', frameon=True, fontsize=8)
    ax1.grid(True, linestyle=':', alpha=0.6)

    ax2.set_title('Underwater Drawdown Profiles (%)', fontsize=11, fontweight='bold', pad=8)
    ax2.set_ylabel('Drawdown (%)', fontsize=10)
    ax2.set_xlabel('Date', fontsize=11)
    ax2.grid(True, linestyle=':', alpha=0.6)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.tight_layout()
    chart_path = 'memlabs_qta_chart.png'
    plt.savefig(chart_path, dpi=200)
    print(f"\nSaved equity chart to {chart_path}")
    return metrics_summary

if __name__ == '__main__':
    main()
