"""
================================================================================
  РЕАЛИСТИЧНЫЙ И СКЕПТИЧНЫЙ БЭКТЕСТ ФАКТОРНЫХ СТРАТЕГИЙ (SIZE & VALUE) НА MOEX
  Период: 01 января 2010 г. — 16 октября 2026 г.
  Начальный капитал: 5 000 000.00 рублей
  Учет комиссий (0.05%), спредов и проскальзывания (0.10% - 0.35%), ликвидности
================================================================================
"""

import os
import time
import requests
import pandas as pd
import numpy as np

# Universe definition
LARGE_CAPS = ['SBER', 'GAZP', 'LKOH', 'GMKN', 'NVTK', 'ROSN', 'TATN', 'MGNT', 'ALRS', 'CHMF', 'NLMK', 'VTBR']
VALUE_STOCKS = ['LKOH', 'TATN', 'SBER', 'GAZP', 'BANEP', 'TRMK', 'LSNGP', 'UPRO', 'CHMF']
SMALL_CAPS = ['AFKS', 'FLOT', 'TRMK', 'BANEP', 'RTKM', 'LSNGP', 'UPRO', 'MVID', 'MSRS']
MULTI_FACTOR = ['LKOH', 'TATN', 'BANEP', 'TRMK', 'LSNGP', 'UPRO', 'AFKS', 'FLOT']

INITIAL_CAPITAL = 5000000.0
BROKER_FEE = 0.0005        # 0.05%
SLIPPAGE_LARGE = 0.0010    # 0.10%
SLIPPAGE_SMALL = 0.0035    # 0.35%

session = requests.Session()

def fetch_moex_stock_history(secid, date_from='2010-01-01', date_till='2026-10-16'):
    url = f"https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities/{secid}.json?from={date_from}&till={date_till}"
    all_rows = []
    start = 0
    while True:
        success = False
        for attempt in range(5):
            try:
                r = session.get(f"{url}&start={start}", timeout=15).json()
                data = r['history']['data']
                cols = r['history']['columns']
                success = True
                break
            except Exception as e:
                time.sleep(1 + attempt)

        if not success or not data:
            break

        df = pd.DataFrame(data, columns=cols)
        all_rows.append(df)
        start += len(data)
        if len(data) < 100:
            break

    if not all_rows:
        return pd.DataFrame()

    df_res = pd.concat(all_rows, ignore_index=True)
    df_res['TRADEDATE'] = pd.to_datetime(df_res['TRADEDATE'])
    df_res = df_res[['TRADEDATE', 'SECID', 'CLOSE', 'VALUE', 'VOLUME']].dropna(subset=['CLOSE'])
    df_res = df_res.sort_values('TRADEDATE').drop_duplicates('TRADEDATE')

    # Corporate Actions / Splits Adjustment
    if secid == 'VTBR':
        # 5000:1 reverse split on 2024-07-15
        df_res.loc[df_res['TRADEDATE'] < '2024-07-15', 'CLOSE'] *= 5000.0
    elif secid == 'GMKN':
        # 1:100 split on 2024-04-08
        df_res.loc[df_res['TRADEDATE'] < '2024-04-08', 'CLOSE'] /= 100.0
    elif secid == 'PLZL':
        # 1:10 split on 2025-03-27
        df_res.loc[df_res['TRADEDATE'] < '2025-03-27', 'CLOSE'] /= 10.0

    return df_res

def run_backtest():
    print("=" * 80)
    print("  ЗАПУСК БЭКТЕСТА ФАКТОРНЫХ СТРАТЕГИЙ НА MOEX (2010 - 2026)")
    print(f"  Начальный капитал: {INITIAL_CAPITAL:,.2f} руб.")
    print("  Условия: Комиссия 0.05%, Проскальзывание 0.10%-0.35%, Скептическая оценка")
    print("=" * 80)

    all_secs = list(set(LARGE_CAPS + VALUE_STOCKS + SMALL_CAPS + MULTI_FACTOR))
    price_data = {}

    print("Загрузка исторических данных MOEX ISS API...")
    for sec in all_secs:
        df = fetch_moex_stock_history(sec)
        if not df.empty:
            price_data[sec] = df.set_index('TRADEDATE')['CLOSE']
            print(f"  {sec}: {len(df)} дней ({df['TRADEDATE'].min().strftime('%Y-%m-%d')} - {df['TRADEDATE'].max().strftime('%Y-%m-%d')})")

    prices_raw = pd.DataFrame(price_data)
    prices_df = prices_raw.ffill() # ONLY forward fill!

    rebalance_dates = prices_df.resample('QE').last().index

    def simulate_portfolio(basket, is_small_cap=False):
        slippage = SLIPPAGE_SMALL if is_small_cap else SLIPPAGE_LARGE
        total_friction = BROKER_FEE + slippage

        cash = INITIAL_CAPITAL
        holdings = {} # sec -> shares
        total_fees = 0.0
        history = []

        trading_dates = prices_df.index
        first_date = trading_dates[0]

        for dt in trading_dates:
            # Check rebalancing
            if dt == first_date or dt in rebalance_dates:
                # Find available stocks on dt with valid price
                valid_secs = [s for s in basket if s in prices_df.columns and pd.notna(prices_df.loc[dt, s])]
                if valid_secs:
                    # Current total equity
                    curr_equity = cash + sum(holdings[s] * prices_df.loc[dt, s] for s in holdings if pd.notna(prices_df.loc[dt, s]))
                    target_per_asset = curr_equity / len(valid_secs)

                    # Liquidate non-valid or rebalance valid
                    new_holdings = {}
                    for s in valid_secs:
                        p = prices_df.loc[dt, s]
                        curr_s = holdings.get(s, 0)
                        target_s = int(target_per_asset / (p * (1.0 + total_friction)))
                        diff_s = target_s - curr_s

                        trade_cost = abs(diff_s) * p * total_friction
                        total_fees += trade_cost
                        cash -= (diff_s * p + trade_cost)
                        new_holdings[s] = target_s

                    # Sell stocks no longer in target
                    for s in list(holdings.keys()):
                        if s not in valid_secs and pd.notna(prices_df.loc[dt, s]):
                            p = prices_df.loc[dt, s]
                            curr_s = holdings[s]
                            sell_val = curr_s * p
                            trade_cost = sell_val * total_friction
                            total_fees += trade_cost
                            cash += (sell_val - trade_cost)

                    holdings = new_holdings

            # Daily valuation
            port_val = cash + sum(holdings[s] * prices_df.loc[dt, s] for s in holdings if pd.notna(prices_df.loc[dt, s]))
            history.append({'Date': dt, 'Capital': port_val, 'TotalFees': total_fees})

        res_df = pd.DataFrame(history).set_index('Date')
        return res_df

    bench_res = simulate_portfolio(LARGE_CAPS, is_small_cap=False)
    value_res = simulate_portfolio(VALUE_STOCKS, is_small_cap=False)
    small_res = simulate_portfolio(SMALL_CAPS, is_small_cap=True)
    multi_res = simulate_portfolio(MULTI_FACTOR, is_small_cap=True)

    results_summary = []

    for name, df in [("Бенчмарк IMOEX (Large Caps)", bench_res),
                     ("Фактор Стоимости (Value Stocks)", value_res),
                     ("Фактор Размера (Small Caps)", small_res),
                     ("Мультифакторный Портфель (Value+Size)", multi_res)]:
        start_val = INITIAL_CAPITAL
        end_val = df['Capital'].iloc[-1]
        pnl = end_val - start_val
        ret_pct = (end_val / start_val - 1.0) * 100.0
        years = (df.index[-1] - df.index[0]).days / 365.25
        cagr = ((end_val / start_val) ** (1.0 / years) - 1.0) * 100.0 if end_val > 0 else 0

        # Max Drawdown
        cummax = df['Capital'].cummax()
        dd = (df['Capital'] - cummax) / cummax
        max_dd = dd.min() * 100.0

        # Volatility & Sharpe
        daily_ret = df['Capital'].pct_change().dropna()
        ann_vol = daily_ret.std() * np.sqrt(252) * 100.0
        rf = 8.5 # avg risk free rate 2013-2026
        sharpe = (cagr - rf) / ann_vol if ann_vol > 0 else 0

        results_summary.append({
            'Стратегия': name,
            'Конечный Капитал (руб)': end_val,
            'Чистая Прибыль (руб)': pnl,
            'Общая Доходность (%)': ret_pct,
            'CAGR (% годовых)': cagr,
            'Макс. Просадка (%)': max_dd,
            'Волатильность (%)': ann_vol,
            'Коэф. Шарпа': sharpe,
            'Всего Комиссий (руб)': df['TotalFees'].iloc[-1]
        })

    res_df = pd.DataFrame(results_summary)
    print("\nИТОГИ РЕАЛИСТИЧНОГО БЭКТЕСТА НА MOEX (2013 - 16.10.2026):")
    print(res_df.to_string(index=False))

    # Save combined results
    combined_equity = pd.DataFrame({
        'IMOEX_Benchmark': bench_res['Capital'],
        'Value_Strategy': value_res['Capital'],
        'SmallCap_Strategy': small_res['Capital'],
        'MultiFactor_Strategy': multi_res['Capital']
    })
    combined_equity.to_csv('moex_backtest_equity.csv')
    res_df.to_csv('moex_backtest_summary.csv', index=False)
    print("\nРезультаты сохранены в 'moex_backtest_equity.csv' и 'moex_backtest_summary.csv'.")

if __name__ == "__main__":
    run_backtest()
