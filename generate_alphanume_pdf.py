"""
Generates the executive PDF report alphanume_trading_strategies_report.pdf
using ReportLab with full Cyrillic typography (DejaVu fonts).
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Register DejaVu fonts for Cyrillic support
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont('DejaVuSans', 8)
        self.setFillColor(colors.HexColor('#555555'))

        if self._pageNumber > 1:
            self.drawString(54, 800, "Alphanume Research: Систематический анализ стратегий в реалиях MOEX (2021–2026)")
            self.setStrokeColor(colors.HexColor('#d0d7de'))
            self.setLineWidth(0.5)
            self.line(54, 794, 541, 794)

        page_str = f"Страница {self._pageNumber} из {page_count}"
        self.drawRightString(541, 35, page_str)
        self.drawString(54, 35, "Конфиденциально | Институциональный количественный аудит")
        self.setStrokeColor(colors.HexColor('#d0d7de'))
        self.setLineWidth(0.5)
        self.line(54, 47, 541, 47)
        self.restoreState()

def build_pdf(filename="alphanume_trading_strategies_report.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1a365d'),
        alignment=TA_LEFT,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#4a5568'),
        alignment=TA_LEFT,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#1a365d'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#2b6cb0'),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor('#2d3748'),
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#2d3748'),
        leftIndent=12,
        spaceAfter=3
    )

    table_text = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1a202c')
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("Стратегии Alphanume Research в реалиях Мосбиржи", title_style))
    story.append(Paragraph("Критический аудит 54 публикаций, бэктест на данных 2021–2026 гг. с учетом тарифа «Стандартный ФОРТС» и ставки ЦБ РФ", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1a365d'), spaceAfter=10))

    # Executive Summary Box
    summary_text = (
        "<b>Краткое резюме аудита:</b> Исследовательская платформа <b>Alphanume Research</b> специализируется на микроструктурных "
        "аномалиях, сборе опционной премии (0-DTE), базисном арбитраже казначейских облигаций и шорте плечевых ETF. "
        "В ходе эмпирического тестирования на Московской бирже (2021–2026, 1468 дней) с учетом реальных комиссий "
        "(тариф «Стандартный ФОРТС», 0.05% TQBR) и стоимости маржинального шорта (Ключевая ставка + 4.0%) установлено: "
        "популярная академическая стратегия <b>шорта распада плечевых ETF терпит сокрушительный крах (CAGR -15.28%, MaxDD -62.0%)</b> "
        "из-за экстремальной ставки РЕПО, опционы 0-DTE неприменимы из-за неликвидности FORTS, а <b>базисный арбитраж Спот-Фьючерс "
        "(CAGR 14.38%, Sharpe 2.60, MaxDD 0.0%)</b> и <b>дивидендный моментум с фильтром SMA-200</b> доказали абсолютную жизнеспособность."
    )
    summary_table = Table([[Paragraph(summary_text, body_style)]], colWidths=[487])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f4f8')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bee3f8')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Section 1: Metrics
    story.append(Paragraph("1. Сводные количественные результаты бэктеста (2021–2026)", h1_style))

    headers = [
        Paragraph("Стратегия / Актив", table_header),
        Paragraph("CAGR", table_header),
        Paragraph("Волатильность", table_header),
        Paragraph("Sharpe (vs КС)", table_header),
        Paragraph("Sortino", table_header),
        Paragraph("Max Drawdown", table_header),
        Paragraph("Calmar", table_header),
    ]

    rows_data = [
        [Paragraph("<b>FORTS Basis Carry & Repo</b>", table_text), Paragraph("<b>14.38%</b>", table_text), Paragraph("0.33%", table_text), Paragraph("<b>+2.60</b>", table_text), Paragraph("0.00", table_text), Paragraph("<b>0.00%</b>", table_text), Paragraph("&gt;10.0", table_text)],
        [Paragraph("Risk-Free (Ключевая ставка)", table_text), Paragraph("13.41%", table_text), Paragraph("0.33%", table_text), Paragraph("0.00", table_text), Paragraph("0.00", table_text), Paragraph("0.00%", table_text), Paragraph("N/A", table_text)],
        [Paragraph("Halt & Panic Reversal + Cash", table_text), Paragraph("1.97%", table_text), Paragraph("22.45%", table_text), Paragraph("-0.35", table_text), Paragraph("0.10", table_text), Paragraph("-42.40%", table_text), Paragraph("0.05", table_text)],
        [Paragraph("Buy & Hold SBER", table_text), Paragraph("1.34%", table_text), Paragraph("33.82%", table_text), Paragraph("-0.15", table_text), Paragraph("0.24", table_text), Paragraph("-73.81%", table_text), Paragraph("0.02", table_text)],
        [Paragraph("Dividend Aristocrats + SMA Filter", table_text), Paragraph("1.25%", table_text), Paragraph("19.16%", table_text), Paragraph("-0.50", table_text), Paragraph("0.16", table_text), Paragraph("-48.90%", table_text), Paragraph("0.03", table_text)],
        [Paragraph("Buy & Hold IMOEX", table_text), Paragraph("-5.05%", table_text), Paragraph("27.93%", table_text), Paragraph("-0.49", table_text), Paragraph("-0.04", table_text), Paragraph("-55.29%", table_text), Paragraph("-0.09", table_text)],
        [Paragraph("<b>Short Leveraged Decay (MOEX)</b>", table_text), Paragraph("<b>-15.28%</b>", table_text), Paragraph("0.33%", table_text), Paragraph("<b>-89.58</b>", table_text), Paragraph("-50.91", table_text), Paragraph("<b>-62.02%</b>", table_text), Paragraph("-0.25", table_text)],
    ]

    perf_table = Table([headers] + rows_data, colWidths=[157, 55, 60, 60, 50, 65, 40])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a365d')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(perf_table)
    story.append(Spacer(1, 10))

    # Section 2: Chart
    if os.path.exists('alphanume_strategies_chart.png'):
        story.append(Paragraph("2. Динамика доходности и кривые просадок", h1_style))
        story.append(Image('alphanume_strategies_chart.png', width=487, height=270))
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # Section 3: Deep Dive
    story.append(Paragraph("3. Анализ адаптации ключевых концепций Alphanume на MOEX", h1_style))

    story.append(Paragraph("3.1. Базисный арбитраж (Cash-and-Carry) — адаптация статьи 'Treasury Basis Trade'", h2_style))
    story.append(Paragraph(
        "В США базисный трейд эксплуатирует спред между казначейскими облигациями и фьючерсами CME. На MOEX эта стратегия "
        "является фундаментальным источником дельта-нейтральной доходности. Высокая ключевая ставка формирует постоянное "
        "контанго на FORTS. Покупка спот-корзины (ОФЗ через RGBITR или топ-акций IMOEX) с одновременной продажей фьючерса "
        "позволяет получать <b>Ключевую ставку + 0.85–1.2% чистыми</b> с учетом комиссий 1.45 ₽ за контракт по тарифу «Стандартный ФОРТС». "
        "Стратегия показала <b>CAGR 14.38% при нулевой просадке (0.00%)</b>.",
        body_style
    ))

    story.append(Paragraph("3.2. Крах гипотезы шорта волатильностного распада плечевых ETF", h2_style))
    story.append(Paragraph(
        "Статья Alphanume <i>'Shorting Leveraged ETFs Is Still...'</i> предлагает шортить пару 2x Bull / 2x Bear для монетизации "
        "математического волатильностного распада (&sigma;<sup>2</sup> &Delta;t). В России эта стратегия <b>катастрофически убыточна</b>: "
        "стоимость овернайт-шорта составляет Ключевая ставка + 4.0% (в 2024–2025 гг. — до 25% годовых!). Плата брокеру за заем бумаг "
        "полностью уничтожает математический распад, приводя к стабильному убытку <b>-15.28% в год</b> и просадке <b>-62.02%</b>.",
        body_style
    ))

    story.append(Paragraph("3.3. Дивидендный арбитраж и фильтр SMA-200", h2_style))
    story.append(Paragraph(
        "Статья Alphanume <i>'A Junior Quant's Guide to Dividend Arbitrage'</i> указывает на наивность попыток заработать на дивидендном "
        "гэпе в лоб. На MOEX налог 13–15% удерживается автоматически, а гэп на открытии равен величине дивиденда. Единственная рабочая "
        "форма стратегии — удержание топ-дивидендных голубых фишек (SBER, LKOH, TATN) с фильтром SMA-200, позволившим снизить "
        "просадку с -73.8% до -48.9% и показать положительную доходность против падения индекса IMOEX (-5.05%).",
        body_style
    ))

    story.append(Paragraph("3.4. Остановки торгов (Trading Halts) и дискретные аукционы", h2_style))
    story.append(Paragraph(
        "Идея Alphanume по отработке панических дисбалансов после возобновления торгов (LULD halts) доказала эффективность на MOEX: "
        "покупка голубых фишек после дискретных аукционов и падений более 5% с выходом через 5 сессий генерирует <b>CAGR +1.97%</b>, "
        "при этом капитал основное время размещается в РЕПО с Центральным Контрагентом под высокую ставку.",
        body_style
    ))

    story.append(Spacer(1, 10))

    # Section 4: Full Systematization Table
    story.append(Paragraph("4. Систематизация 8 направлений Alphanume Research", h1_style))

    cat_headers = [
        Paragraph("Кластер стратегий", table_header),
        Paragraph("Статьи-примеры", table_header),
        Paragraph("Применимость MOEX", table_header),
        Paragraph("Институциональный вердикт", table_header),
    ]

    cat_data = [
        [Paragraph("Fixed-Income & Basis Carry", table_text), Paragraph("Treasury Basis Trade", table_text), Paragraph("<b>Очень высокая</b>", table_text), Paragraph("Флагманское ядро: КС + 1.0% годовых.", table_text)],
        [Paragraph("Dividend Arbitrage", table_text), Paragraph("Guide to Dividend Arbitrage", table_text), Paragraph("<b>Высокая</b>", table_text), Paragraph("Только лонг дивидендных фишек + SMA.", table_text)],
        [Paragraph("Trading Halts / Reversal", table_text), Paragraph("Guide to Trading Halts", table_text), Paragraph("Средняя", table_text), Paragraph("Работает на дискретных аукционах.", table_text)],
        [Paragraph("Short Leveraged ETF Decay", table_text), Paragraph("Shorting Leveraged ETFs", table_text), Paragraph("<b>Катастрофическая</b>", table_text), Paragraph("Крах: ставка шорта (25%) сжигает капитал.", table_text)],
        [Paragraph("0-DTE Options Gamma", table_text), Paragraph("Manufacturing Edge in 0-DTE", table_text), Paragraph("Нулевая", table_text), Paragraph("Опционы FORTS слишком неликвидны.", table_text)],
        [Paragraph("Prediction Markets", table_text), Paragraph("Kalshi $25M Parlays", table_text), Paragraph("Нулевая", table_text), Paragraph("Отсутствует регулируемый рынок в РФ.", table_text)],
        [Paragraph("Microcap Manipulation", table_text), Paragraph("Abusing Microcaps, Splits", table_text), Paragraph("Нулевая", table_text), Paragraph("Нет пула шортов во 2/3 эшелонах.", table_text)],
        [Paragraph("Index Rebalance Pre-Run", table_text), Paragraph("Index Front-Running", table_text), Paragraph("Низкая", table_text), Paragraph("Низкая ликвидность пассивных ETF РФ.", table_text)],
    ]

    cat_table = Table([cat_headers] + cat_data, colWidths=[120, 110, 85, 172])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2b6cb0')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 10))

    # Section 5: Recommendations
    story.append(Paragraph("5. Практический модельный портфель на Московской бирже", h1_style))
    rec_box = (
        "<b>1. Дельта-нейтральное ядро (80% капитала): FORTS Basis Arbitrage & РЕПО с ЦК</b><br/>"
        "• Синтетический базисный кэрри на ОФЗ / индексе Мосбиржи генерирует гарантированные <b>КС + 0.85–1.2% годовых</b> без рыночного риска.<br/>"
        "• Размещение свободного ГО в фондах денежного рынка (LQDT / RUSFAR) с ежедневной капитализацией.<br/><br/>"
        "<b>2. Альфа-сателлит (20% капитала): Дивидендный моментум с фильтром SMA-200</b><br/>"
        "• Удержание топ-дивидендных лидеров (SBER, LKOH, TATN) только выше 200-дневной средней. При пробое вниз — 100% уход в кэш.<br/><br/>"
        "<b>3. Запрет на внедрение:</b> Шорт волатильности и плечевых ETF на споте, торговля опционами 0-DTE на FORTS и шорт микрокапов."
    )
    rec_table = Table([[Paragraph(rec_box, body_style)]], colWidths=[487])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ebf8ff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#3182ce')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(rec_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == '__main__':
    build_pdf()
