#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
arbitrage_scanner.py
--------------------
Программа для анализа и поиска букмекерских вилок (арбитражных ситуаций)
на основе CSV-файлов с коэффициентами спортивных событий.

Функционал:
1. Загрузка данных из одного или нескольких CSV-файлов.
2. Интеллектуальное сопоставление событий между БК (Fuzzy matching).
3. Поиск 2-исходных вилок:
   - Тотал Больше / Тотал Меньше (ТБ vs ТМ при одинаковом значении тотала)
   - Фора 1 / Фора 2 (Ф1(+X) vs Ф2(-X))
   - Двойной исход vs Противоположный исход (1X vs П2, X2 vs П1, 12 vs X)
4. Поиск 3-исходных вилок:
   - Исход матча (П1, X, П2)
5. Расчет оптимальных ставок для заданного банка (по умолчанию 10 000 руб):
   - Округление ставок до 10 руб (для реалистичности и минимизации внимания СБ)
   - Расчет гарантированной прибыли в рублях и % доходности.
6. Экспорт найденных вилок в CSV и наглядный вывод в терминал.
"""

import sys
import re
import os
import argparse
import datetime
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

try:
    from rapidfuzz import fuzz
except ImportError:
    # Запасной вариант если rapidfuzz не установлен
    import difflib
    class FuzzFallback:
        @staticmethod
        def token_sort_ratio(s1: str, s2: str) -> float:
            return difflib.SequenceMatcher(None, sorted(s1.split()), sorted(s2.split())).ratio() * 100
        @staticmethod
        def ratio(s1: str, s2: str) -> float:
            return difflib.SequenceMatcher(None, s1, s2).ratio() * 100
    fuzz = FuzzFallback()


TRANSLIT_DICT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
}

def transliterate(text: str) -> str:
    """Транслитерирует русский текст в латиницу для сопоставления между ру/англ написанием."""
    res = []
    for char in text.lower():
        res.append(TRANSLIT_DICT.get(char, char))
    return "".join(res)

def clean_team_name(name: str) -> str:
    """Очищает, транслитерирует и нормализует название команды/спортсмена."""
    if not isinstance(name, str):
        return ""
    name = name.lower()
    # Удаление кавычек, спецсимволов и лишних знаков
    name = re.sub(r'["\'`«»()\[\]{}]', ' ', name)
    # Замена дефисов и подчеркиваний на пробелы
    name = re.sub(r'[-_./\\]', ' ', name)
    # Удаление частых приставок команд
    stop_words = {
        'фк', 'хк', 'бк', 'вк', 'пфк', 'fc', 'hc', 'bc', 'fk', 'sk', 'club', 'team',
        'жфк', 'women', 'жен', 'муж', 'u19', 'u20', 'u21', 'u23', 'ю19', 'ю21',
        'молодежь', 'резерв', 'дубль', '2', 'ii'
    }
    tokens = [t for t in name.split() if t not in stop_words]
    cleaned = " ".join(tokens).strip()
    return transliterate(cleaned)


def calculate_arbitrage_2way(k1: float, k2: float, bank: float = 10000.0, round_to: int = 10) -> Optional[Dict[str, Any]]:
    """
    Рассчитывает параметры 2-исходной вилки.
    L = 1/k1 + 1/k2. Вилка существует, если L < 1.0.
    """
    if k1 <= 1.01 or k2 <= 1.01:
        return None
    inv_sum = (1.0 / k1) + (1.0 / k2)
    if inv_sum >= 1.0:
        return None  # Нет вилки

    profit_pct = (1.0 / inv_sum - 1.0) * 100.0

    # Идеальные ставки
    stake1_exact = bank / (k1 * inv_sum)
    stake2_exact = bank / (k2 * inv_sum)

    # Округление ставок
    if round_to > 0:
        stake1 = round(stake1_exact / round_to) * round_to
        stake2 = round(stake2_exact / round_to) * round_to
    else:
        stake1 = round(stake1_exact, 2)
        stake2 = round(stake2_exact, 2)

    total_invested = stake1 + stake2
    win1 = stake1 * k1 - total_invested
    win2 = stake2 * k2 - total_invested
    min_profit = min(win1, win2)

    return {
        'type': '2-исходная',
        'inv_sum': round(inv_sum, 4),
        'profit_pct': round(profit_pct, 2),
        'bank': bank,
        'total_invested': total_invested,
        'stake1': stake1,
        'stake2': stake2,
        'win1': round(win1, 2),
        'win2': round(win2, 2),
        'min_profit_rub': round(min_profit, 2)
    }


def calculate_arbitrage_3way(k1: float, kx: float, k2: float, bank: float = 10000.0, round_to: int = 10) -> Optional[Dict[str, Any]]:
    """
    Рассчитывает параметры 3-исходной вилки (П1, X, П2).
    L = 1/k1 + 1/kx + 1/k2. Вилка существует, если L < 1.0.
    """
    if k1 <= 1.01 or kx <= 1.01 or k2 <= 1.01:
        return None
    inv_sum = (1.0 / k1) + (1.0 / kx) + (1.0 / k2)
    if inv_sum >= 1.0:
        return None

    profit_pct = (1.0 / inv_sum - 1.0) * 100.0

    stake1_exact = bank / (k1 * inv_sum)
    stakex_exact = bank / (kx * inv_sum)
    stake2_exact = bank / (k2 * inv_sum)

    if round_to > 0:
        stake1 = round(stake1_exact / round_to) * round_to
        stakex = round(stakex_exact / round_to) * round_to
        stake2 = round(stake2_exact / round_to) * round_to
    else:
        stake1 = round(stake1_exact, 2)
        stakex = round(stakex_exact, 2)
        stake2 = round(stake2_exact, 2)

    total_invested = stake1 + stakex + stake2
    win1 = stake1 * k1 - total_invested
    winx = stakex * kx - total_invested
    win2 = stake2 * k2 - total_invested
    min_profit = min(win1, winx, win2)

    return {
        'type': '3-исходная',
        'inv_sum': round(inv_sum, 4),
        'profit_pct': round(profit_pct, 2),
        'bank': bank,
        'total_invested': total_invested,
        'stake1': stake1,
        'stake2': stakex,
        'stake3': stake2,
        'win1': round(win1, 2),
        'win2': round(winx, 2),
        'win3': round(win2, 2),
        'min_profit_rub': round(min_profit, 2)
    }


class ArbitrageScanner:
    """Класс для загрузки данных, матчинга матчей и поиска вилок."""

    def __init__(self, bank: float = 10000.0, min_profit: float = 0.1, max_profit: float = 25.0, round_to: int = 10):
        self.bank = bank
        self.min_profit = min_profit
        self.max_profit = max_profit  # Защита от явных опечаток/ошибок линии букмекера (>25%)
        self.round_to = round_to
        self.events_df = pd.DataFrame()

    def load_data(self, files: List[str]) -> pd.DataFrame:
        """Загружает данные из одного или нескольких CSV файлов."""
        dfs = []
        for f in files:
            if not os.path.exists(f):
                print(f"[ПРЕДУПРЕЖДЕНИЕ] Файл {f} не найден, пропускаем.")
                continue
            try:
                df = pd.read_csv(f)
                if not df.empty and 'bookmaker' in df.columns:
                    dfs.append(df)
                    print(f"[ИНФО] Загружено {len(df)} записей из {f} (БК: {df['bookmaker'].unique().tolist()})")
            except Exception as e:
                print(f"[ОШИБКА] Не удалось прочитать {f}: {e}")

        if not dfs:
            print("[ОШИБКА] Нет доступных данных для анализа.")
            self.events_df = pd.DataFrame()
            return self.events_df

        combined = pd.concat(dfs, ignore_index=True)
        # Очистка и нормализация
        combined['clean_t1'] = combined['team1'].fillna('').apply(clean_team_name)
        combined['clean_t2'] = combined['team2'].fillna('').apply(clean_team_name)
        self.events_df = combined
        print(f"[ИТОГО] Всего загружено {len(combined)} записей от {combined['bookmaker'].nunique()} букмекеров.")
        return combined

    def match_events(self, threshold: float = 78.0) -> List[Dict[str, Any]]:
        """
        Сопоставляет одинаковые события между разными букмекерами.
        Группирует по виду спорта для ускорения.
        """
        if self.events_df.empty:
            return []

        bks = self.events_df['bookmaker'].unique()
        if len(bks) < 2:
            print(f"[ВНИМАНИЕ] В данных представлен только один букмекер: {bks}. Для поиска вилок нужно минимум два!")
            return []

        matched_pairs = []
        # Разделим по видам спорта
        sports = self.events_df['sport'].fillna('Другое').unique()

        for sport in sports:
            sport_df = self.events_df[self.events_df['sport'] == sport].copy()
            # Сравним букмекеров попарно
            for i in range(len(bks)):
                bk1 = bks[i]
                df1 = sport_df[sport_df['bookmaker'] == bk1]
                if df1.empty:
                    continue
                for j in range(i + 1, len(bks)):
                    bk2 = bks[j]
                    df2 = sport_df[sport_df['bookmaker'] == bk2]
                    if df2.empty:
                        continue

                    for _, row1 in df1.iterrows():
                        t1_1, t1_2 = row1['clean_t1'], row1['clean_t2']
                        if not t1_1 or not t1_2:
                            continue

                        best_match = None
                        best_score = 0.0

                        for _, row2 in df2.iterrows():
                            t2_1, t2_2 = row2['clean_t1'], row2['clean_t2']
                            if not t2_1 or not t2_2:
                                continue

                            # Сравнение команда 1 и команда 2
                            score_direct = (fuzz.token_sort_ratio(t1_1, t2_1) + fuzz.token_sort_ratio(t1_2, t2_2)) / 2.0
                            score_rev = (fuzz.token_sort_ratio(t1_1, t2_2) + fuzz.token_sort_ratio(t1_2, t2_1)) / 2.0
                            score = max(score_direct, score_rev)

                            if score > best_score:
                                best_score = score
                                best_match = row2

                        if best_score >= threshold and best_match is not None:
                            matched_pairs.append({
                                'sport': sport,
                                'match_name': f"{row1['team1']} — {row1['team2']}",
                                'time': row1.get('event_time') or best_match.get('event_time') or "Ближайшее время",
                                'bk1_row': row1,
                                'bk2_row': best_match,
                                'similarity': best_score
                            })

        print(f"[ИНФО] Найдено {len(matched_pairs)} парных совпадений матчей между БК.")
        return matched_pairs

    def scan_surebets(self, matched_pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ищет арбитражные ситуации по всем маркетам для найденных пар матчей."""
        surebets = []

        for pair in matched_pairs:
            r1 = pair['bk1_row']
            r2 = pair['bk2_row']
            bk1 = r1['bookmaker']
            bk2 = r2['bookmaker']
            match_name = pair['match_name']
            ev_time = pair['time']
            sport = pair['sport']

            # -------------------------------------------------------------
            # 1. 3-way: П1 - X - П2
            # -------------------------------------------------------------
            # Возможные комбинации между двумя БК:
            # (BK1: П1, BK2: X, BK2: П2) или (BK1: П1, BK1: X, BK2: П2) и т.д.
            # Для каждого исхода берем максимальный кф:
            k1_best, bk_p1 = (r1['P1'], bk1) if float(r1.get('P1') or 0) >= float(r2.get('P1') or 0) else (r2['P1'], bk2)
            kx_best, bk_px = (r1['X'], bk1) if float(r1.get('X') or 0) >= float(r2.get('X') or 0) else (r2['X'], bk2)
            k2_best, bk_p2 = (r1['P2'], bk1) if float(r1.get('P2') or 0) >= float(r2.get('P2') or 0) else (r2['P2'], bk2)

            # Проверяем, что кэфы от РАЗНЫХ БК (иначе это маржа одного БК)
            if len({bk_p1, bk_px, bk_p2}) > 1 and all(pd.notna(k) and float(k) > 1.01 for k in [k1_best, kx_best, k2_best]):
                k1, kx, k2 = float(k1_best), float(kx_best), float(k2_best)
                arb = calculate_arbitrage_3way(k1, kx, k2, self.bank, self.round_to)
                if arb and self.min_profit <= arb['profit_pct'] <= self.max_profit:
                    surebets.append({
                        'event': match_name,
                        'sport': sport,
                        'time': ev_time,
                        'market': 'Исход матча (1X2)',
                        'profit_pct': arb['profit_pct'],
                        'min_profit_rub': arb['min_profit_rub'],
                        'invested': arb['total_invested'],
                        'outcome1': f"Победа 1 в {bk_p1} (кф {k1})",
                        'stake1': arb['stake1'],
                        'outcome2': f"Ничья (X) в {bk_px} (кф {kx})",
                        'stake2': arb['stake2'],
                        'outcome3': f"Победа 2 в {bk_p2} (кф {k2})",
                        'stake3': arb['stake3'],
                        'details': arb
                    })

            # -------------------------------------------------------------
            # 2. 2-way: Тотал (ТБ / ТМ) при одинаковом значении
            # -------------------------------------------------------------
            tot1_val = str(r1.get('Total_val', '')).strip().replace('+', '')
            tot2_val = str(r2.get('Total_val', '')).strip().replace('+', '')

            if tot1_val and tot2_val and tot1_val == tot2_val and tot1_val != 'nan':
                # Вариант А: ТБ в BK1, ТМ в BK2
                tb1 = float(r1.get('Total_over') or 0)
                tm2 = float(r2.get('Total_under') or 0)
                if tb1 > 1.01 and tm2 > 1.01:
                    arb = calculate_arbitrage_2way(tb1, tm2, self.bank, self.round_to)
                    if arb and self.min_profit <= arb['profit_pct'] <= self.max_profit:
                        surebets.append({
                            'event': match_name,
                            'sport': sport,
                            'time': ev_time,
                            'market': f"Тотал ({tot1_val})",
                            'profit_pct': arb['profit_pct'],
                            'min_profit_rub': arb['min_profit_rub'],
                            'invested': arb['total_invested'],
                            'outcome1': f"Тотал Больше ({tot1_val}) в {bk1} (кф {tb1})",
                            'stake1': arb['stake1'],
                            'outcome2': f"Тотал Меньше ({tot1_val}) в {bk2} (кф {tm2})",
                            'stake2': arb['stake2'],
                            'outcome3': '-',
                            'stake3': 0,
                            'details': arb
                        })
                # Вариант Б: ТМ в BK1, ТБ в BK2
                tm1 = float(r1.get('Total_under') or 0)
                tb2 = float(r2.get('Total_over') or 0)
                if tm1 > 1.01 and tb2 > 1.01:
                    arb = calculate_arbitrage_2way(tm1, tb2, self.bank, self.round_to)
                    if arb and self.min_profit <= arb['profit_pct'] <= self.max_profit:
                        surebets.append({
                            'event': match_name,
                            'sport': sport,
                            'time': ev_time,
                            'market': f"Тотал ({tot1_val})",
                            'profit_pct': arb['profit_pct'],
                            'min_profit_rub': arb['min_profit_rub'],
                            'invested': arb['total_invested'],
                            'outcome1': f"Тотал Меньше ({tot1_val}) в {bk1} (кф {tm1})",
                            'stake1': arb['stake1'],
                            'outcome2': f"Тотал Больше ({tot1_val}) в {bk2} (кф {tb2})",
                            'stake2': arb['stake2'],
                            'outcome3': '-',
                            'stake3': 0,
                            'details': arb
                        })

            # -------------------------------------------------------------
            # 3. 2-way: Двойные шансы (1X vs П2, X2 vs П1, 12 vs X)
            # -------------------------------------------------------------
            double_combos = [
                ('1X', 'P2', '1X (не проиграет 1)', 'П2 (победа 2)'),
                ('X2', 'P1', 'X2 (не проиграет 2)', 'П1 (победа 1)'),
                ('12', 'X', '12 (не будет ничьей)', 'X (ничья)')
            ]

            for d_col, s_col, d_name, s_name in double_combos:
                # Вариант 1: Двойной в BK1, Одиночный в BK2
                k_d1 = float(r1.get(d_col) or 0)
                k_s2 = float(r2.get(s_col) or 0)
                if k_d1 > 1.01 and k_s2 > 1.01:
                    arb = calculate_arbitrage_2way(k_d1, k_s2, self.bank, self.round_to)
                    if arb and self.min_profit <= arb['profit_pct'] <= self.max_profit:
                        surebets.append({
                            'event': match_name,
                            'sport': sport,
                            'time': ev_time,
                            'market': f"Двойной шанс: {d_col} / {s_col}",
                            'profit_pct': arb['profit_pct'],
                            'min_profit_rub': arb['min_profit_rub'],
                            'invested': arb['total_invested'],
                            'outcome1': f"{d_name} в {bk1} (кф {k_d1})",
                            'stake1': arb['stake1'],
                            'outcome2': f"{s_name} в {bk2} (кф {k_s2})",
                            'stake2': arb['stake2'],
                            'outcome3': '-',
                            'stake3': 0,
                            'details': arb
                        })
                # Вариант 2: Двойной в BK2, Одиночный в BK1
                k_d2 = float(r2.get(d_col) or 0)
                k_s1 = float(r1.get(s_col) or 0)
                if k_d2 > 1.01 and k_s1 > 1.01:
                    arb = calculate_arbitrage_2way(k_d2, k_s1, self.bank, self.round_to)
                    if arb and self.min_profit <= arb['profit_pct'] <= self.max_profit:
                        surebets.append({
                            'event': match_name,
                            'sport': sport,
                            'time': ev_time,
                            'market': f"Двойной шанс: {d_col} / {s_col}",
                            'profit_pct': arb['profit_pct'],
                            'min_profit_rub': arb['min_profit_rub'],
                            'invested': arb['total_invested'],
                            'outcome1': f"{d_name} в {bk2} (кф {k_d2})",
                            'stake1': arb['stake1'],
                            'outcome2': f"{s_name} в {bk1} (кф {k_s1})",
                            'stake2': arb['stake2'],
                            'outcome3': '-',
                            'stake3': 0,
                            'details': arb
                        })

        # Сортировка по доходности по убыванию
        surebets.sort(key=lambda x: x['profit_pct'], reverse=True)
        return surebets

    def print_arbitrage_report(self, surebets: List[Dict[str, Any]]):
        """Выводит форматированный и наглядный отчет о найденных вилках."""
        print("\n" + "=" * 90)
        print("          ОТЧЕТ ПОИСКА БУКМЕКЕРСКИХ ВИЛОК (ARBITRAGE SUREBETS)          ")
        print(f"  Общий банк для ставок: {self.bank:,.2f} руб. | Округление ставок: до {self.round_to} руб.")
        print(f"  Время анализа: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 90)

        if not surebets:
            print("\n❌ На данный момент актуальных вилок с доходностью от "
                  f"{self.min_profit}% до {self.max_profit}% не обнаружено.")
            print("Совет: запустите повторный парсинг через 5-10 минут перед началом матчей.")
            print("=" * 90 + "\n")
            return

        print(f"\n Найдено арбитражных ситуаций: {len(surebets)}\n")

        for idx, arb in enumerate(surebets, 1):
            print(f"------------------------------------------------------------------------------------------")
            print(f" ВИЛКА #{idx}: {arb['event']}  |  Вид спорта: {arb['sport']}")
            print(f"⏰ Время матча (когда ставить): {arb['time']}")
            print(f" Рынок: {arb['market']}  |  Чистая доходность: +{arb['profit_pct']}%  |  Прибыль: +{arb['min_profit_rub']} руб.")
            print(f" РЕКОМЕНДАЦИЯ ПО СТАВКАМ (Банк {self.bank:.0f} руб.):")
            print(f"   1️⃣  {arb['outcome1']:<52}  => Ставить: {arb['stake1']:>6.0f} руб.")
            print(f"   2️⃣  {arb['outcome2']:<52}  => Ставить: {arb['stake2']:>6.0f} руб.")
            if arb.get('outcome3') and arb['outcome3'] != '-':
                print(f"   3️⃣  {arb['outcome3']:<52}  => Ставить: {arb['stake3']:>6.0f} руб.")
            print(f"   💰 Всего вложено: {arb['invested']:.0f} руб. | Гарантированная выплата при любом исходе: ~{arb['invested'] + arb['min_profit_rub']:.0f} руб.")

        print("=" * 90 + "\n")

    def export_to_csv(self, surebets: List[Dict[str, Any]], filename: str = "arbitrage_bets.csv"):
        """Экспортирует найденные вилки в CSV файл."""
        if not surebets:
            # Создаем пустой файл с заголовками
            df_empty = pd.DataFrame(columns=[
                'event', 'sport', 'time', 'market', 'profit_pct', 'min_profit_rub',
                'invested', 'outcome1', 'stake1', 'outcome2', 'stake2', 'outcome3', 'stake3'
            ])
            df_empty.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"[ИНФО] Вилок нет. Создан пустой файл {filename}.")
            return

        export_records = []
        for a in surebets:
            export_records.append({
                'event': a['event'],
                'sport': a['sport'],
                'time': a['time'],
                'market': a['market'],
                'profit_pct': a['profit_pct'],
                'min_profit_rub': a['min_profit_rub'],
                'invested': a['invested'],
                'outcome1': a['outcome1'],
                'stake1': a['stake1'],
                'outcome2': a['outcome2'],
                'stake2': a['stake2'],
                'outcome3': a.get('outcome3', '-'),
                'stake3': a.get('stake3', 0)
            })

        df = pd.DataFrame(export_records)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"[УСПЕХ] Экспортировано {len(df)} вилок в {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Анализатор букмекерских вилок (Surebets) из файлов CSV."
    )
    parser.add_argument(
        '--input', nargs='+', default=['bookmaker_odds.csv', 'fonbet_odds.csv', 'pari_odds.csv'],
        help="Один или несколько файлов CSV с коэффициентами БК."
    )
    parser.add_argument(
        '--bank', type=float, default=10000.0,
        help="Общий банк для распределения ставок в рублях (по умолчанию: 10000)."
    )
    parser.add_argument(
        '--min-profit', type=float, default=0.1,
        help="Минимальная доходность вилки в процентах (по умолчанию: 0.1%%)."
    )
    parser.add_argument(
        '--max-profit', type=float, default=25.0,
        help="Максимальная доходность вилки (фильтр от ошибок линии, по умолчанию: 25.0%%)."
    )
    parser.add_argument(
        '--round-to', type=int, default=10,
        help="Округление ставок (в рублях, например 10 или 50, по умолчанию: 10)."
    )
    parser.add_argument(
        '--output', default='arbitrage_bets.csv',
        help="Путь для сохранения найденных вилок (по умолчанию: arbitrage_bets.csv)."
    )

    # Игнорируем специфичные флаги ipykernel / colab (-f kernel-*.json)
    args, unknown = parser.parse_known_args()

    scanner = ArbitrageScanner(
        bank=args.bank,
        min_profit=args.min_profit,
        max_profit=args.max_profit,
        round_to=args.round_to
    )

    scanner.load_data(args.input)
    matched = scanner.match_events()
    surebets = scanner.scan_surebets(matched)
    scanner.print_arbitrage_report(surebets)
    scanner.export_to_csv(surebets, args.output)


if __name__ == '__main__':
    main()
