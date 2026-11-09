"""
generate_smartlab_pdf.py
Генерация профессионального аналитического PDF-отчета на основе анализа Smart-Lab и бэктестов MOEX.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
import pandas as pd

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
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6c757d"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 800, "Smart-Lab Quantitative Strategies Research | MOEX Backtest Analysis")
            self.setStrokeColor(colors.HexColor("#dee2e6"))
            self.setLineWidth(0.5)
            self.line(54, 792, 541, 792)

        # Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(541, 35, page_str)
        self.drawString(54, 35, "CONFIDENTIAL & PROPRIETARY — FOR PROFESSIONAL USE ONLY")
        self.setStrokeColor(colors.HexColor("#dee2e6"))
        self.setLineWidth(0.5)
        self.line(54, 47, 541, 47)
        self.restoreState()


def generate_pdf():
    pdf_filename = "smartlab_trading_strategies_report.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4a5568'),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#2b6cb0'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=6
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1a202c')
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Smart-Lab Strategies: Quantitative Analysis & MOEX Backtests", title_style))
    story.append(Paragraph("Systematic evaluation of 5 trading methodologies discussed on Smart-Lab.ru | Period: 2021–2024", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2b6cb0"), spaceAfter=12))

    # Executive Summary Box
    summary_text = (
        "<b>Executive Summary:</b> Analysis of popular algorithms from Smart-Lab demonstrates that standard textbook "
        "strategies fail on the Russian market under high interest rates (16-21%) and severe dividend drops. "
        "However, integrating <b>tactical asset allocation</b> (Equities + Gold + Money Market) and <b>trend-following with "
        "liquidity fund cash parking</b> produces superior risk-adjusted alpha (CAGR 19.3–21.1%, Sharpe > 1.0, Max DD < 17%), "
        "massively outperforming Buy & Hold IMOEX (-6.7% CAGR, -55.3% Max DD)."
    )
    summary_table = Table([[Paragraph(summary_text, callout_style)]], colWidths=[515])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#edf2f7')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Section 1
    story.append(Paragraph("1. Systematic Performance Comparison (MOEX 2021–2024)", h1_style))
    story.append(Paragraph(
        "Historical data retrieved directly from MOEX ISS API. Backtest incorporates actual exchange and broker commissions (0.04%), "
        "realistic execution slippage (0.04%), and dynamic Central Bank risk-free cash yields (LQDT).", body_style))

    # Load metrics from CSV
    metrics_df = pd.read_csv("smartlab_strategies_metrics.csv")

    # Table header and rows
    table_data = [["Strategy", "CAGR", "Total Ret", "Max DD", "Vol", "Sharpe", "Sortino", "Calmar"]]
    for _, row in metrics_df.iterrows():
        name = row["Strategy"]
        # Format name for clean display
        if "Tactical" in name:
            short_name = "Tactical Allocation (Stock+Gold+Cash)"
        elif "Trend" in name:
            short_name = "Trend Following (Donchian + LQDT)"
        elif "Cash & Carry" in name:
            short_name = "Cash & Carry / Basis Arbitrage"
        elif "Dividend" in name:
            short_name = "Dividend Momentum (Alpha Horses)"
        elif "Money Market" in name:
            short_name = "Benchmark: Money Market (LQDT)"
        elif "Mean-Reversion" in name:
            short_name = "Mean-Reversion (RSI-2 Pullback)"
        elif "Buy & Hold" in name:
            short_name = "Benchmark: Buy & Hold IMOEX"
        else:
            short_name = name

        table_data.append([
            short_name,
            f"{row['CAGR']*100:.1f}%",
            f"{row['Total Return']*100:.1f}%",
            f"{row['Max Drawdown']*100:.1f}%",
            f"{row['Annual Volatility']*100:.1f}%",
            f"{row['Sharpe Ratio']:.2f}",
            f"{row['Sortino Ratio']:.2f}",
            f"{row['Calmar Ratio']:.2f}"
        ])

    perf_table = Table(table_data, colWidths=[205, 45, 50, 45, 45, 42, 42, 41])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e6fffa')), # Highlight winner
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#ebf8ff')), # Highlight runner-up
        ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor('#fff5f5')), # Benchmark negative
    ]))
    story.append(perf_table)
    story.append(Spacer(1, 10))

    # Section 2: Chart Image
    story.append(Paragraph("2. Cumulative Equity Curves and Drawdown Profiles", h1_style))
    if os.path.exists("smartlab_strategies_chart.png"):
        img = Image("smartlab_strategies_chart.png", width=515, height=275)
        story.append(img)
    story.append(Spacer(1, 10))

    # Section 3: Deep Dive Findings
    story.append(Paragraph("3. Core Analytical Findings & Smart-Lab Debate Resolution", h1_style))
    findings = [
        "<b>1. Tactical Multi-Asset Allocation Wins (CAGR 21.1%, Sharpe 1.02):</b> As discussed across top blogs, combining equities with physical gold (GLDRUB_TOM) and liquidity funds neutralizes ruble devaluation shocks and geopolitical drawdowns.",
        "<b>2. Trend Following is a 'Cash-Parking' Engine:</b> Classic 20/10 Donchian systems stay in cash 65% of the time. When cash earns 15–19% in LQDT, the strategy achieves CAGR 19.3% with an ultra-low Max Drawdown of just 8.5%.",
        "<b>3. The Failure of Unhedged Mean-Reversion:</b> RSI-2 dip buying delivers poor returns (6.1% CAGR vs 11.8% in cash), as falling Russian equities tend to develop long momentum cascades rather than immediate mean-reversions.",
        "<b>4. Cash & Carry / Basis Arbitrage for Institutional Capital:</b> Synthesizing high contango spreads provides 14.9% CAGR with zero drawdown, serving as an optimal alternative to short-term deposits.",
    ]
    for f in findings:
        story.append(Paragraph(f, body_style))
        story.append(Spacer(1, 2))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF отчет успешно сформирован: {pdf_filename}")

if __name__ == "__main__":
    generate_pdf()
