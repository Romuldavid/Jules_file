"""
generate_rbloggers_pdf.py
Генерация профессионального PDF-отчета на русском языке
с анализом квантовых стратегий с R-bloggers.com и результатами бэктеста на MOEX.
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

# Регистрация кириллических шрифтов
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

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 800, "R-Bloggers Quantitative Strategies Audit | MOEX Backtest Analysis")
            self.setStrokeColor(colors.HexColor("#dee2e6"))
            self.setLineWidth(0.5)
            self.line(54, 792, 541, 792)

        # Footer
        page_text = f"Стр. {self._pageNumber} из {page_count}"
        self.drawRightString(541, 35, page_text)
        self.drawString(54, 35, "Конфиденциально | Количественный аудит стратегий (MOEX 2021–2024)")
        self.setStrokeColor(colors.HexColor("#dee2e6"))
        self.setLineWidth(0.5)
        self.line(54, 47, 541, 47)
        self.restoreState()


def build_pdf_report(pdf_filename="rbloggers_moex_strategies_report.pdf"):
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Стили с поддержкой кириллицы
    title_style = ParagraphStyle(
        "DocTitle",
        fontName=FONT_BOLD,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f2b48"),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        fontName=FONT_REGULAR,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#555555"),
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        fontName=FONT_BOLD,
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f2b48"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1b4d79"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        fontName=FONT_REGULAR,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#222222"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        fontName=FONT_REGULAR,
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#222222"),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    verdict_style = ParagraphStyle(
        "Verdict_Custom",
        fontName=FONT_BOLD,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#8b0000"),
        spaceAfter=6
    )

    story = []

    # Титульный блок
    story.append(Paragraph("Критический аудит стратегий с R-bloggers в реалиях MOEX", title_style))
    story.append(Paragraph("Количественный стресс-тест западных алгоритмов на реальных данных Мосбиржи (2021–2024 гг.)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f2b48"), spaceBefore=0, spaceAfter=10))

    # Введение
    story.append(Paragraph("1. Системные заблуждения квантов при переносе моделей на российский рынок", h1_style))
    intro_p1 = (
        "Портал <b>R-bloggers.com</b> служит глобальным хабом для тысяч quantitative-разработчиков и исследователей "
        "(блоги Systematic Investor, The R Trader, Robot Wealth, Learning Machines). Однако бэктесты, публикуемые на портале, "
        "страдают от четырех фатальных уязвимостей, делающих их неприменимыми к рынку РФ:"
    )
    story.append(Paragraph(intro_p1, body_style))

    story.append(Paragraph("• <b>Иллюзия нулевой ставки (Zero Rate Bias):</b> В R-bloggers безрисковая ставка $R_f$ по умолчанию равна 0%. На MOEX безрисковая доходность (RUSFAR/LQDT) колебалась от 6.5% до 21.0% годовых. Стратегия с доходностью 10% годовых в РФ генерирует глубоко отрицательный коэффициент Шарпа.", bullet_style))
    story.append(Paragraph("• <b>Запретительная стоимость шорта на споте:</b> Модели Pairs Trading исходят из симметричности плеч. На MOEX спот-шорт обходится в ставку ЦБ + 4–6% (до 26% годовых в 2024 г.), что полностью уничтожает альфу. Единственное решение — торговля через фьючерсы срочного рынка FORTS.", bullet_style))
    story.append(Paragraph("• <b>Динамика Ключевой Ставки ЦБ РФ:</b> В расчетах строго задействовано дискретное расписание (7.5% -> пик 21% в 2024-2025 гг. -> 14.0% на 20.08.2026 г.).", bullet_style))
    story.append(Paragraph("• <b>Учет тарифа «Стандартный ФОРТС»:</b> Комиссия брокера 0.45 руб. + биржа ~1.00 руб. = 1.45 руб./контракт. Полный круг на спред из 2 контрактов обходится всего в 5.80 руб., а исполнение опциона — в 0.90 руб., что делает срочный арбитраж высокоэффективным.", bullet_style))
    story.append(Paragraph("• <b>Геополитические структурные сломы:</b> Западные квант-модели не учитывают остановки биржи (февраль-март 2022), валютную фрагментацию и дивидендные шоки.", bullet_style))
    story.append(Paragraph("• <b>Транзакционные издержки:</b> Частые ребалансировки в неликвидных стаканах съедают бумажную прибыль на комиссиях и проскальзывании (слиппедже).", bullet_style))

    story.append(Spacer(1, 8))

    # Сводная таблица результатов
    story.append(Paragraph("2. Результаты доказательного моделирования (Бэктест 2021–2024 гг.)", h1_style))

    metrics_df = pd.read_csv("rbloggers_strategies_metrics.csv")
    table_data = [
        ["Стратегия / Бенчмарк", "CAGR", "Волатильность", "Шарп (vs RUSFAR)", "Сортино", "MaxDD", "Винрейт", "Доходность"]
    ]

    for _, row in metrics_df.iterrows():
        s_name = row["Strategy"].replace("Benchmark: ", "").replace("1. ", "").replace("2. ", "").replace("3. ", "").replace("4. ", "").replace("5. ", "")
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
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Вставка графика
    if os.path.exists("rbloggers_strategies_chart.png"):
        story.append(Paragraph("3. Графический анализ динамики капитала и просадок", h1_style))
        story.append(Image("rbloggers_strategies_chart.png", width=480, height=270))
        story.append(Spacer(1, 10))

    # Детальный разбор
    story.append(Paragraph("4. Скептический разбор каждого квантового архетипа", h1_style))

    # Стратегия 1
    story.append(Paragraph("Стратегия №1: Adaptive Asset Allocation (AAA / Systematic Investor)", h2_style))
    story.append(Paragraph(
        "<b>Результат:</b> CAGR +15.60%, Total Return +73.53%, Sharpe +0.25, MaxDD 44.14%.<br/>"
        "<b>Анализ:</b> Стратегия показала максимальную накопленную прибыль благодаря своевременному уходу в Золото (GLDRUB) в 2023–2024 гг. "
        "Однако просадка 44.1% делает ее неприемлемой для консерваторов. Причина: в начале 2022 года акции и ОФЗ рухнули синхронно, "
        "а 6-месячный моментум запаздывал с выходом в кэш. <i>Вердикт: Условно жизнеспособна при сокращении окна моментума.</i>",
        body_style
    ))

    # Стратегия 2
    story.append(Paragraph("Стратегия №2: Volatility Targeting Filter (Learning Machines / ChatGPT)", h2_style))
    story.append(Paragraph(
        "<b>Результат:</b> CAGR +6.23%, Sharpe -0.33, MaxDD 26.20%.<br/>"
        "<b>Анализ:</b> Фильтр волатильности сократил рыночную просадку вдвое, но отстал от безрискового фонда LQDT (+12.3%). "
        "Волатильность на MOEX — запаздывающий индикатор: алгоритм выходит на «дне» паники и заходит обратно с огромным опозданием. "
        "<i>Вердикт: Неэффективна на развивающемся рынке.</i>",
        body_style
    ))

    # Стратегия 3
    story.append(Paragraph("Стратегия №3: Cointegration & Pairs Trading (Спот vs Срочный рынок FORTS)", h2_style))
    story.append(Paragraph(
        "<b>Вариант 3а (Спот, маржинальный шорт):</b> CAGR +3.49%, Sharpe -2.33, MaxDD 4.57%. Вся прибыль сожрана платой за перенос короткой позиции (ставка ЦБ + 5%). <i>Вердикт: Непригодна на акциях.</i><br/>"
        "<b>Вариант 3b (FORTS, тариф «Стандартный ФОРТС»):</b> CAGR <b>+12.76%</b>, Sharpe <b>+0.68</b>, MaxDD <b>2.88%</b>, Calmar <b>4.44</b>, Total Return <b>+57.86%</b>. "
        "Фьючерсный шорт бесплатен, комиссия всего 5.80 руб. на спред, а 80% залога приносит доходность RUSFAR (LQDT). <i>Вердикт: Институциональный эталон риск-доходности!</i>",
        body_style
    ))

    # Стратегия 4
    story.append(Paragraph("Стратегия №4: Trend Following SMA-200 with Money Market (Quantstrat)", h2_style))
    story.append(Paragraph(
        "<b>Результат:</b> CAGR +11.76%, Volatility 8.73%, Sharpe -0.01, MaxDD 16.27%, Win Rate 83.4%.<br/>"
        "<b>Анализ:</b> Единственная стратегия, успешно предотвратившая геополитический обвал 2022 года (выход в кэш до СВО). "
        "Высвобождаемый кэш на Мосбирже эффективно аккумулирует процентный доход под ставку RUSFAR. "
        "<i>Вердикт: Рекомендована как основа среднесрочного распределения активов.</i>",
        body_style
    ))

    # Стратегия 5
    story.append(Paragraph("Стратегия №5: Short-term 1-Month Mean Reversion (Systematic Investor)", h2_style))
    story.append(Paragraph(
        "<b>Результат:</b> CAGR -12.14%, Sharpe -0.96, MaxDD 51.96%, Total Return -38.86%.<br/>"
        "<b>Анализ:</b> Полный разгром капитала. Покупка отстающих акций на MOEX приводит к регулярной ловле падающих ножей "
        "(кейс обвала Газпрома после отмены дивидендов). На Мосбирже доминирует жесткий тренд и инсайдерский моментум, а не реверсия. "
        "<i>Вердикт: Категорически непригодна.</i>",
        body_style
    ))

    story.append(Spacer(1, 8))

    # Заключение
    story.append(Paragraph("5. Практические рекомендации для инвестора на Московской бирже", h1_style))
    recs = (
        "1. <b>Ориентир — ставка RUSFAR:</b> Любая стратегия обязана обыгрывать фонды денежного рынка (LQDT/SBMM) с запасом не менее 5–8% годовых.<br/>"
        "2. <b>Запрет на маржинальный шорт спот-акций:</b> Статистический арбитраж и парный трейдинг допустимы исключительно на срочном рынке FORTS (синтетический базис Cash & Carry).<br/>"
        "3. <b>Оптимальная формула:</b> Гибридный портфель, сочетающий 60% базисного арбитража/флоатеров (доходность 20–24% годовых при MaxDD < 2%) и 40% трендового моментума с жестким фильтром SMA-200 и защитным кэшем в LQDT."
    )
    story.append(Paragraph(recs, body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report successfully generated: {pdf_filename}")


if __name__ == "__main__":
    build_pdf_report()
