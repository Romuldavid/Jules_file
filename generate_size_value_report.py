"""
================================================================================
  ГЕНЕРАТОР ОТЧЕТА И ГРАФИКА: ЭФФЕКТ РАЗМЕРА И АНОМАЛИЯ СТОИМОСТИ
  (Size and Value Anomalies - Fama-French Factor Model)
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
# 2. ГЕНЕРАЦИЯ ГРАФИКА
# ------------------------------------------------------------------------------
def generate_chart(output_path="size_value_chart.png"):
    np.random.seed(42)
    dates = pd.date_range(start="2000-01-01", end="2025-12-31", freq="ME")
    n = len(dates)

    # Симуляция гипотетических доходностей факторов на долгосрочном горизонте
    mkt_ret = np.random.normal(0.007, 0.045, n)    # ~8.4% годовых
    smb_ret = np.random.normal(0.0025, 0.025, n)   # ~3.0% премия за размер
    hml_ret = np.random.normal(0.0035, 0.030, n)   # ~4.2% премия за стоимость

    val_ret = mkt_ret + 0.6 * hml_ret + 0.2 * smb_ret
    small_ret = mkt_ret + 0.8 * smb_ret + 0.1 * hml_ret

    mkt_cum = np.cumprod(1 + mkt_ret) * 100
    val_cum = np.cumprod(1 + val_ret) * 100
    small_cum = np.cumprod(1 + small_ret) * 100
    hml_cum = np.cumprod(1 + hml_ret) * 100
    smb_cum = np.cumprod(1 + smb_ret) * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), gridspec_kw={'height_ratios': [2.2, 1]})

    # Верхний график: Кумулятивная динамика портфелей
    ax1.plot(dates, mkt_cum, label="Рыночный индекс (Market Cap Weighted)", color="#1f77b4", linewidth=2)
    ax1.plot(dates, val_cum, label="Портфель Стоимости (Value Factor / HML)", color="#2ca02c", linewidth=2)
    ax1.plot(dates, small_cum, label="Портфель Малой Капитализации (Small Caps / SMB)", color="#ff7f0e", linewidth=2)

    ax1.set_title("Долгосрочная Кумулятивная Доходность Факторных Портфелей (2000–2025 гг.)", fontsize=12, fontweight='bold', pad=10)
    ax1.set_ylabel("Индекс роста капитала (Базис = 100)", fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left", fontsize=9, frameon=True)
    ax1.set_yscale('log')

    # Нижний график: Избыточные факторные премии (HML и SMB)
    ax2.plot(dates, hml_cum, label="Чистый фактор HML (Value - Growth Long/Short)", color="#d62728", linewidth=1.5)
    ax2.plot(dates, smb_cum, label="Чистый фактор SMB (Small - Big Long/Short)", color="#9467bd", linewidth=1.5)
    ax2.axhline(100, color="black", linestyle=":", alpha=0.7)

    ax2.set_title("Динамика Чистых Факторных Премий (Long/Short Market Neutral)", fontsize=10, fontweight='bold', pad=6)
    ax2.set_ylabel("Базис = 100", fontsize=9)
    ax2.set_xlabel("Дата", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper left", fontsize=8, frameon=True)

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
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F2C59'),
        alignment=0,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName=MAIN_FONT,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName=BOLD_FONT,
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#0F2C59'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName=MAIN_FONT,
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=6
    )

    table_header_style = ParagraphStyle(
        'TableHeader_Custom',
        parent=styles['Normal'],
        fontName=BOLD_FONT,
        fontSize=9.5,
        leading=13.5,
        textColor=colors.white
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=styles['Normal'],
        fontName=MAIN_FONT,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1A202C')
    )

    story = []

    # Заголовок
    story.append(Paragraph("Эффект Размерa и Аномалия Стоимости (Size and Value Anomalies)", title_style))
    story.append(Paragraph("Академические истоки, математическая модель Фама-Френча и квантитативная практика", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0F2C59'), spaceAfter=12))

    # Краткий обзор / Callout
    summary_html = "<b>Ключевые авторы:</b> Юджин Фама и Кеннет Френч (1992–1993 гг.).<br/>" \
                   "<b>Суть:</b> Акции компаний с малой капитализацией (Small Caps) и недооцененные акции с низким $P/B$ (Value) " \
                   "системно обгоняют широкий рынок на долгой дистанции.<br/>" \
                   "<b>Практика:</b> Клифф Аснесс и фонд AQR Capital Management ($100 млрд AUM) построили бизнес на эксплуатации фактора Value."

    callout_data = [[Paragraph(summary_html, callout_style)]]
    callout_table = Table(callout_data, colWidths=[520])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EDF2F7')),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 10))

    # Раздел 1
    story.append(Paragraph("1. История Открытия и Трехфакторная Модель Фама-Френча", h1_style))
    p1 = "В 1992–1993 годах Юджин Фама и Кеннет Френч опубликовали фундаментальные работы, доказавшие несостоятельность " \
         "однофакторной модели CAPM. Они ввели Трехфакторную модель, учитывающую рыночный риск, размер и стоимость:"
    story.append(Paragraph(p1, body_style))

    formula_text = "<b>R<sub>it</sub> - R<sub>ft</sub> = α<sub>i</sub> + β<sub>i</sub>(R<sub>mt</sub> - R<sub>ft</sub>) + s<sub>i</sub> · SMB<sub>t</sub> + h<sub>i</sub> · HML<sub>t</sub> + ε<sub>it</sub></b>"
    story.append(Spacer(1, 4))
    story.append(Paragraph(formula_text, ParagraphStyle('Formula', parent=body_style, fontName=BOLD_FONT, alignment=1, fontSize=10)))
    story.append(Spacer(1, 6))

    # Таблица с описанием факторов
    table_data = [
        [Paragraph("<b>Фактор</b>", table_header_style), Paragraph("<b>Название</b>", table_header_style), Paragraph("<b>Описание и Расчет</b>", table_header_style)],
        [Paragraph("<b>SMB</b>", body_style), Paragraph("Small Minus Big", body_style), Paragraph("Премия за риск компании малой капитализации против гигантов.", body_style)],
        [Paragraph("<b>HML</b>", body_style), Paragraph("High Minus Low", body_style), Paragraph("Избыточная доходность недооцененных акций (высокий B/M) против акций роста.", body_style)],
        [Paragraph("<b>Rm - Rf</b>", body_style), Paragraph("Market Premium", body_style), Paragraph("Премия за риск инвестирования в широкий рынок акций.", body_style)]
    ]
    t_factors = Table(table_data, colWidths=[60, 110, 350])
    t_factors.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2C59')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_factors)
    story.append(Spacer(1, 10))

    # Раздел 2: Почему это работает
    story.append(Paragraph("2. Экономическое и Поведенческое Обоснование", h1_style))
    story.append(Paragraph("• <b>Премия за риск (Risk-Based):</b> Инвесторы требуют повышенную доходность за удержание акций компаний с ограниченной ликвидностью (Small Caps) или компаний, переживающих временный финансовый стресс (Value).", bullet_style))
    story.append(Paragraph("• <b>Поведенческая психология (Behavioral):</b> Рынок склонен слишком сильно переоценивать «хайповые» акции роста (Growth), создавая систематическую недооценку в устойчивых или застойных секторах.", bullet_style))
    story.append(Spacer(1, 10))

    # Раздел 3: График
    story.append(Paragraph("3. Эмпирическая Симуляция Факторных Доходностей", h1_style))
    if os.path.exists(chart_image):
        story.append(Image(chart_image, width=520, height=280))
    story.append(Spacer(1, 10))

    # Раздел 4: AQR и Практика на MOEX
    story.append(Paragraph("4. Квант-Фонды и Специфика на Российском Рынке (MOEX)", h1_style))
    story.append(Paragraph("• <b>AQR Capital Management:</b> Фонд Клиффа Аснесса ($100 млрд AUM) построен на комбинировании факторов Value и Momentum в рыночно-нейтральных портфелях.", bullet_style))
    story.append(Paragraph("• <b>Применение на MOEX:</b> На российском рынке фактор Value измеряется через P/B и ROE (для банков) и EV/EBITDA и FCF Yield (для нефтегаза). Фактор Size требует отсева неликвидных ценных бумаг из-за высокого спреда.", bullet_style))
    story.append(Paragraph("• <b>Value Traps & Quality:</b> Современный подход дополняет Value фактором Quality (Profitability), отсеивающим компании с высокой долговой нагрузкой.", bullet_style))

    # Сборка документа
    doc.build(story)
    print(f"PDF успешно создан: {pdf_filename}")

if __name__ == "__main__":
    chart_path = generate_chart()
    generate_pdf_report(chart_image=chart_path)
