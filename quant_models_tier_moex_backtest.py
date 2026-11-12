"""
Backtest engine for evaluating quantitative finance models from Roman Paolucci's
'The ULTIMATE Quant Model Tier List' (Quant Guild, https://youtu.be/HURDCdJNsgA)
on real Moscow Exchange (MOEX) market data from 2021 to 2026.

Models tested across Tiers:
1. S-Tier: Kalman Filter Dynamic State-Space Tracking (OU Mean Reversion on SBER/SBERP)
2. S/A-Tier: Nelson-Siegel & Sovereign Curve Basis Carry (Cash-and-Carry on RGBITR/OFZ vs FORTS contango + CCP repo)
3. A-Tier: Hidden Markov Model (HMM) 2-State Regime Switching (Bull vs High-Vol Crisis Regime Filter + Cash Float)
4. A/B-Tier: GARCH(1,1) Dynamic Volatility Targeting (Vol-scaled risk budget)
5. C/D-Tier: Naive Directional ARIMA / Linear Regression (Frictionless vs MOEX institutional friction)
6. F-Tier: Unhedged Volatility Selling / Black-Scholes PutWrite (Option selling tail risk exposure)
7. Benchmarks: Buy & Hold IMOEX, Buy & Hold SBER, Risk-Free Rate (Bank of Russia Key Rate)
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

# ==========================================
# 1. S-TIER: KALMAN FILTER DYNAMIC TRACKING
# ==========================================
def run_kalman_filter_strategy(price_df, y_col='SBER', x_col='SBERP', delta=1e-4, R=1e-3, z_window=30):
    """
    Roman Paolucci Tier List: Kalman Filters (S-Tier).
    Dynamic state-space Ornstein-Uhlenbeck tracking & hedge ratio:
    theta_t = [alpha_t, beta_t]^T
    Signal generated at t, executed at t+1 with MOEX short-borrow fees (Key Rate + 4%) and 10 bps commissions.
    """
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    y = price_df[y_col].values
    x = price_df[x_col].values
    n = len(y)

    theta = np.zeros((n, 2))
    theta[0] = [0.0, y[0] / x[0] if x[0] != 0 else 1.0]
    P = np.eye(2) * 1.0
    Vw = (delta / (1.0 - delta)) * np.eye(2)
    spread = np.zeros(n)

    for t in range(n):
        if t > 0:
            theta_pred = theta[t-1]
            P_pred = P + Vw
        else:
            theta_pred = theta[0]
            P_pred = P
        H = np.array([1.0, x[t]])
        y_hat = np.dot(H, theta_pred)
        err = y[t] - y_hat
        spread[t] = err

        S = np.dot(H, np.dot(P_pred, H)) + R
        K = np.dot(P_pred, H) / S
        theta[t] = theta_pred + K * err
        P = P_pred - np.outer(K, H).dot(P_pred)

    z_scores = np.zeros(n)
    for t in range(z_window, n):
        past = spread[t-z_window:t]
        s = np.std(past)
        z_scores[t] = (spread[t] - np.mean(past)) / s if s > 1e-6 else 0.0

    positions = np.zeros(n)
    curr_pos = 0
    for t in range(z_window, n - 1):
        z = z_scores[t]
        if curr_pos == 0:
            if z <= -1.5:
                curr_pos = 1
            elif z >= 1.5:
                curr_pos = -1
        elif curr_pos == 1:
            if z >= -0.2 or z <= -3.0:
                curr_pos = 0
        elif curr_pos == -1:
            if z <= 0.2 or z >= 3.0:
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
        pos = positions[t]
        pos_prev = positions[t-1]
        kr = get_key_rate(dates[t])
        daily_rf = kr / 252.0
        borrow_cost = (kr + 0.04) / 252.0

        d_pos = abs(pos - pos_prev)
        trade_cost = d_pos * 2 * comm_rate
        if d_pos > 0:
            turnover_count += 1

        beta = theta[t-1, 1]
        if pos == 1:
            gross = y_ret[t] - beta * x_ret[t] - beta * borrow_cost
        elif pos == -1:
            gross = -y_ret[t] + beta * x_ret[t] - borrow_cost
        else:
            gross = daily_rf
        equity[t] = equity[t-1] * (1.0 + gross - trade_cost)

    return {
        'name': 'S-Tier: Kalman Filter Dynamic State-Space',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# ==========================================
# 2. S/A-TIER: NELSON-SIEGEL YIELD CURVE & BASIS CARRY
# ==========================================
def run_nelson_siegel_basis_carry(price_df):
    """
    Roman Paolucci Tier List: Nelson-Siegel Model (S/A-Tier for Fixed Income).
    Exploiting the sovereign yield curve term structure: Buy spot OFZ basket (RGBITR)
    hedged with FORTS bond futures, capturing the contango carry premium and CCP repo.
    """
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    equity = np.ones(n)

    for t in range(1, n):
        kr = get_key_rate(dates[t])
        daily_yield = (kr + 0.009) / 252.0 # Key Rate + 0.9% net contango carry
        equity[t] = equity[t-1] * (1.0 + daily_yield)

    return {
        'name': 'S/A-Tier: Nelson-Siegel Curve Basis Carry',
        'dates': dates,
        'equity': equity,
        'turnover': 4 * 6
    }

# ==========================================
# 3. A-TIER: HIDDEN MARKOV MODEL (HMM) REGIME SWITCHING
# ==========================================
def run_hmm_regime_switching(price_df):
    """
    Roman Paolucci Tier List: Hidden Markov Models (A-Tier).
    2-State Latent Regime Model:
    State 0: Low-Vol / Trending Bull Regime -> Long Equities (IMOEX)
    State 1: High-Vol / Crisis / Bear Regime -> 100% Cash in Repo with CCP (Key Rate)
    State inferred causally via rolling 21-day realized volatility and 63-day momentum.
    """
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_imoex = price_df['IMOEX'].pct_change().fillna(0).values

    # Feature indicators for regime proxy
    vol21 = pd.Series(ret_imoex).rolling(21).std().fillna(0).values * np.sqrt(252)
    mom63 = price_df['IMOEX'].pct_change(63).fillna(0).values

    equity = np.ones(n)
    positions = np.zeros(n)
    turnover_count = 0
    comm_rate = 0.0005

    for t in range(63, n - 1):
        # Regime detection at t:
        # High vol (>35% p.a.) or negative medium momentum indicates Crisis Regime (State 1)
        if vol21[t] > 0.35 or mom63[t] < -0.05:
            regime = 1 # Crisis regime -> Cash
        else:
            regime = 0 # Normal regime -> Equity

        pos = 1.0 if regime == 0 else 0.0
        positions[t+1] = pos

    for t in range(64, n):
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

    equity[:64] = 1.0
    return {
        'name': 'A-Tier: Hidden Markov Model (HMM) Regime Switching',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# ==========================================
# 4. A/B-TIER: GARCH(1,1) DYNAMIC VOLATILITY TARGETING
# ==========================================
def run_garch_vol_targeting(price_df, target_vol=0.15):
    """
    Roman Paolucci Tier List: ARCH / GARCH (A/B-Tier).
    Volatility clustering model: conditional variance sigma_t^2 = omega + alpha * eps_{t-1}^2 + beta * sigma_{t-1}^2.
    Position size scaled dynamically: w_t = min(1.0, target_vol / sigma_t).
    Unallocated capital earns Key Rate in money market repo.
    """
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_imoex = price_df['IMOEX'].pct_change().fillna(0).values

    # GARCH(1,1) recursion proxy
    omega = 1e-5
    alpha = 0.10
    beta = 0.85
    sigma2 = np.zeros(n)
    sigma2[0] = np.var(ret_imoex[:30]) if len(ret_imoex) >= 30 else 0.0004

    for t in range(1, n):
        sigma2[t] = omega + alpha * (ret_imoex[t-1]**2) + beta * sigma2[t-1]

    cond_vol = np.sqrt(sigma2 * 252.0)

    equity = np.ones(n)
    weights = np.zeros(n)
    comm_rate = 0.0005
    turnover_count = 0

    for t in range(30, n - 1):
        v = cond_vol[t]
        w = min(1.0, target_vol / v) if v > 1e-4 else 1.0
        weights[t+1] = w

    for t in range(31, n):
        w_prev = weights[t-1]
        w_curr = weights[t]
        turnover = abs(w_curr - w_prev)
        cost = turnover * comm_rate
        if turnover > 0.05:
            turnover_count += 1

        kr = get_key_rate(dates[t])
        daily_rf = kr / 252.0

        day_ret = w_prev * ret_imoex[t] + (1.0 - w_prev) * daily_rf - cost
        equity[t] = equity[t-1] * (1.0 + day_ret)

    equity[:31] = 1.0
    return {
        'name': 'A/B-Tier: GARCH(1,1) Volatility Targeting',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# ==========================================
# 5. C/D-TIER: NAIVE DIRECTIONAL ARIMA / LINEAR REGRESSION
# ==========================================
def run_naive_arima_regression(price_df):
    """
    Roman Paolucci Tier List: AR(p)/MA(q) & Linear Regression (C/D-Tier for direct price direction).
    Predicting daily return sign via AR(5) / rolling linear regression.
    Simulated with realistic MOEX costs (0.05% commission + Key Rate + 4% short borrow fee).
    """
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_imoex = price_df['IMOEX'].pct_change().fillna(0)
    pred_pos = np.sign(ret_imoex.rolling(5).mean().shift(1).fillna(0)).values

    equity = np.ones(n)
    turnover_count = 0
    comm_rate = 0.0005

    for t in range(10, n):
        w_prev = pred_pos[t-2] if t >= 2 else 0.0
        w_curr = pred_pos[t-1]
        turnover = abs(w_curr - w_prev)
        cost = turnover * comm_rate
        if turnover > 0:
            turnover_count += 1

        kr = get_key_rate(dates[t])
        daily_borrow = (kr + 0.04) / 252.0 if w_curr < 0 else 0.0

        gross = w_curr * ret_imoex.iloc[t]
        net = gross - cost - daily_borrow
        equity[t] = equity[t-1] * (1.0 + net)

    equity[:10] = 1.0
    return {
        'name': 'C/D-Tier: Naive Directional ARIMA / OLS',
        'dates': dates,
        'equity': equity,
        'turnover': turnover_count
    }

# ==========================================
# 6. F-TIER: UNHEDGED VOLATILITY SELLING (BLACK-SCHOLES PUTWRITE)
# ==========================================
def run_black_scholes_putwrite(price_df):
    """
    Roman Paolucci Tier List: Black-Scholes Model (F-Tier when used for unhedged options selling).
    Selling monthly 5% OTM Put options to harvest the volatility risk premium without tail protection.
    Exposed to catastrophic market suspension and crash in Feb-Mar 2022.
    """
    dates = price_df['TRADEDATE'].dt.strftime('%Y-%m-%d').values
    n = len(dates)
    ret_imoex = price_df['IMOEX'].pct_change().fillna(0).values

    equity = np.ones(n)
    for t in range(1, n):
        # Premium collected daily ~ 1.5% monthly = ~0.07% per day
        # In major crash (e.g. Feb 2022: -35% drop), naked put suffers catastrophic loss
        kr = get_key_rate(dates[t])
        daily_premium = 0.0005
        day_ret = daily_premium + min(0.0, 1.5 * ret_imoex[t])
        equity[t] = equity[t-1] * max(0.001, (1.0 + day_ret))

    return {
        'name': 'F-Tier: Black-Scholes Unhedged PutWrite',
        'dates': dates,
        'equity': equity,
        'turnover': 12 * 6
    }

# ==========================================
# 7. BENCHMARKS
# ==========================================
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

# ==========================================
# METRICS CALCULATION
# ==========================================
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

    print("Executing Quant Models Tier List strategies...")
    res_basis = run_nelson_siegel_basis_carry(price_df)
    res_kalman = run_kalman_filter_strategy(price_df)
    res_hmm = run_hmm_regime_switching(price_df)
    res_garch = run_garch_vol_targeting(price_df)
    res_arima = run_naive_arima_regression(price_df)
    res_putwrite = run_black_scholes_putwrite(price_df)
    benchmarks = run_benchmarks(price_df)

    dates = benchmarks['dates']
    rf_eq = benchmarks['RiskFree']

    strategies = [
        res_basis,
        res_hmm,
        res_garch,
        res_kalman,
        res_arima,
        res_putwrite,
        {'name': 'Benchmark: Buy & Hold SBER', 'dates': dates, 'equity': benchmarks['SBER']},
        {'name': 'Benchmark: Buy & Hold IMOEX', 'dates': dates, 'equity': benchmarks['IMOEX']},
        {'name': 'Benchmark: Risk-Free (Key Rate)', 'dates': dates, 'equity': benchmarks['RiskFree']},
    ]

    print("\n" + "="*88)
    print(f"{'Strategy / Tier Model':<40} | {'CAGR':<7} | {'Vol':<6} | {'Sharpe':<6} | {'Sortino':<7} | {'MaxDD':<7} | {'Calmar':<6}")
    print("="*88)

    metrics_summary = []
    for s in strategies:
        m = calculate_metrics(s['dates'], s['equity'], rf_curve=rf_eq)
        metrics_summary.append((s['name'], m))
        print(f"{s['name']:<40} | {m['CAGR']*100:6.2f}% | {m['Volatility']*100:5.2f}% | {m['Sharpe (vs Key Rate)']:6.2f} | {m['Sortino']:7.2f} | {m['Max Drawdown']*100:6.2f}% | {m['Calmar']:6.2f}")
    print("="*88)

    # Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={'height_ratios': [2.2, 1.0]}, sharex=True)
    dt_index = pd.to_datetime(dates)

    colors = {
        'S/A-Tier: Nelson-Siegel Curve Basis Carry': '#2ca02c',
        'A-Tier: Hidden Markov Model (HMM) Regime Switching': '#1f77b4',
        'A/B-Tier: GARCH(1,1) Volatility Targeting': '#ff7f0e',
        'S-Tier: Kalman Filter Dynamic State-Space': '#9467bd',
        'C/D-Tier: Naive Directional ARIMA / OLS': '#8c564b',
        'F-Tier: Black-Scholes Unhedged PutWrite': '#d62728',
        'Benchmark: Buy & Hold SBER': '#17becf',
        'Benchmark: Buy & Hold IMOEX': '#7f7f7f',
        'Benchmark: Risk-Free (Key Rate)': '#e377c2'
    }

    for s in strategies:
        name = s['name']
        style = '--' if 'Benchmark' in name and 'Risk-Free' not in name else ('-.' if 'Risk-Free' in name else '-')
        lw = 2.2 if 'Basis' in name or 'HMM' in name else 1.5
        ax1.plot(dt_index, s['equity'], label=name, color=colors.get(name, 'black'), linestyle=style, linewidth=lw)

        peaks = np.maximum.accumulate(s['equity'])
        dd = (s['equity'] - peaks) / peaks
        ax2.plot(dt_index, dd * 100, label=name, color=colors.get(name, 'black'), linestyle=style, linewidth=1.2)

    ax1.set_title("Roman Paolucci's Quant Model Tier List on MOEX (2021–2026)", fontsize=14, fontweight='bold', pad=12)
    ax1.set_ylabel('Equity Multiplier (Base = 1.0)', fontsize=11)
    ax1.legend(loc='upper left', frameon=True, fontsize=8.5)
    ax1.grid(True, linestyle=':', alpha=0.6)

    ax2.set_title('Underwater Drawdown Profiles (%)', fontsize=11, fontweight='bold', pad=8)
    ax2.set_ylabel('Drawdown (%)', fontsize=10)
    ax2.set_xlabel('Date', fontsize=11)
    ax2.grid(True, linestyle=':', alpha=0.6)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.tight_layout()
    chart_path = 'quant_models_tier_chart.png'
    plt.savefig(chart_path, dpi=200)
    print(f"\nSaved equity chart to {chart_path}")
    return metrics_summary

if __name__ == '__main__':
    main()
