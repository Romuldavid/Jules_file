"""
smartlab_parser.py
Универсальный, понятный и нативный парсер финансовых данных и отчетности со Smart-Lab.ru.

Возможности:
1. get_fundamental_screener() - парсинг сводной таблицы фундаментального анализа акций РФ
   (выручка, чистая прибыль, P/E, P/S, P/B, EV/EBITDA, дивидендная доходность, долг/EBITDA)
2. get_company_financials(ticker) - парсинг многолетней детальной финансовой отчетности МСФО/РСБУ
   (динамика за 5-10 лет: выручка, EBITDA, чистая прибыль, чистый долг, дивиденды, FCF)
3. prepare_for_analysis(df) - автоматическая очистка и перевод всех строковых колонок в числовой вид (float)
4. filter_stocks(...) - готовый скринер для инвестора (недооцененные акции, дивидендные аристократы)
"""

import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def clean_number(val):
    """
    Преобразует строку из Smart-Lab в чистое число (float).
    Примеры:
      '4 179' -> 4179.0
      '11.2%' -> 11.2
      '-0.3'  -> -0.3
      '505%'  -> 505.0
      '-' / '' / None -> None
    """
    if pd.isna(val) or val is None:
        return None
    val_str = str(val).strip().replace("\xa0", " ").replace(" ", "")
    if val_str in ["-", "", "—", "None", "nan"]:
        return None

    # Удаление знака %
    is_percent = False
    if val_str.endswith("%"):
        is_percent = True
        val_str = val_str[:-1]

    # Замена запятой на точку
    val_str = val_str.replace(",", ".")

    # Поиск чисел (включая отрицательные)
    match = re.search(r"[-+]?\d*\.?\d+", val_str)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def get_fundamental_screener(include_banks=True):
    """
    Загружает актуальный скринер акций и мультипликаторов со Smart-Lab.
    URL: https://smart-lab.ru/q/shares_fundamental/

    Возвращает pandas.DataFrame со стандартизированными числовыми колонками.
    """
    url = "https://smart-lab.ru/q/shares_fundamental/"
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Ошибка при запросе к {url}: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "lxml")
    tables = soup.find_all("table")
    if not tables:
        print("Таблицы не найдены на странице.")
        return pd.DataFrame()

    all_companies = []

    # Таблица 0: Обычные компании (производство, ритейл, нефтегаз, энергетика)
    t0 = tables[0]
    rows0 = t0.find_all("tr")
    for row in rows0[1:]:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        # Пропускаем пустые или неполные строки
        if len(cells) < 18:
            continue
        # Позиции в таблице 0:
        # 0: №, 1: Название, 2: Тикер, 5: Капит-я, 6: EV, 7: Выручка, 8: Чистая прибыль,
        # 9: ДД ао %, 10: ДД ап %, 11: ДД/ЧП %, 12: P/E, 13: P/S, 14: P/B, 15: EV/EBITDA,
        # 16: Рентаб EBITDA, 17: Долг/EBITDA, 18: Отчет
        item = {
            "name": cells[1],
            "ticker": cells[2],
            "sector": "Реальный сектор",
            "market_cap_bln": clean_number(cells[5]),
            "ev_bln": clean_number(cells[6]),
            "revenue_bln": clean_number(cells[7]),
            "net_income_bln": clean_number(cells[8]),
            "div_yield_ao_pct": clean_number(cells[9]),
            "div_yield_ap_pct": clean_number(cells[10]) if len(cells) > 10 else None,
            "pe": clean_number(cells[12]) if len(cells) > 12 else None,
            "ps": clean_number(cells[13]) if len(cells) > 13 else None,
            "pb": clean_number(cells[14]) if len(cells) > 14 else None,
            "ev_ebitda": clean_number(cells[15]) if len(cells) > 15 else None,
            "ebitda_margin_pct": clean_number(cells[16]) if len(cells) > 16 else None,
            "net_debt_ebitda": clean_number(cells[17]) if len(cells) > 17 else None,
            "report_standard": cells[18] if len(cells) > 18 else "",
        }
        all_companies.append(item)

    # Таблица 1: Банки и финансовый сектор
    if include_banks and len(tables) > 1:
        t1 = tables[1]
        rows1 = t1.find_all("tr")
        for row in rows1[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 16:
                continue
            item = {
                "name": cells[1],
                "ticker": cells[2],
                "sector": "Банки и финансы",
                "market_cap_bln": clean_number(cells[5]),
                "ev_bln": clean_number(cells[5]),  # Для банков EV ~ Market Cap
                "revenue_bln": clean_number(cells[6]),  # Чистый операционный доход
                "net_income_bln": clean_number(cells[7]),
                "div_yield_ao_pct": clean_number(cells[8]),
                "div_yield_ap_pct": clean_number(cells[9]) if len(cells) > 9 else None,
                "pe": clean_number(cells[11]) if len(cells) > 11 else None,
                "ps": None,
                "pb": clean_number(cells[12]) if len(cells) > 12 else None,
                "ev_ebitda": None,
                "ebitda_margin_pct": clean_number(cells[14]) if len(cells) > 14 else None,  # RoE
                "net_debt_ebitda": None,
                "report_standard": cells[16] if len(cells) > 16 else "",
            }
            all_companies.append(item)

    df = pd.DataFrame(all_companies)
    return df


def get_company_financials(ticker):
    """
    Загружает подробную историю финансовой отчетности компании по годам (МСФО/РСБУ).
    URL: https://smart-lab.ru/q/{ticker}/f/y/

    Возвращает pandas.DataFrame, где строки - это годы, а колонки - финансовые показатели:
    - Выручка (млрд руб)
    - Операционная прибыль / EBITDA
    - Чистая прибыль
    - Чистый долг
    - Капитальные затраты (CAPEX)
    - Свободный денежный поток (FCF)
    - Дивиденды на акцию и дивдоходность
    """
    ticker_clean = ticker.upper().strip()
    url = f"https://smart-lab.ru/q/{ticker_clean}/f/y/"
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Ошибка при запросе отчета для {ticker_clean}: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "lxml")
    table = soup.find("table")
    if not table:
        print(f"Таблица отчетности для {ticker_clean} не найдена.")
        return pd.DataFrame()

    rows = table.find_all("tr")
    if len(rows) < 3:
        return pd.DataFrame()

    # 3-я строка (индекс 2) обычно содержит годы: ['Лукойл', '', '2021', '2022', '2023', '2024', '2025']
    years_row = [c.get_text(strip=True) for c in rows[2].find_all(["th", "td"])]

    # Находим индексы колонок с годами
    year_cols = {}
    for idx, col in enumerate(years_row):
        if re.match(r"^20\d\d$", col):
            year_cols[idx] = col

    if not year_cols:
        # Попробуем 4-ю строку
        years_row = [c.get_text(strip=True) for c in rows[3].find_all(["th", "td"])]
        for idx, col in enumerate(years_row):
            if re.match(r"^20\d\d$", col):
                year_cols[idx] = col

    # Собираем данные построчно
    financial_data = {yr: {} for yr in year_cols.values()}

    for row in rows[3:]:
        cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if not cells or not cells[0]:
            continue
        metric_name = cells[0]

        for col_idx, yr in year_cols.items():
            if col_idx < len(cells):
                raw_val = cells[col_idx]
                val = clean_number(raw_val)
                financial_data[yr][metric_name] = val

    # Преобразуем в структурированный DataFrame
    df = pd.DataFrame.from_dict(financial_data, orient="index")
    df.index.name = "Year"
    df = df.sort_index()

    return df


def filter_undervalued_dividend_stocks(df, max_pe=10.0, min_div_yield=7.0, max_debt_ebitda=2.5):
    """
    Инвестиционный фильтр: отбирает недооцененные компании с хорошими дивидендами и низкой долговой нагрузкой.
    """
    filtered = df.copy()
    if "pe" in filtered.columns:
        filtered = filtered[(filtered["pe"] > 0) & (filtered["pe"] <= max_pe)]
    if "div_yield_ao_pct" in filtered.columns:
        filtered = filtered[filtered["div_yield_ao_pct"] >= min_div_yield]
    if "net_debt_ebitda" in filtered.columns:
        filtered = filtered[(filtered["net_debt_ebitda"].isna()) | (filtered["net_debt_ebitda"] <= max_debt_ebitda)]
    return filtered.sort_values(by="div_yield_ao_pct", ascending=False)


if __name__ == "__main__":
    print("=" * 80)
    print("ЗАПУСК ПАРСЕРА SMART-LAB: ФУНДАМЕНТАЛЬНЫЙ АНАЛИЗ И ОТЧЕТНОСТЬ")
    print("=" * 80)

    # 1. Загрузка общего скринера
    print("\n1. Загрузка скринера всех компаний...")
    screener_df = get_fundamental_screener(include_banks=True)
    print(f"Успешно спарсено компаний: {len(screener_df)}")
    print(screener_df[["name", "ticker", "market_cap_bln", "pe", "div_yield_ao_pct", "net_debt_ebitda"]].head(10))

    # Сохраняем в CSV
    screener_df.to_csv("smartlab_fundamental_screener.csv", index=False, encoding="utf-8-sig")
    print("Скринер сохранен в 'smartlab_fundamental_screener.csv'")

    # 2. Пример фильтрации для инвестора (Alpha & Value)
    print("\n2. Фильтрация недооцененных дивидендных компаний (P/E <= 10, ДД >= 7%, Долг/EBITDA <= 2.5):")
    best_stocks = filter_undervalued_dividend_stocks(screener_df, max_pe=10.0, min_div_yield=7.0, max_debt_ebitda=2.5)
    print(f"Отобрано перспективных бумаг: {len(best_stocks)}")
    cols_show = ["name", "ticker", "market_cap_bln", "pe", "div_yield_ao_pct", "net_debt_ebitda"]
    print(best_stocks[cols_show].head(10).to_string(index=False))

    # 3. Детальная финансовая отчетность по годам (на примере LKOH)
    print("\n3. Загрузка финансовой отчетности МСФО по годам для Лукойл (LKOH):")
    lkoh_fin = get_company_financials("LKOH")
    print(f"Доступные годы: {list(lkoh_fin.index)}")
    print(lkoh_fin.iloc[:, :6].to_string())

    # Сохраняем отчетность Лукойла
    lkoh_fin.to_csv("smartlab_lkoh_financials.csv", encoding="utf-8-sig")
    print("Отчетность Лукойла сохранена в 'smartlab_lkoh_financials.csv'")
