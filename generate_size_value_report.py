"""
================================================================================
  ГЕНЕРАТОР ОТЧЕТА И ГРАФИКА: ЭФФЕКТ РАЗМЕРА И АНОМАЛИЯ СТОИМОСТИ
  (Size and Value Anomalies - Fama-French Factor Model & Real MOEX Backtest)
================================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ------------------------------------------------------------------------------
# 1. ШРИФТЫ С ПОДДЕРЖКОЙ КИРИЛЛИЦЫ
# ------------------------------------------------------------------------------
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('DejaVuSans', FONT_PATH))
    MAIN_FONT = 'DejaVuSans'
else:
    MAIN_FONT = 'Helvetica'

if os.path.exists(FONT_BOLD_PATH):
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', FONT_BOLD_PATH))
    BOLD_FONT = 'DejaVuSans-Bold'
else:
    BOLD_FONT = MAIN_FONT

# ------------------------------------------------------------------------------
# 2. ГЕНЕРАЦИЯ ГРАФИКА НА РЕАЛЬНЫХ ДАННЫХ MOEX
# ------------------------------------------------------------------------------
def generate_chart(output_path="size_value_chart.png"):
    csv_equity = "moex_backtest_equity.csv"
    if os.path.exists(csv_equity):
        df_eq = pd.read_csv(csv_equity, index_col=0, parse_dates=True)
    else:
        from moex_size_value_backtest import run_backtest
        run_backtest()
        df_eq = pd.read_csv(csv_equity, index_col=0, parse_dates=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), gridspec_kw={'height_ratios': [2.2, 1]})

    # Верхний график: Кумулятивная динамика капитала на MOEX (млн руб.)
    ax1.plot(df_eq.index, df_eq['IMOEX_Benchmark'] / 1e6, label="Бенчмарк IMOEX (Large Caps)", color="#1f77b4", linewidth=2)
    ax1.plot(df_eq.index, df_eq['Value_Strategy'] / 1e6, label="Фактор Стоимости (Value Stocks)", color="#2ca02c", linewidth=2.5)
    ax1.plot(df_eq.index, df_eq['SmallCap_Strategy'] / 1e6, label="Фактор Размера (Small Caps)", color="#d62728", linewidth=2)
    ax1.plot(df_eq.index, df_eq['MultiFactor_Strategy'] / 1e6, label="Мультифактор (Value + Size)", color="#9467bd", linewidth=2, linestyle='--')

    ax1.set_title("Динамика Капитала Стратегий на MOEX (2013–2026 гг., Нач. капитал = 5 млн руб.)", fontsize=12, fontweight='bold', pad=10)
    ax1.set_ylabel("Капитал (млн руб.)", fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left", fontsize=9, frameon=True)

    # Нижний график: Просадки (Drawdowns)
    dd_bench = (df_eq['IMOEX_Benchmark'] - df_eq['IMOEX_Benchmark'].cummax()) / df_eq['IMOEX_Benchmark'].cummax() * 100
    dd_val = (df_eq['Value_Strategy'] - df_eq['Value_Strategy'].cummax()) / df_eq['Value_Strategy'].cummax() * 100
    dd_small = (df_eq['SmallCap_Strategy'] - df_eq['SmallCap_Strategy'].cummax()) / df_eq['SmallCap_Strategy'].cummax() * 100

    ax2.plot(df_eq.index, dd_bench, label="Просадка IMOEX (%)", color="#1f77b4", linewidth=1.2, alpha=0.7)
    ax2.plot(df_eq.index, dd_val, label="Просадка Value (%)", color="#2ca02c", linewidth=1.2, alpha=0.8)
    ax2.plot(df_eq.index, dd_small, label="Просадка Small Caps (%)", color="#d62728", linewidth=1.2, alpha=0.7)

    ax2.set_title("Профили Просадок Стратегий (Drawdowns %)", fontsize=10, fontweight='bold', pad=6)
    ax2.set_ylabel("Просадка (%)", fontsize=9)
    ax2.set_xlabel("Дата", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="lower left", fontsize=8, frameon=True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    return output_path

# ------------------------------------------------------------------------------
# 3. ГЕНЕРАЦИЯ PDF-ОТЧЕТА
# ------------------------------------------------------------------------------
def generate_pdf_report(pdf_filename="size_and_value_anomalies.pdf", chart_image="size_value_chart.png"):
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName=BOLD_FONT,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F2C59'),
        alignment=0,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName=MAIN_FONT,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName=BOLD_FONT,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0F2C59'),
        spaceBefore=10,
        spaceAfter=5
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName=MAIN_FONT,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=5
    )

    table_header_style = ParagraphStyle(
        'TableHeader_Custom',
        parent=styles['Normal'],
        fontName=BOLD_FONT,
        fontSize=8.5,
        leading=11.5,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell_Custom',
        parent=styles['Normal'],
        fontName=MAIN_FONT,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#2D3748')
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=styles['Normal'],
        fontName=MAIN_FONT,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1A202C')
    )

    story = []

    # Заголовок
    story.append(Paragraph("Эффект Размерa и Аномалия Стоимости (Size and Value Anomalies)", title_style))
    story.append(Paragraph("Академическая теория, Модель Фама-Френча, Практика AQR и Бэктест на MOEX (2013–2026 гг.)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0F2C59'), spaceAfter=10))

    # Краткий обзор / Callout
    summary_html = "<b>Авторы открытий:</b> Юджин Фама и Кеннет Френч (1992–1993 гг., Нобелевская премия 2013 г.).<br/>" \
                   "<b>Суть:</b> Акции с низкой капитализацией (Small Caps) и недооцененные акции с низким $P/B$ (Value) системно превосходят рынок.<br/>" \
                   "<b>Использование фондами:</b> Клифф Аснесс и AQR Capital Management ($100 млрд AUM) построили квант-индустрию на фаторах Value и Momentum.<br/>" \
                   "<b>Эмпирика на MOEX:</b> Реалистичный бэктест на MOEX ISS API подтвердил огромную премию фактора Value (+201.2% vs +79.3% IMOEX)."

    callout_data = [[Paragraph(summary_html, callout_style)]]
    callout_table = Table(callout_data, colWidths=[520])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EDF2F7')),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 8))

    # Раздел 1: Теория Фама-Френча
    story.append(Paragraph("1. Теория и Модель Фама-Френча", h1_style))
    p1 = "В 1992–1993 гг. Юджин Фама и Кеннет Френч заменили модель CAPM на 3-факторную регрессионную модель:"
    story.append(Paragraph(p1, body_style))

    formula_text = "<b>R<sub>it</sub> - R<sub>ft</sub> = α<sub>i</sub> + β<sub>i</sub>(R<sub>mt</sub> - R<sub>ft</sub>) + s<sub>i</sub> · SMB<sub>t</sub> + h<sub>i</sub> · HML<sub>t</sub> + ε<sub>it</sub></b>"
    story.append(Spacer(1, 3))
    story.append(Paragraph(formula_text, ParagraphStyle('Formula', parent=body_style, fontName=BOLD_FONT, alignment=1, fontSize=9.5)))
    story.append(Spacer(1, 6))

    # Раздел 2: Бэктест на MOEX Таблица
    story.append(Paragraph("2. Результаты Реалистичного Бэктеста на MOEX (2013–2026 гг.)", h1_style))

    csv_summary = "moex_backtest_summary.csv"
    if os.path.exists(csv_summary):
        df_sum = pd.read_csv(csv_summary)
    else:
        df_sum = pd.DataFrame()

    table_data = [
        [
            Paragraph("<b>Стратегия</b>", table_header_style),
            Paragraph("<b>Капитал (руб)</b>", table_header_style),
            Paragraph("<b>Доходность</b>", table_header_style),
            Paragraph("<b>CAGR</b>", table_header_style),
            Paragraph("<b>Макс. Просадка</b>", table_header_style),
            Paragraph("<b>Волатильность</b>", table_header_style),
            Paragraph("<b>Шарп</b>", table_header_style)
        ]
    ]

    for _, row in df_sum.iterrows():
        table_data.append([
            Paragraph(f"<b>{row['Стратегия']}</b>", table_cell_style),
            Paragraph(f"{row['Конечный Капитал (руб)']:,.0f}", table_cell_style),
            Paragraph(f"{row['Общая Доходность (%)']:+.1f}%", table_cell_style),
            Paragraph(f"{row['CAGR (% годовых)']:.2f}%", table_cell_style),
            Paragraph(f"{row['Макс. Просадка (%)']:.1f}%", table_cell_style),
            Paragraph(f"{row['Волатильность (%)']:.1f}%", table_cell_style),
            Paragraph(f"{row['Коэф. Шарпа']:.2f}", table_cell_style)
        ])

    t_summary = Table(table_data, colWidths=[140, 75, 60, 55, 70, 65, 55])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2C59')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 8))

    # Раздел 3: График
    story.append(Paragraph("3. Динамика Капитала и Просадок на MOEX", h1_style))
    if os.path.exists(chart_image):
        story.append(Image(chart_image, width=520, height=270))
    story.append(Spacer(1, 8))

    # Раздел 4: Анализ и Выводы
    story.append(Paragraph("4. Выводы по Российскому Рынку Акций", h1_style))
    story.append(Paragraph("• <b>Аномалия Стоимости (Value) работает отлично:</b> Недооцененные дивидендные акции (+201.2%) опередили IMOEX (+79.3%) более чем в 2.5 раза за счет высокой дивидендной доходности и устойчивого бизнеса.", bullet_style))
    story.append(Paragraph("• <b>Чистый фактор Размера (Small Caps) неэффективен:</b> Акции малых компаний уступили рынку (+28.2%) из-за высоких спредов, комиссии за ребалансировку и отсутствия институционального спроса во 2-3 эшелонах.", bullet_style))
    story.append(Paragraph("• <b>Рекомендация:</b> Наиболее эффективная квант-стратегия на MOEX — сочетание Value и Quality/Dividend во 2 эшелоне и крупных фишках.", bullet_style))

    # Сборка документа
    doc.build(story)
    print(f"PDF успешно создан: {pdf_filename}")

if __name__ == "__main__":
    chart_path = generate_chart()
    generate_pdf_report(chart_image=chart_path)
