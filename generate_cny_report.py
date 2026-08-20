import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Set style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

# 1. CBR Key Rates
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

print("Downloading MOEX data...")
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

spot_fee_rate = 0.00025  # 0.025%
forts_fee_per_contract = 2.50 # 2.50 RUB

trade_log = []
equity_curve = [{'date': '2023-01-01', 'capital': initial_capital, 'cbr_rate': 7.50}]

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
    equity_curve.append({'date': exit_date, 'capital': capital, 'cbr_rate': cbr_rate_period})

df_trades = pd.DataFrame(trade_log)
df_equity = pd.DataFrame(equity_curve)
df_equity['date'] = pd.to_datetime(df_equity['date'])

# Generate matplotlib plots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

# Chart 1: Equity Growth
ax1.plot(df_equity['date'], df_equity['capital'], marker='o', color='#1A365D', linewidth=2.5, label='Депозит (Капитал, руб.)')
ax1.set_title('Рост капитала 1,000,000 руб. на Валютном Cash-and-Carry MOEX (2023-2025)', fontsize=12, fontweight='bold', pad=10)
ax1.set_ylabel('Капитал (руб.)', fontsize=10)
ax1.yaxis.set_major_formatter('{x:,.0f}')
ax1.grid(True, linestyle='--', alpha=0.5)

for _, row in df_trades.iterrows():
    ax1.annotate(f"{row['annual_return_pct']:.1f}% APR\n({row['action'][:6]})", 
                 (pd.to_datetime(row['exit_date']), row['capital_end']),
                 textcoords="offset points", xytext=(0,10), ha='center', fontsize=7, fontweight='bold', color='#2B6CB0')

# Chart 2: CBR Rate
ax2.step(df_equity['date'], df_equity['cbr_rate'], where='post', color='#C53030', linewidth=2, label='Ключевая ставка ЦБ РФ (%)')
ax2.set_ylabel('Ставка ЦБ (%)', fontsize=10)
ax2.set_xlabel('Дата', fontsize=10)
ax2.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
chart_path = "cny_cash_carry_chart.png"
plt.savefig(chart_path, dpi=200)
plt.close()
print(f"Chart saved to {chart_path}")

# Build PDF report
def build_cny_pdf():
    pdf_filename = "cny_cash_carry_report.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=landscape(letter),
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    
    regular_font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    bold_font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    if os.path.exists(regular_font_path):
        pdfmetrics.registerFont(TTFont("LiberationSans", regular_font_path))
    if os.path.exists(bold_font_path):
        pdfmetrics.registerFont(TTFont("LiberationSans-Bold", bold_font_path))
        
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        name='TitleStyle', parent=styles['Heading1'],
        fontName='LiberationSans-Bold' if os.path.exists(bold_font_path) else 'Helvetica-Bold',
        fontSize=16, leading=20, textColor=colors.HexColor("#1A365D"), spaceAfter=5, alignment=1
    )
    
    subtitle_style = ParagraphStyle(
        name='SubtitleStyle', parent=styles['Normal'],
        fontName='LiberationSans' if os.path.exists(regular_font_path) else 'Helvetica',
        fontSize=9, leading=12, textColor=colors.HexColor("#4A5568"), spaceAfter=15, alignment=1
    )
    
    header_style = ParagraphStyle(
        name='HeaderStyle', parent=styles['Normal'],
        fontName='LiberationSans-Bold' if os.path.exists(bold_font_path) else 'Helvetica-Bold',
        fontSize=8, leading=10, textColor=colors.white, alignment=1
    )
    
    cell_style = ParagraphStyle(
        name='CellStyle', parent=styles['Normal'],
        fontName='LiberationSans' if os.path.exists(regular_font_path) else 'Helvetica',
        fontSize=7.5, leading=9.5, textColor=colors.HexColor("#2D3748")
    )
    
    cell_bold_style = ParagraphStyle(
        name='CellBoldStyle', parent=styles['Normal'],
        fontName='LiberationSans-Bold' if os.path.exists(bold_font_path) else 'Helvetica-Bold',
        fontSize=7.5, leading=9.5, textColor=colors.HexColor("#1A365D")
    )

    story = []
    story.append(Paragraph("Детальный отчет: Валютный Cash-and-Carry на Московской бирже (MOEX)", title_style))
    story.append(Paragraph("Бэктест по реальным ценам спот CNYRUB_TOM и фьючерсов CR (01.01.2023 – 2025 гг.). Начальный капитал: 1,000,000 руб. Тариф FORTS + Спот.", subtitle_style))
    
    # Add Image
    story.append(Image(chart_path, width=700, height=220))
    story.append(Spacer(1, 10))
    
    # Table of Trades
    headers = [
        Paragraph("<b>Контракт</b>", header_style),
        Paragraph("<b>Стратегия</b>", header_style),
        Paragraph("<b>Вход / Выход</b>", header_style),
        Paragraph("<b>Спот / Фьюч (Вход)</b>", header_style),
        Paragraph("<b>Контанго</b>", header_style),
        Paragraph("<b>Комиссия</b>", header_style),
        Paragraph("<b>Чистый PnL (руб)</b>", header_style),
        Paragraph("<b>Доходность (APR)</b>", header_style),
        Paragraph("<b>Капитал (руб)</b>", header_style),
        Paragraph("<b>Ставка ЦБ</b>", header_style)
    ]
    
    data = [headers]
    
    for _, row in df_trades.iterrows():
        data.append([
            Paragraph(f"<b>{row['contract']}</b><br/>{row['name']}", cell_style),
            Paragraph(row['action'], cell_style),
            Paragraph(f"{row['entry_date']}<br/>{row['exit_date']}", cell_style),
            Paragraph(f"{row['spot_entry']:.4f}<br/>{row['fut_entry']:.4f}", cell_style),
            Paragraph(f"{row['contango_pct']:.2f}%", cell_style),
            Paragraph(f"{row['fees_rub']:,.0f} ₽", cell_style),
            Paragraph(f"<b>+{row['net_pnl_rub']:,.0f} ₽</b>" if row['net_pnl_rub'] >= 0 else f"{row['net_pnl_rub']:,.0f} ₽", cell_bold_style),
            Paragraph(f"<b>{row['annual_return_pct']:.2f}%</b>", cell_bold_style),
            Paragraph(f"{row['capital_end']:,.0f} ₽", cell_style),
            Paragraph(f"{row['cbr_rate']:.1f}%", cell_style)
        ])
        
    col_widths = [65, 85, 75, 75, 55, 55, 75, 75, 80, 55]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])
    ]))
    
    story.append(t)
    doc.build(story)
    print("PDF cny_cash_carry_report.pdf generated successfully.")

build_cny_pdf()
