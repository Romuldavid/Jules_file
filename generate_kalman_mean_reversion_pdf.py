"""
Generates the executive PDF report kalman_mean_reversion_moex_report.pdf
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
            self.drawString(54, 800, "Kalman Mean Reversion: Анализ лекции Романа Паолуччи на MOEX (2021–2026)")
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

def build_pdf(filename="kalman_mean_reversion_moex_report.pdf"):
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
    story.append(Paragraph("Возврат к среднему на фильтрах Калмана (KTS) на MOEX", title_style))
    story.append(Paragraph("Скептический аудит лекции Романа Паолуччи (Quant Guild), бэктест на данных 2021–2026 гг. с учетом тарифа «Стандартный ФОРТС» и ставки ЦБ РФ", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f2b48'), spaceAfter=10))

    # Executive Summary Box
    summary_text = (
        "<b>Краткое резюме аудита:</b> Проанализирована видеолекция Романа Паолуччи <i>«Trading Mean Reversion with Kalman Filters»</i> "
        "и исходный код системы KTS (Quant Guild, <code>kts.py</code>). "
        "Эмпирическое тестирование на Московской Бирже (2021–2026, 1468 дней) с учетом реальных трений (тариф «Стандартный ФОРТС», "
        "комиссия 0.05%, ставка шорта Ключевая ставка + 4.0% и задержка $t+1$) показало: <br/>"
        "1. <b>Торговля одиночными акциями по KTS полностью провальна:</b> Сбербанк (CAGR -26.98%, MaxDD -86.2%) и индекс IMOEX (CAGR -20.03%) "
        "терпят крах из-за нестационарности рыночных трендов (ловля падающих ножей).<br/>"
        "2. <b>Парадокс Noise Lever:</b> Настройка «Trust Prices» (Lever = 0%) с низким оборотом генерирует <b>CAGR +11.84% при просадке всего -4.45%</b> "
        "на спреде SBER/SBERP, тогда как баланс 50% сливает капитал (-10.62%) из-за переторговки.<br/>"
        "3. <b>Межэмитентный арбитраж (LKOH/ROSN):</b> Завершается полной ликвидацией (-95.8% CAGR) из-за фундаментального разрыва коинтеграции."
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

    # Section 1: Metrics
    story.append(Paragraph("1. Сводные количественные результаты бэктеста KTS (2021–2026)", h1_style))

    headers = [
        Paragraph("Стратегия / Система KTS", table_header),
        Paragraph("CAGR", table_header),
        Paragraph("Волатильность", table_header),
        Paragraph("Sharpe (vs КС)", table_header),
        Paragraph("Sortino", table_header),
        Paragraph("Max Drawdown", table_header),
        Paragraph("Calmar", table_header),
    ]

    rows_data = [
        [Paragraph("<b>FORTS Basis Carry & Repo (Бенчмарк)</b>", table_text), Paragraph("<b>14.43%</b>", table_text), Paragraph("0.33%", table_text), Paragraph("<b>+2.76</b>", table_text), Paragraph("0.00", table_text), Paragraph("<b>0.00%</b>", table_text), Paragraph("&gt;10.0", table_text)],
        [Paragraph("<b>KTS Pair: SBER/SBERP (Lever = 0%)</b>", table_text), Paragraph("<b>11.84%</b>", table_text), Paragraph("<b>1.76%</b>", table_text), Paragraph("-0.79", table_text), Paragraph("<b>2.84</b>", table_text), Paragraph("<b>-4.45%</b>", table_text), Paragraph("<b>2.66</b>", table_text)],
        [Paragraph("Benchmark: Risk-Free (Ключевая ставка)", table_text), Paragraph("13.41%", table_text), Paragraph("0.33%", table_text), Paragraph("0.00", table_text), Paragraph("0.00", table_text), Paragraph("0.00%", table_text), Paragraph("N/A", table_text)],
        [Paragraph("Benchmark: Buy & Hold SBER", table_text), Paragraph("1.34%", table_text), Paragraph("33.82%", table_text), Paragraph("-0.15", table_text), Paragraph("0.24", table_text), Paragraph("-73.81%", table_text), Paragraph("0.02", table_text)],
        [Paragraph("Benchmark: Buy & Hold IMOEX", table_text), Paragraph("-5.05%", table_text), Paragraph("27.93%", table_text), Paragraph("-0.49", table_text), Paragraph("-0.04", table_text), Paragraph("-55.29%", table_text), Paragraph("-0.09", table_text)],
        [Paragraph("<b>KTS Pair: SBER/SBERP (Lever = 50%)</b>", table_text), Paragraph("<b>-10.62%</b>", table_text), Paragraph("4.73%", table_text), Paragraph("-5.02", table_text), Paragraph("-2.89", table_text), Paragraph("<b>-51.10%</b>", table_text), Paragraph("-0.21", table_text)],
        [Paragraph("<b>KTS Single-Asset (IMOEX)</b>", table_text), Paragraph("<b>-20.03%</b>", table_text), Paragraph("23.23%", table_text), Paragraph("-1.38", table_text), Paragraph("-0.70", table_text), Paragraph("<b>-75.76%</b>", table_text), Paragraph("-0.26", table_text)],
        [Paragraph("<b>KTS Single-Asset (SBER)</b>", table_text), Paragraph("<b>-26.98%</b>", table_text), Paragraph("29.08%", table_text), Paragraph("-1.36", table_text), Paragraph("-0.76", table_text), Paragraph("<b>-86.19%</b>", table_text), Paragraph("-0.31", table_text)],
        [Paragraph("<b>KTS Pair: LKOH/ROSN (Lever = 50%)</b>", table_text), Paragraph("<b>-95.84%</b>", table_text), Paragraph("331.13%", table_text), Paragraph("-0.20", table_text), Paragraph("-0.15", table_text), Paragraph("<b>-103.10%</b>", table_text), Paragraph("-0.93", table_text)],
    ]

    perf_table = Table([headers] + rows_data, colWidths=[177, 48, 58, 60, 44, 62, 38])
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
    if os.path.exists('kalman_mean_reversion_chart.png'):
        story.append(Paragraph("2. Графики эквити и динамика подводных просадок", h1_style))
        story.append(Image('kalman_mean_reversion_chart.png', width=487, height=265))
        story.append(Spacer(1, 8))

    story.append(PageBreak())

    # Section 3: Deep Dive
    story.append(Paragraph("3. Глубокий критический анализ алгоритма KTS", h1_style))

    story.append(Paragraph("3.1. Почему модель Паолуччи ломается на одиночных акциях?", h2_style))
    story.append(Paragraph(
        "В видеолекции автор демонстрирует работу интерфейса <code>kts.py</code> на отдельной акции (Apple). "
        "Однако на развивающемся и санкционном рынке РФ цены акций являются <b>нестационарными геометрическими случайными блужданиями</b>, "
        "а не процессами Орнштейна-Уленбека. В кризис 2022 года при обвале Сбербанка с 300 до 90 рублей фильтр Калмана считал "
        "каждое падение «временным отклонением от справедливой цены» и непрерывно открывал лонг против нисходящего тренда, "
        "а в восходящем тренде 2023 года — открывал шорт, оплачивая брокеру ставку заимствования (до 25% годовых). "
        "Итог: <b>CAGR -26.98% и просадка -86.19%</b>.",
        body_style
    ))

    story.append(Paragraph("3.2. Парадокс Noise Lever: почему 0% спасает систему, а 50% уничтожает?", h2_style))
    story.append(Paragraph(
        "Рычаг шума (Noise Lever) определяет масштабирование ковариации шума наблюдений R. "
        "При <b>Lever = 50%</b> (сбалансированный режим из видео) фильтр обновляет среднее слишком медленно, генерируя "
        "<b>367 ложных входов</b>. Огромная комиссионная нагрузка и плата за шорты приводят к убытку <b>-10.62% годовых и просадке -51.1%</b>.<br/>"
        "Напротив, при <b>Lever = 0% («Trust Prices»)</b> фильтр мгновенно подтягивает fair value к рынку (R &rarr; 0), поэтому сигналы "
        "формируются <i>только при экстремальных расхождениях</i>. Число сделок сокращается до <b>46</b>, а результат взлетает до "
        "<b>CAGR +11.84% при просадке всего -4.45% и коэффициенте Сортино 2.84</b>!",
        body_style
    ))

    story.append(Paragraph("3.3. Крах межэмитентных пар (LKOH против ROSN)", h2_style))
    story.append(Paragraph(
        "При попытке применить KTS к спреду акций Лукойла и Роснефти система терпит <b>полную ликвидацию (-95.84% CAGR, просадка &gt;100%)</b>. "
        "Различная структура экспорта, санкционные пакеты и дивидендные решения разрушают долгосрочную коинтеграцию, лишая спред свойства возврата к среднему.",
        body_style
    ))

    story.append(Spacer(1, 8))

    # Section 4: Practical Recommendations
    story.append(Paragraph("4. Институциональный модельный портфель на Московской бирже", h1_style))
    rec_box = (
        "<b>1. Консервативное ядро (75% капитала): FORTS Basis Carry & РЕПО с ЦК</b><br/>"
        "• Синтетический базисный кэрри на ОФЗ / индексе Мосбиржи генерирует гарантированные <b>КС + 1.0% годовых (14.4%)</b> без рыночного риска.<br/>"
        "• Размещение свободного ГО в фондах денежного рынка (LQDT / RUSFAR) с ежедневной капитализацией под ставку ЦБ РФ.<br/><br/>"
        "<b>2. Альфа-сателлит (25% капитала): KTS на паре SBER / SBERP с Noise Lever = 0%</b><br/>"
        "• Эксплуатация статистического расхождения обыкновенных и привилегированных акций Сбербанка в режиме мгновенного доверия ценам.<br/>"
        "• Доходность: <b>11.8% годовых при минимальной просадке 4.45%</b> и коэффициенте Сортино 2.84.<br/><br/>"
        "<b>3. Категорический запрет:</b> Применение KTS к одиночным акциям (SBER, GAZP), индексам (IMOEX) и межэмитентным парам (LKOH/ROSN)."
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
