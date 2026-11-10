import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 🎯 Поиск букмекерских вилок (Surebets / Arbitrage) в реальном времени\n",
    "Данный блокнот Google Colab предназначен для:\n",
    "1. **Сбора коэффициентов** официальных БК РФ (Бетсити, Марафон, Фонбет, PARI) в `.csv` файлы.\n",
    "2. **Интеллектуального сопоставления матчей** (Fuzzy matching + транслитерация) между разными букмекерами.\n",
    "3. **Поиска арбитражных ситуаций (вилок)**: 2-исходные (Тоталы, Двойные шансы) и 3-исходные (Исход 1X2).\n",
    "4. **Расчета ставок на банк 10 000 руб**: точные суммы ставок с округлением, гарантированная выгода и время проведения событий."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Шаг 1: Установка необходимых библиотек\n",
    "!pip install -q pandas requests beautifulsoup4 rapidfuzz tabulate"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Шаг 2: Скачивание актуальных модулей парсера и анализатора вилок\n",
    "# Если файлы уже в сессии Colab, они будут использованы напрямую\n",
    "import os\n",
    "print('Текущие файлы в рабочей директории:', os.listdir('.'))\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Шаг 3: Сбор коэффициентов с БК Бетсити и Марафон\n",
    "!python3 sports_odds_parser.py --limit 300 --output bookmaker_odds.csv\n",
    "# Сбор коэффициентов с БК Фонбет и PARI\n",
    "!python3 parse_fonbet_pari.py"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Шаг 4: Запуск анализатора вилок на собранных CSV\n",
    "# Банк 10 000 руб, минимальная выгода 0.2%, округление ставок до 10 руб\n",
    "from arbitrage_scanner import ArbitrageScanner\n",
    "\n",
    "scanner = ArbitrageScanner(\n",
    "    bank=10000.0,\n",
    "    min_profit=0.2,\n",
    "    max_profit=25.0,\n",
    "    round_to=10\n",
    ")\n",
    "\n",
    "# Загружаем данные из файлов CSV\n",
    "csv_files = ['bookmaker_odds.csv', 'fonbet_odds.csv', 'pari_odds.csv']\n",
    "scanner.load_data(csv_files)\n",
    "\n",
    "# Сопоставляем события между БК\n",
    "matched = scanner.match_events(threshold=78.0)\n",
    "\n",
    "# Сканируем и вычисляем вилки\n",
    "surebets = scanner.scan_surebets(matched)\n",
    "\n",
    "# Выводим наглядные рекомендации: когда, на что и сколько ставить\n",
    "scanner.print_arbitrage_report(surebets)\n",
    "\n",
    "# Экспортируем в CSV файл\n",
    "scanner.export_to_csv(surebets, 'arbitrage_bets.csv')\n",
    "print(' Готово! Результаты также сохранены в файл arbitrage_bets.csv')\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Шаг 5: Просмотр топ-10 самых выгодных вилок в табличном виде\n",
    "import pandas as pd\n",
    "df_res = pd.read_csv('arbitrage_bets.csv')\n",
    "if not df_res.empty:\n",
    "    display(df_res[['event', 'sport', 'time', 'market', 'profit_pct', 'min_profit_rub', 'outcome1', 'stake1', 'outcome2', 'stake2', 'outcome3', 'stake3']].head(10))\n",
    "else:\n",
    "    print('В данный момент вилок не найдено. Повторите запуск перед началом ближайших матчей.')"
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

print("colab_arbitrage_scanner.ipynb создан успешно.")
