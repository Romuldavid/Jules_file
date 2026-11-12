"""
generate_quantt_pdf.py
Генерация профессионального аналитического PDF-отчета
по критическому аудиту квантовых стратегий из библиотеки Quantt (quantt.co.uk) на MOEX.
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
            self.drawString(54, 800, "Quantt UK Institutional Strategies Audit | MOEX Backtest Analysis")
            self.setStrokeColor(colors.HexColor("#dee2e6"))
            self.setLineWidth(0.5)
            self.line(54, 792, 541, 792)

        page_text = f"Стр. {self._pageNumber} из {page_count}"
        self.drawRightString(541, 35, page_text)
        self.drawString(54, 35, "Конфиденциально | Аудит стратегий Quantt (MOEX 2021–2024)")
        self.setStrokeColor(colors.HexColor("#dee2e6"))
        self.setLineWidth(0.5)
        self.line(54, 47, 541, 47)
        self.restoreState()


def build_quantt_pdf(pdf_filename="quantt_trading_strategies_report.pdf"):
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

    story.append(Paragraph("Критический аудит стратегий Quantt на MOEX", title_style))
    story.append(Paragraph("Стресс-тест институциональных моделей (Selling Volatility, Cross-Sectional Momentum, Market Making) на данных 2021–2024 гг.", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f2b48"), spaceBefore=0, spaceAfter=8))

    story.append(Paragraph("1. Реальность британских квантовых концепций на Мосбирже", h1_style))
    story.append(Paragraph(
        "Британский портал <b>Quantt.co.uk</b> обучает квантов стандартам Tier-1 фондов (Citadel, Jane Street). "
        "Однако применимость этих концепций в России требует предельного скептицизма:",
        body_style
    ))

    story.append(Paragraph("• <b>Ловушка продажи волатильности:</b> Статья Quantt 'Selling Volatility' подтверждает: сбор теты в опционах несет хвостовой риск. На MOEX в 2022 году стратегия потеряла -97.1%.", bullet_style))
    story.append(Paragraph("• <b>Cross-Sectional Momentum:</b> Лидеры российского рынка (Сбербанк, Лукойл) при жестком контроле пробоя SMA-200 принесли +15.1% годовых при умеренной просадке 20.4%.", bullet_style))
    story.append(Paragraph("• <b>Тариф «Стандартный ФОРТС»:</b> 1.45 ₽/контракт, 5.80 ₽/спред, 0.90 ₽ опцион. Базисный арбитраж на FORTS показал +14.6% годовых при нулевой просадке.", bullet_style))

    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Результаты количественного бэктестирования", h1_style))
    metrics_df = pd.read_csv("quantt_strategies_metrics.csv")
    table_data = [
        ["Стратегия / Модель", "CAGR", "Волатильность", "Шарп (vs RUSFAR)", "Сортино", "MaxDD", "Винрейт", "Доходность"]
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

    if os.path.exists("quantt_strategies_chart.png"):
        story.append(Paragraph("3. Графический сравнительный анализ", h1_style))
        story.append(Image("quantt_strategies_chart.png", width=480, height=260))
        story.append(Spacer(1, 8))

    story.append(Paragraph("4. Скептические выводы", h1_style))
    story.append(Paragraph("Квантовые стратегии с западных платформ обязаны учитывать специфику санкционного рынка РФ. Продажа опционной волатильности и пассивный маркет-мейкинг ведут к ликвидации счета. Единственными работающими инструментами являются среднесрочный моментум лидеров и деривативный арбитраж на FORTS с монетизацией высокой ставки Банка России.", body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report successfully generated: {pdf_filename}")


if __name__ == "__main__":
    build_quantt_pdf()
