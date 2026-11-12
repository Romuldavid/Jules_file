"""
Generates the executive PDF report memlabs_trilogy_moex_report.pdf
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
            self.drawString(54, 800, "MemLabs HFT Quant Trilogy: Анализ Trend, Reversion & Regime на MOEX (2021–2026)")
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

def build_pdf(filename="memlabs_trilogy_moex_report.pdf"):
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
    story.append(Paragraph("Трилогия MemLabs (Trend, Reversion, Regime) на Мосбирже", title_style))
    story.append(Paragraph("Скептический аудит 3 видеоэкспертиз экс-HFT кванта, бэктест на данных 2021–2026 гг. с учетом тарифа «Стандартный ФОРТС» и ставки ЦБ РФ", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f2b48'), spaceAfter=10))

    # Executive Summary Box
    summary_text = (
        "<b>Краткое резюме аудита:</b> Проанализированы три фундаментальных видеоурока экс-HFT кванта <b>MemLabs</b>: "
        "<i>«Trend Following»</i>, <i>«Mean Reversion»</i> и <i>«How to handle Regime Changes»</i>. "
        "Эмпирический бэктест на котировках Московской Биржи (2021–2026, 1468 дней) с учетом тарифа «Стандартный ФОРТС», "
        "ставки заимствования шорта (Ключевая ставка + 4.0% = до 25% годовых) и каузальной задержки $t+1$ выявил: <br/>"
        "1. <b>1-Bar Momentum (Trend Following) катастрофически убыточен (-34.38% CAGR, MaxDD -91.5%)</b> из-за отрицательной "
        "автокорреляции российских акций на дневном горизонте и комиссионного износа.<br/>"
        "2. <b>1-Bar Mean Reversion математически выигрывает (+9.09% без трений), но уничтожается брокером (-12.59% чистыми)</b> из-за ставки шорта 25% годовых.<br/>"
        "3. <b>Адаптация к смене режимов (Regime Changes) спасает систему:</b> динамический переключатель тренда/боковика с выходом в РЕПО "
        "при панике показал <b>CAGR +10.27% при просадке всего -20.80%</b>, а институциональный <b>Long-Only AR — CAGR +13.42%</b>."
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
    story.append(Paragraph("1. Сводные количественные результаты бэктеста трилогии MemLabs", h1_style))

    headers = [
        Paragraph("Стратегия / Модель MemLabs", table_header),
        Paragraph("CAGR", table_header),
        Paragraph("Волатильность", table_header),
        Paragraph("Sharpe (vs КС)", table_header),
        Paragraph("Sortino", table_header),
        Paragraph("Max Drawdown", table_header),
        Paragraph("Calmar", table_header),
    ]

    rows_data = [
        [Paragraph("<b>1. FORTS Basis Arbitrage & Repo Carry</b>", table_text), Paragraph("<b>14.43%</b>", table_text), Paragraph("0.33%", table_text), Paragraph("<b>+2.76</b>", table_text), Paragraph("0.00", table_text), Paragraph("<b>0.00%</b>", table_text), Paragraph("&gt;10.0", table_text)],
        [Paragraph("<b>2. Институциональный: Long-Only AR + Repo Cash</b>", table_text), Paragraph("<b>13.42%</b>", table_text), Paragraph("12.82%", table_text), Paragraph("<b>+0.06</b>", table_text), Paragraph("<b>0.60</b>", table_text), Paragraph("<b>-22.02%</b>", table_text), Paragraph("<b>0.61</b>", table_text)],
        [Paragraph("<b>3. Adaptive Regime Switcher (SBER) (Vid 3)</b>", table_text), Paragraph("<b>10.27%</b>", table_text), Paragraph("11.60%", table_text), Paragraph("-0.19", table_text), Paragraph("<b>0.76</b>", table_text), Paragraph("<b>-20.80%</b>", table_text), Paragraph("0.49", table_text)],
        [Paragraph("4. Trend Following: SMA-200 + Repo Cash", table_text), Paragraph("9.28%", table_text), Paragraph("10.45%", table_text), Paragraph("-0.30", table_text), Paragraph("0.84", table_text), Paragraph("-26.64%", table_text), Paragraph("0.35", table_text)],
        [Paragraph("5. 1-Bar Mean Reversion (0-Cost Academic)", table_text), Paragraph("9.09%", table_text), Paragraph("33.79%", table_text), Paragraph("+0.05", table_text), Paragraph("0.55", table_text), Paragraph("-47.44%", table_text), Paragraph("0.19", table_text)],
        [Paragraph("Benchmark: Buy & Hold SBER", table_text), Paragraph("1.34%", table_text), Paragraph("33.82%", table_text), Paragraph("-0.15", table_text), Paragraph("0.24", table_text), Paragraph("-73.81%", table_text), Paragraph("0.02", table_text)],
        [Paragraph("Benchmark: Buy & Hold IMOEX", table_text), Paragraph("-5.05%", table_text), Paragraph("27.93%", table_text), Paragraph("-0.49", table_text), Paragraph("-0.04", table_text), Paragraph("-55.29%", table_text), Paragraph("-0.09", table_text)],
        [Paragraph("Benchmark: Risk-Free (Ключевая ставка)", table_text), Paragraph("13.41%", table_text), Paragraph("0.33%", table_text), Paragraph("0.00", table_text), Paragraph("0.00", table_text), Paragraph("0.00%", table_text), Paragraph("N/A", table_text)],
        [Paragraph("<b>6. 1-Bar Mean Reversion (Realistic MOEX Costs)</b>", table_text), Paragraph("<b>-12.59%</b>", table_text), Paragraph("33.81%", table_text), Paragraph("-0.61", table_text), Paragraph("-0.31", table_text), Paragraph("<b>-68.70%</b>", table_text), Paragraph("-0.18", table_text)],
        [Paragraph("<b>7. 1-Bar Momentum (0-Cost Academic)</b>", table_text), Paragraph("<b>-18.37%</b>", table_text), Paragraph("33.79%", table_text), Paragraph("-0.80", table_text), Paragraph("-0.50", table_text), Paragraph("<b>-74.47%</b>", table_text), Paragraph("-0.25", table_text)],
        [Paragraph("<b>8. 1-Bar Momentum (Realistic MOEX Costs)</b>", table_text), Paragraph("<b>-34.38%</b>", table_text), Paragraph("33.82%", table_text), Paragraph("-1.44", table_text), Paragraph("-1.29", table_text), Paragraph("<b>-91.53%</b>", table_text), Paragraph("-0.38", table_text)],
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
    if os.path.exists('memlabs_trilogy_chart.png'):
        story.append(Paragraph("2. Графики эквити и динамика подводных просадок", h1_style))
        story.append(Image('memlabs_trilogy_chart.png', width=487, height=265))
        story.append(Spacer(1, 8))

    story.append(PageBreak())

    # Section 3: Deep Dive into Trilogy
    story.append(Paragraph("3. Детальный разбор моделей MemLabs и институциональные уроки", h1_style))

    story.append(Paragraph("3.1. Почему 1-Bar Momentum (Trend Following) убивает счет на MOEX?", h2_style))
    story.append(Paragraph(
        "В видео 5tyLyYY1PXY автор исследует правило следования тренду лага 1: s<sub>t</sub> = sign(r<sub>t-1</sub>). "
        "На дневном горизонте российского рынка акций наблюдается <b>отрицательная автокорреляция</b> (локальный откат после роста). "
        "Покупка на вчерашних максимумах и шорт на минимумах приносит убыток даже без комиссий (<b>-18.37% CAGR</b>). "
        "Включение комиссий 0.05% и ставки шорта (25% годовых) приводит к полному уничтожению счета: <b>-34.38% CAGR и просадка -91.53%</b>.",
        body_style
    ))

    story.append(Paragraph("3.2. Парадокс Mean Reversion: математический плюс, убитый шортами", h2_style))
    story.append(Paragraph(
        "В видео _urG139AM48 автор переворачивает сигнал: s<sub>t</sub> = -sign(r<sub>t-1</sub>). "
        "В безналоговом мире без издержек это действительно генерирует <b>+9.09% годовых</b> (отскок от перепроданности работает). "
        "Однако чтобы шортить после каждого растущего дня, инвестор должен платить брокеру за заем акций <b>до 25% годовых</b>. "
        "Плата за шорт превышает математическое преимущество, превращая потенциальный плюс в <b>убыток -12.59% годовых и просадку -68.70%</b>.",
        body_style
    ))

    story.append(Paragraph("3.3. Триумф Regime Changes (Видео X5QcNyYRMqQ) и институциональная адаптация", h2_style))
    story.append(Paragraph(
        "В третьем видео автор обосновывает необходимость адаптации к режимам: <br/>"
        "• В бычьем тренде (волатильность &lt; 22%) работает импульс;<br/>"
        "• В боковике (22% &lt; Vol &lt; 35%) работает возврат к среднему;<br/>"
        "• В кризис (Vol &gt; 35% или пробой ниже SMA-200) — <b>100% уход в кэш-РЕПО под ставку ЦБ</b>.<br/>"
        "Результат: адаптивная модель заработала <b>CAGR +10.27% при просадке всего -20.80%</b>, "
        "а институциональный Long-Only AR с порогом входа (|y| &gt; 0.15%) показал <b>CAGR +13.42% при просадке -22.02%</b>!",
        body_style
    ))

    story.append(Spacer(1, 8))

    # Section 4: Practical Recommendations
    story.append(Paragraph("4. Институциональный модельный портфель на Московской бирже", h1_style))
    rec_box = (
        "<b>1. Дельта-нейтральное ядро (75% капитала): FORTS Basis Carry & РЕПО с ЦК</b><br/>"
        "• Синтетический базисный кэрри на ОФЗ / индексе Мосбиржи генерирует гарантированные <b>КС + 1.0% годовых (14.4%)</b> без рыночного риска.<br/>"
        "• Размещение свободного ГО в фондах денежного рынка (LQDT / RUSFAR) с ежедневной капитализацией под ставку ЦБ РФ.<br/><br/>"
        "<b>2. Альфа-сателлит (25% капитала): Адаптивный переключатель режимов (Regime Switcher) + Long-Only AR</b><br/>"
        "• Вход в лонг лидеров рынка (Сбербанк, Лукойл) строго выше SMA-200 при подтверждении порога сигнала. При высокой волатильности (&gt;35%) — полный уход в денежный рынок.<br/>"
        "• Доходность сателлита: <b>13.4% годовых при минимальной просадке</b>.<br/><br/>"
        "<b>3. Запрет на внедрение:</b> 1-барный дейтрейдинг по моментуму, симметричный лонг-шорт на спотовых акциях."
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
