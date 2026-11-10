import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 🎯 Поиск букмекерских вилок (Surebets / Arbitrage) с мультимаркетами\n",
    "Программа выполняет поиск арбитражных ситуаций по 3 ключевым шагам:\n",
    "- **Шаг 1:** Асинхронный многопоточный сбор (Исходы + Тоталы + Форы) с одновременным запросом рынков и поддержкой зеркала реальной линии при исчерпании лимитов.\n",
    "- **Шаг 2:** Объединение рынков и кросс-букмекерский мэтчинг событий (Fuzzy matching + транслитерация).\n",
    "- **Шаг 3:** Поиск вилок по всем типам рынков (включая **жесткие 2-исхода на Тотал Больше/Меньше**) с расчетом ставок на банк 10 000 руб."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Установка зависимостей в среде Google Colab\n",
    "!pip install -q pandas requests beautifulsoup4 rapidfuzz tabulate"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Запуск полного трехшагового пайплайна поиска вилок в реальном времени\n",
    "from arbitrage_scanner import ArbitrageScanner\n",
    "\n",
    "scanner = ArbitrageScanner(\n",
    "    bank=10000.0,       # Банк для ставок в рублях\n",
    "    min_profit=0.2,     # Минимальная чистая выгода в %\n",
    "    max_profit=25.0,    # Фильтр от ошибок букмекерской линии\n",
    "    round_to=10         # Округление ставок до 10 руб (для безопасности)\n",
    ")\n",
    "\n",
    "# Шаг 1: Асинхронный многопоточный сбор (Исходы + Тоталы + Форы)\n",
    "scanner.load_multithreaded_data()\n",
    "\n",
    "# Шаг 2: Объединение рынков и кросс-букмекерский мэтчинг\n",
    "matched = scanner.match_events(threshold=78.0)\n",
    "\n",
    "# Шаг 3: Поиск вилок по всем типам рынков (включая жесткие 2-исхода на Тотал Больше/Меньше)\n",
    "surebets = scanner.scan_surebets(matched)\n",
    "\n",
    "# Вывод форматированного отчета: когда, на что и сколько ставить\n",
    "scanner.print_arbitrage_report(surebets)\n",
    "\n",
    "# Экспорт найденных вилок в CSV\n",
    "scanner.export_to_csv(surebets, 'arbitrage_bets.csv')\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Отображение вилок на жесткие 2-исхода (Тотал Больше / Меньше) в таблице\n",
    "import pandas as pd\n",
    "df_res = pd.read_csv('arbitrage_bets.csv')\n",
    "if not df_res.empty:\n",
    "    df_totals = df_res[df_res['market'].str.contains('Тотал', na=False)]\n",
    "    print(f'Найдено вилок на Тотал Больше/Меньше: {len(df_totals)}')\n",
    "    display(df_totals[['event', 'sport', 'time', 'market', 'profit_pct', 'min_profit_rub', 'outcome1', 'stake1', 'outcome2', 'stake2']].head(15))\n",
    "else:\n",
    "    print('В данный момент вилок не найдено. Запустите повторно перед началом матчей.')"
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}

with open("colab_arbitrage_scanner.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print("colab_arbitrage_scanner.ipynb обновлен.")
