"""
generate_csmom_pdf.py
Генерация профессионального аналитического PDF-отчета
по тестированию Cross-Sectional Momentum на реальных данных MOEX (01.01.2021 – 09.11.2026).
"""

import os
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
pdfmetrics.registerFont(TTFont(FONT_REGULAR, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))


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
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont(FONT_REGULAR, 8)
        self.setFillColor(colors.HexColor("#6c757d"))

        if self._pageNumber > 1:
            self.drawString(54, 800, "MOEX Cross-Sectional Momentum Research | Real Data 2021–2026")
            self.setStrokeColor(colors.HexColor("#dee2e6"))
            self.setLineWidth(0.5)
            self.line(54, 792, 541, 792)

        page_text = f"Стр. {self._pageNumber} из {page_count}"
        self.drawRightString(541, 35, page_text)
        self.drawString(54, 35, "Конфиденциально | Доказательное исследование (MOEX 2021–2026)")
        self.setStrokeColor(colors.HexColor("#dee2e6"))
        self.setLineWidth(0.5)
        self.line(54, 47, 541, 47)
        self.restoreState()


def build_csmom_pdf(pdf_filename="csmom_moex_report.pdf"):
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        fontName=FONT_BOLD,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f2b48"),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        fontName=FONT_REGULAR,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#555555"),
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        fontName=FONT_BOLD,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f2b48"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        fontName=FONT_BOLD,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1b4d79"),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        fontName=FONT_REGULAR,
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#222222"),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        fontName=FONT_REGULAR,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#222222"),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    story = []

    story.append(Paragraph("Cross-Sectional Momentum на реальных данных MOEX", title_style))
    story.append(Paragraph("Исследование относительного моментума лидеров с 01.01.2021 по 09.11.2026 гг. (1469 торговых дней)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f2b48"), spaceBefore=0, spaceAfter=8))

    story.append(Paragraph("1. Механика и контекст исследования", h1_style))
    story.append(Paragraph(
        "<b>Cross-Sectional Momentum (CSMOM)</b> — покупка сильнейших акций-лидеров относительно других бумаг корзины "
        "(SBER, LKOH, ROSN, GAZP, GMKN, TATN, NVTK) за последние 3–6 месяцев. "
        "Тестирование проведено на 100% реальных данных Московской биржи по 06.11.2026 г. с учетом ставок RUSFAR и комиссий.",
        body_style
    ))

    story.append(Paragraph("• <b>Провал наивного моментума:</b> Без макро-фильтра просадка составила -67.25% (хуже индекса IMOEX -55.29%).", bullet_style))
    story.append(Paragraph("• <b>Спасительный фильтр SMA-200:</b> Уход в кэш (фонд LQDT) при даунтренде дал CAGR +7.05% при снижении просадки до 30.83%.", bullet_style))
    story.append(Paragraph("• <b>Токсичность спот-шорта:</b> Маржинальный шорт аутсайдеров по ставке ЦБ + 5% привел к убытку -16.56%.", bullet_style))
    story.append(Paragraph("• <b>Триумф денежного рынка:</b> Ставка RUSFAR дала удвоение капитала (+101.63%) при нулевой просадке.", bullet_style))

    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Сводная таблица результатов (2021–2026 гг.)", h1_style))
    metrics_df = pd.read_csv("csmom_strategies_metrics.csv")
    table_data = [
        ["Стратегия / Бенчмарк", "CAGR", "Волатильность", "Шарп (vs RUSFAR)", "Сортино", "MaxDD", "Винрейт", "Доходность"]
    ]
    for _, row in metrics_df.iterrows():
        s_name = row["Strategy"].replace("Benchmark: ", "").replace("1. ", "").replace("2. ", "").replace("3. ", "").replace("4. ", "")
        table_data.append([
            s_name[:32],
            f"{row['CAGR']*100:.1f}%",
            f"{row['Volatility']*100:.1f}%",
            f"{row['Sharpe']:.2f}",
            f"{row['Sortino']:.2f}",
            f"{row['MaxDrawdown']*100:.1f}%",
            f"{row['WinRate']*100:.1f}%",
            f"{row['TotalReturn']*100:.1f}%"
        ])

    t = Table(table_data, colWidths=[150, 48, 52, 54, 48, 48, 44, 50])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f2b48")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), FONT_REGULAR),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    if os.path.exists("csmom_strategies_chart.png"):
        story.append(Paragraph("3. Графический сравнительный анализ", h1_style))
        story.append(Image("csmom_strategies_chart.png", width=480, height=260))
        story.append(Spacer(1, 8))

    story.append(Paragraph("4. Практические квантовые выводы для инвестора", h1_style))
    story.append(Paragraph("Cross-Sectional Momentum на MOEX оправдан исключительно в комбинации со среднесрочным трендовым предохранителем (SMA-200). Попытка держать моментум на падающем рынке или использовать маржинальный спот-шорт разрушает капитал. Базовым активом для управления ликвидностью в РФ остается денежный рынок RUSFAR.", body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report successfully generated: {pdf_filename}")


if __name__ == "__main__":
    build_csmom_pdf()
