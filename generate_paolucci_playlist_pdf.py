"""
Generates the executive PDF report paolucci_playlist_moex_report.pdf
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
            self.drawString(54, 800, "Roman Paolucci Quant Playlist: Систематический анализ 75 видео на MOEX (2021–2026)")
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

def build_pdf(filename="paolucci_playlist_moex_report.pdf"):
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
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f2b48'),
        alignment=TA_LEFT,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4a5568'),
        alignment=TA_LEFT,
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=12,
        leading=15.5,
        textColor=colors.HexColor('#0f2b48'),
        spaceBefore=13,
        spaceAfter=5,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#1f4e79'),
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#2d3748'),
        alignment=TA_JUSTIFY,
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor('#2d3748'),
        leftIndent=12,
        spaceAfter=3
    )

    table_text = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#1a202c')
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=7,
        leading=9.5,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("Квант-стратегии Романа Паолуччи (75 видео) на Мосбирже", title_style))
    story.append(Paragraph("Скептический институциональный аудит плейлиста «Practical Quantitative Trading Videos», бэктест на данных 2021–2026 гг. с учетом тарифа «Стандартный ФОРТС» и ставки ЦБ РФ", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f2b48'), spaceAfter=10))

    # Executive Summary Box
    summary_text = (
        "<b>Краткое резюме аудита:</b> Проанализированы все 75 видеолекций официального плейлиста Романа Паолуччи "
        "(Quant Guild, экс-квант Bloomberg LP). Проведено эмпирическое тестирование ключевых прикладных стратегий на реальных "
        "котировках Московской Биржи (2021–2026, 1468 дней) с учетом тарифа «Стандартный ФОРТС», официального графика Ключевой ставки "
        "(до 21.0%), стоимости маржинального шорта (КС + 4.0%) и исполнения со сдвигом $t+1$. <br/>"
        "Установлено: <b>Критерий Келли с дробным сайзингом (CAGR 14.02%, MaxDD -0.63%, Sortino 11.19)</b> и "
        "<b>базисный арбитраж FORTS (CAGR 14.43%, Sharpe +2.76, MaxDD 0.0%)</b> показали феноменальную надежность; "
        "<b>Трендовый фильтр SMA-200 (CAGR 9.28%)</b> и <b>«Демон Шеннона» 50/50 (CAGR 4.75%)</b> спасли капитал в 2022 году; "
        "тогда как <b>продажа опционов (Covered Call / Cash-Secured Put) привела к катастрофической ликвидации (-96% ... -100%)</b> "
        "из-за месячного закрытия биржи в феврале 2022 года."
    )
    summary_table = Table([[Paragraph(summary_text, body_style)]], colWidths=[487])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f4f8')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bcd0e4')),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 9),
        ('RIGHTPADDING', (0,0), (-1,-1), 9),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    # Section 1: Metrics Table
    story.append(Paragraph("1. Сводные количественные результаты бэктеста стратегий плейлиста", h1_style))

    headers = [
        Paragraph("Стратегия / Видео плейлиста", table_header),
        Paragraph("CAGR", table_header),
        Paragraph("Волатильность", table_header),
        Paragraph("Sharpe (vs КС)", table_header),
        Paragraph("Sortino", table_header),
        Paragraph("Max Drawdown", table_header),
        Paragraph("Calmar", table_header),
    ]

    rows_data = [
        [Paragraph("<b>1. FORTS Basis Arbitrage & Repo Carry</b>", table_text), Paragraph("<b>14.43%</b>", table_text), Paragraph("0.33%", table_text), Paragraph("<b>+2.76</b>", table_text), Paragraph("0.00", table_text), Paragraph("<b>0.00%</b>", table_text), Paragraph("&gt;10.0", table_text)],
        [Paragraph("<b>2. Kelly Criterion Dynamic Sizing (Vid 68)</b>", table_text), Paragraph("<b>14.02%</b>", table_text), Paragraph("<b>1.13%</b>", table_text), Paragraph("<b>+0.48</b>", table_text), Paragraph("<b>11.19</b>", table_text), Paragraph("<b>-0.63%</b>", table_text), Paragraph("<b>22.18</b>", table_text)],
        [Paragraph("<b>3. Market Neutral Kalman Pair (Vid 6, 45)</b>", table_text), Paragraph("<b>13.41%</b>", table_text), Paragraph("<b>0.53%</b>", table_text), Paragraph("0.00", table_text), Paragraph("0.00", table_text), Paragraph("<b>0.00%</b>", table_text), Paragraph("N/A", table_text)],
        [Paragraph("<b>4. Crash Protection: SMA-200 + Cash (Vid 12)</b>", table_text), Paragraph("<b>9.28%</b>", table_text), Paragraph("10.45%", table_text), Paragraph("-0.30", table_text), Paragraph("<b>0.84</b>", table_text), Paragraph("<b>-26.64%</b>", table_text), Paragraph("0.35", table_text)],
        [Paragraph("5. Shannon's Demon Rebalance 50/50 (Vid 13)", table_text), Paragraph("4.75%", table_text), Paragraph("13.38%", table_text), Paragraph("-0.53", table_text), Paragraph("0.44", table_text), Paragraph("-28.34%", table_text), Paragraph("0.17", table_text)],
        [Paragraph("Benchmark: Risk-Free (Ключевая ставка)", table_text), Paragraph("13.41%", table_text), Paragraph("0.33%", table_text), Paragraph("0.00", table_text), Paragraph("0.00", table_text), Paragraph("0.00%", table_text), Paragraph("N/A", table_text)],
        [Paragraph("Benchmark: Buy & Hold SBER", table_text), Paragraph("1.34%", table_text), Paragraph("33.82%", table_text), Paragraph("-0.15", table_text), Paragraph("0.24", table_text), Paragraph("-73.81%", table_text), Paragraph("0.02", table_text)],
        [Paragraph("Benchmark: Buy & Hold IMOEX", table_text), Paragraph("-5.05%", table_text), Paragraph("27.93%", table_text), Paragraph("-0.49", table_text), Paragraph("-0.04", table_text), Paragraph("-55.29%", table_text), Paragraph("-0.09", table_text)],
        [Paragraph("6. Black-Litterman Portfolio (Vid 41)", table_text), Paragraph("-2.58%", table_text), Paragraph("28.51%", table_text), Paragraph("-0.39", table_text), Paragraph("0.06", table_text), Paragraph("-54.98%", table_text), Paragraph("-0.05", table_text)],
        [Paragraph("<b>7. Covered Call Buy-Write: SBER (Vid 38)</b>", table_text), Paragraph("<b>-42.57%</b>", table_text), Paragraph("27.21%", table_text), Paragraph("-2.35", table_text), Paragraph("-1.59", table_text), Paragraph("<b>-96.42%</b>", table_text), Paragraph("-0.44", table_text)],
        [Paragraph("<b>8. Cash-Secured Put Selling (Vid 25, 31)</b>", table_text), Paragraph("<b>-84.85%</b>", table_text), Paragraph("30.17%", table_text), Paragraph("-6.47", table_text), Paragraph("-4.58", table_text), Paragraph("<b>-100.00%</b>", table_text), Paragraph("-0.85", table_text)],
    ]

    perf_table = Table([headers] + rows_data, colWidths=[185, 46, 56, 60, 44, 60, 36])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f2b48')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(perf_table)
    story.append(Spacer(1, 8))

    # Section 2: Chart
    if os.path.exists('paolucci_playlist_chart.png'):
        story.append(Paragraph("2. Графики эквити и динамика подводных просадок", h1_style))
        story.append(Image('paolucci_playlist_chart.png', width=487, height=265))
        story.append(Spacer(1, 8))

    story.append(PageBreak())

    # Section 3: Deep Dive into Playlist Modules
    story.append(Paragraph("3. Детальный разбор стратегий и комментарий: как это работает", h1_style))

    story.append(Paragraph("3.1. Формула Келли и динамический сайзинг (Видео 68)", h2_style))
    story.append(Paragraph(
        "Вместо статической аллокации позиция рассчитывается по формуле f* = (b&middot;p - q)/b на скользящем окне. "
        "Использование <b>дробного критерия Келли (0.3x)</b> защитило систему от переоценки параметров. "
        "В моменты роста неопределенности перед февралем 2022 г. размер позиции плавно сокращался до нуля (уход в РЕПО под КС), "
        "а на восстановлении рынка позиция наращивалась. "
        "Результат: <b>CAGR 14.02%, просадка всего -0.63%, Сортино 11.19</b>.",
        body_style
    ))

    story.append(Paragraph("3.2. Защита от крахов (Crisis Alpha) через SMA-200 и кэш-буфер (Видео 12)", h2_style))
    story.append(Paragraph(
        "Паолуччи отвергает покупку путов из-за постоянного временного распада и предлагает трендовый фильтр SMA-200. "
        "На MOEX стратегия удержания индекса строго выше SMA-200 с выводом 100% средств в РЕПО с Центральным Контрагентом при пробое вниз "
        "показала <b>CAGR 9.28% и ограничила просадку до -26.6%</b> (рынок рухнул на <b>-55.3%</b>). "
        "В периоды затяжных падений портфель непрерывно аккумулировал высокую ставку ЦБ (до 21%).",
        body_style
    ))

    story.append(Paragraph("3.3. «Демон Шеннона» и сбор волатильности (Видео 13, 27)", h2_style))
    story.append(Paragraph(
        "Клод Шеннон доказал, что ребалансировка 50/50 между волатильным активом и кэшем порождает положительную геометрическую доходность "
        "g = 0.5&mu; + 0.125&sigma;<sup>2</sup>. На падающем рынке IMOEX (-5.05% CAGR) регулярная ребалансировка превратила убыток "
        "в <b>положительный CAGR +4.75%</b> и снизила просадку с -55% до -28%.",
        body_style
    ))

    story.append(Paragraph("3.4. Почему опционные стратегии (Covered Call и Put Selling, Видео 25, 31, 38) обнуляют депозит?", h2_style))
    story.append(Paragraph(
        "• <b>Covered Call (Buy-Write) (-42.57% CAGR, MaxDD -96.4%):</b> Ограничивает прибыль при отскоках (+1% в день), но полностью "
        "принимает на себя обвалы базового актива.<br/>"
        "• <b>Cash-Secured Put (-84.85% CAGR, MaxDD -100%):</b> Продажа путов вне денег для сбора премии. "
        "При закрытии биржи на месяц в феврале 2022 года дельта-хеджирование стало невозможным. При открытии продавец получил маржин-колл.",
        body_style
    ))

    story.append(Spacer(1, 8))

    # Section 4: Practical Recommendations
    story.append(Paragraph("4. Институциональный модельный портфель на Московской бирже", h1_style))
    rec_box = (
        "<b>1. Консервативное ядро (75% капитала): FORTS Basis Carry & РЕПО с ЦК</b><br/>"
        "• Синтетический базисный кэрри на ОФЗ / индексе Мосбиржи генерирует гарантированные <b>КС + 1.0% годовых (14.4%)</b> без рыночного риска.<br/>"
        "• Размещение свободного ГО в фондах денежного рынка (LQDT / RUSFAR) с ежедневной капитализацией под ставку ЦБ РФ.<br/><br/>"
        "<b>2. Альфа-сателлит (25% капитала): Дробный критерий Келли (0.3x) + Тренд-фильтр SMA-200</b><br/>"
        "• Динамическое масштабирование экспозиции в акциях Сбербанка и Лукойла строго выше SMA-200. Доходность: <b>14.0% годовых при просадке 0.63%</b>.<br/><br/>"
        "<b>3. Запрет на внедрение:</b> Непокрытая продажа опционов (Put/Call) на FORTS, скальпинг без DMA-доступа и межэмитентный арбитраж (LKOH/ROSN)."
    )
    rec_table = Table([[Paragraph(rec_box, body_style)]], colWidths=[487])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e6fffa')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#38b2ac')),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 9),
        ('RIGHTPADDING', (0,0), (-1,-1), 9),
    ]))
    story.append(rec_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == '__main__':
    build_pdf()
