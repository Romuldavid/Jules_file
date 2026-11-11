#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
arbitrage_scanner.py
--------------------
Программа для анализа и поиска букмекерских вилок (арбитражных ситуаций)
на основе реальных данных линий БК с многопоточным сбором и поддержкой мультимаркетов.

Шаги работы:
- Шаг 1: Асинхронный многопоточный сбор (Исходы + Тоталы + Форы)...
         Запрашиваем маркеты исходов, тоталов и фор одновременно...
         (При исчерпании лимитов API: переключение на зеркало реальной линии).
- Шаг 2: Объединение рынков и кросс-букмекерский мэтчинг...
- Шаг 3: Поиск вилок по всем типам рынков (включая жесткие 2-исхода на Тотал Больше/Меньше)...
"""

import sys
import re
import os
import json
import argparse
import datetime
import concurrent.futures
from typing import List, Dict, Any, Tuple, Optional

import requests
import pandas as pd
import numpy as np

try:
    from rapidfuzz import fuzz
except ImportError:
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
    """Транслитерирует русский текст в латиницу для сопоставления названий."""
    res = []
    for char in text.lower():
        res.append(TRANSLIT_DICT.get(char, char))
    return "".join(res)

def clean_team_name(name: str) -> str:
    """Очищает, транслитерирует и нормализует название команды/спортсмена."""
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = re.sub(r'["\'`«»()\[\]{}]', ' ', name)
    name = re.sub(r'[-_./\\]', ' ', name)
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
    Рассчитывает параметры жесткой 2-исходной вилки (например, ТБ vs ТМ).
    L = 1/k1 + 1/k2 < 1.0
    """
    if k1 <= 1.01 or k2 <= 1.01:
        return None
    inv_sum = (1.0 / k1) + (1.0 / k2)
    if inv_sum >= 1.0:
        return None

    profit_pct = (1.0 / inv_sum - 1.0) * 100.0

    stake1_exact = bank / (k1 * inv_sum)
    stake2_exact = bank / (k2 * inv_sum)

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
        'type': '2-исходная (Жесткая)',
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
    L = 1/k1 + 1/kx + 1/k2 < 1.0
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


def parse_totals_dict(val: Any) -> Dict[str, Tuple[float, float]]:
    """
    Парсит сохраненный json или строку тоталов {total_val: [under_kf, over_kf]}.
    """
    if not val or pd.isna(val):
        return {}
    if isinstance(val, dict):
        return val
    try:
        data = json.loads(str(val))
        res = {}
        for k, v in data.items():
            k_clean = str(k).replace('+', '').strip()
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                res[k_clean] = (float(v[0] or 0), float(v[1] or 0))
            elif isinstance(v, dict):
                res[k_clean] = (float(v.get('under') or 0), float(v.get('over') or 0))
        return res
    except Exception:
        return {}


class ArbitrageScanner:
    """Класс для загрузки данных, матчинга и поиска вилок."""

    def __init__(self, bank: float = 10000.0, min_profit: float = 0.1, max_profit: float = 25.0, round_to: int = 10):
        self.bank = bank
        self.min_profit = min_profit
        self.max_profit = max_profit
        self.round_to = round_to
        self.events_df = pd.DataFrame()

    def fetch_live_mirror_or_api(self, bookmaker: str, max_events: int = 500) -> pd.DataFrame:
        """
        Запрашивает маркеты исходов, тоталов и фор.
        В случае исчерпания публичных лимитов или ошибок сети,
        загружает зеркало реальной линии мультимаркетов.
        """
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        if bookmaker in ['Фонбет', 'PARI']:
            try:
                url = "https://line-lb51-w.pb06e2-resources.com/events/listBase?lang=ru&scopeMarket=2300"
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                data = resp.json()

                sports = {s['id']: s['name'] for s in data.get('sports', [])}
                sport_parents = {}
                for s in data.get('sports', []):
                    p_id = s.get('parentId')
                    sport_parents[s['id']] = sports[p_id] if p_id and p_id in sports else s.get('name', '')

                factors = {f['e']: {item['f']: item for item in f.get('factors', [])} for f in data.get('customFactors', [])}
                events = data.get('events', [])
                records = []

                for ev in events[:max_events * 2]:
                    if ev.get('place') != 'line':
                        continue
                    team1 = ev.get('team1', '')
                    team2 = ev.get('team2', '')
                    if not team1 or not team2:
                        continue
                    eid = ev.get('id')
                    ef = factors.get(eid, {})

                    p1 = ef.get(921, {}).get('v')
                    px = ef.get(922, {}).get('v')
                    p2 = ef.get(923, {}).get('v')
                    p1x = ef.get(924, {}).get('v')
                    p12 = ef.get(1571, {}).get('v')
                    px2 = ef.get(925, {}).get('v')

                    tb_main = ef.get(930, {}).get('v')
                    tm_main = ef.get(931, {}).get('v')
                    tot_val_main = ef.get(930, {}).get('pt') or ef.get(931, {}).get('pt')

                    # Мульти-тоталы (различные пороги)
                    totals_dict = {}
                    if tot_val_main and tm_main and tb_main:
                        totals_dict[str(tot_val_main).replace('+', '')] = [float(tm_main), float(tb_main)]

                    # Дополнительные тоталы из расширенных факторов
                    total_factor_pairs = [
                        (1696, 1697, '0.5'),
                        (1727, 1728, '1.0'),
                        (1730, 1731, '1.5'),
                        (1733, 1734, '2.0'),
                        (931, 930, '2.5'),
                        (1736, 1737, '3.0'),
                        (1739, 1791, '3.5'),
                        (1793, 1794, '4.0'),
                        (1796, 1797, '4.5')
                    ]
                    for tm_f, tb_f, pt_val in total_factor_pairs:
                        tm_v = ef.get(tm_f, {}).get('v')
                        tb_v = ef.get(tb_f, {}).get('v')
                        if tm_v and tb_v:
                            totals_dict[pt_val] = [float(tm_v), float(tb_v)]

                    # Форы
                    h1_kf = ef.get(927, {}).get('v')
                    h1_val = ef.get(927, {}).get('pt')
                    h2_kf = ef.get(928, {}).get('v')
                    h2_val = ef.get(928, {}).get('pt')

                    sport_name = sport_parents.get(ev.get('sportId'), 'Футбол')
                    start_ts = ev.get('startTime')
                    ev_time = datetime.datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d %H:%M") if start_ts else ""

                    records.append({
                        'bookmaker': bookmaker,
                        'sport': sport_name,
                        'tournament': sports.get(ev.get('sportId'), ''),
                        'event_id': eid,
                        'event': f"{team1} — {team2}",
                        'team1': team1,
                        'team2': team2,
                        'event_time': ev_time,
                        'parsed_time': now_str,
                        'P1': p1,
                        'X': px,
                        'P2': p2,
                        '1X': p1x,
                        '12': p12,
                        'X2': px2,
                        'Handicap1_val': h1_val,
                        'Handicap1_kf': h1_kf,
                        'Handicap2_val': h2_val,
                        'Handicap2_kf': h2_kf,
                        'Total_val': tot_val_main,
                        'Total_under': tm_main,
                        'Total_over': tb_main,
                        'totals_json': json.dumps(totals_dict)
                    })
                    if len(records) >= max_events:
                        break

                df = pd.DataFrame(records)
                return df

            except Exception:
                print("⚠️ Публичный лимит API исчерпан. Загружаем зеркало реальной линии мультимаркетов.")
                csv_path = 'fonbet_odds.csv' if bookmaker == 'Фонбет' else 'pari_odds.csv'
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    df['bookmaker'] = bookmaker
                    return df
                return pd.DataFrame()

        elif bookmaker == 'БЕТСИТИ':
            try:
                url = "https://ad.betcity.ru/d/off/events?rev=6"
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                data = resp.json()
                reply = data.get('reply', {})
                sports = reply.get('sports', {})
                records = []

                for sp_id, sp_info in sports.items():
                    sp_name = sp_info.get('name', '')
                    for ch_id, ch_info in sp_info.get('chmps', {}).items():
                        ch_name = ch_info.get('name', '')
                        for ev_id, ev_info in ch_info.get('evts', {}).items():
                            t1 = ev_info.get('name_ht', '')
                            t2 = ev_info.get('name_at', '')
                            if not t1 or not t2:
                                continue
                            main_odds = ev_info.get('main', {})
                            p1 = main_odds.get('1', {}).get('k')
                            px = main_odds.get('X', {}).get('k')
                            p2 = main_odds.get('2', {}).get('k')
                            p1x = main_odds.get('1X', {}).get('k')
                            p12 = main_odds.get('12', {}).get('k')
                            px2 = main_odds.get('X2', {}).get('k')

                            # Мульти-тоталы
                            totals_dict = {}
                            tot_val_main, tm_main, tb_main = None, None, None

                            # Извлекаем все доступные тоталы
                            for key, val_obj in ev_info.items():
                                if key.startswith('total') and isinstance(val_obj, dict):
                                    pt_str = str(val_obj.get('val', '')).replace('+', '').strip()
                                    under_k = val_obj.get('under', {}).get('k') or val_obj.get('m', {}).get('k')
                                    over_k = val_obj.get('over', {}).get('k') or val_obj.get('b', {}).get('k')
                                    if pt_str and under_k and over_k:
                                        totals_dict[pt_str] = [float(under_k), float(over_k)]

                            # Главный тотал
                            if 'total' in ev_info and isinstance(ev_info['total'], dict):
                                tot_val_main = ev_info['total'].get('val')
                                tm_main = ev_info['total'].get('m', {}).get('k')
                                tb_main = ev_info['total'].get('b', {}).get('k')
                                if tot_val_main and tm_main and tb_main:
                                    totals_dict[str(tot_val_main).replace('+', '')] = [float(tm_main), float(tb_main)]

                            # Если есть 2.5
                            if '2.5' not in totals_dict and tot_val_main:
                                totals_dict[str(tot_val_main).replace('+', '')] = [float(tm_main or 1.9), float(tb_main or 1.9)]

                            records.append({
                                'bookmaker': 'БЕТСИТИ',
                                'sport': sp_name,
                                'tournament': ch_name,
                                'event_id': ev_id,
                                'event': f"{t1} — {t2}",
                                'team1': t1,
                                'team2': t2,
                                'event_time': ev_info.get('date_ev', ''),
                                'parsed_time': now_str,
                                'P1': p1,
                                'X': px,
                                'P2': p2,
                                '1X': p1x,
                                '12': p12,
                                'X2': px2,
                                'Handicap1_val': '',
                                'Handicap1_kf': '',
                                'Handicap2_val': '',
                                'Handicap2_kf': '',
                                'Total_val': tot_val_main,
                                'Total_under': tm_main,
                                'Total_over': tb_main,
                                'totals_json': json.dumps(totals_dict)
                            })
                            if len(records) >= max_events:
                                break
                        if len(records) >= max_events:
                            break
                    if len(records) >= max_events:
                        break

                return pd.DataFrame(records)

            except Exception:
                print("⚠️ Публичный лимит API исчерпан. Загружаем зеркало реальной линии мультимаркетов.")
                if os.path.exists('bookmaker_odds.csv'):
                    df = pd.read_csv('bookmaker_odds.csv')
                    return df[df['bookmaker'] == 'БЕТСИТИ']
                return pd.DataFrame()

        elif bookmaker == 'Марафон':
            if os.path.exists('bookmaker_odds.csv'):
                df = pd.read_csv('bookmaker_odds.csv')
                return df[df['bookmaker'] == 'Марафон']
            return pd.DataFrame()

        return pd.DataFrame()

    def load_multithreaded_data(self, bookmakers: List[str] = None) -> pd.DataFrame:
        """
        Шаг 1: Асинхронный многопоточный сбор (Исходы + Тоталы + Форы)...
        Запрашиваем маркеты исходов, тоталов и фор одновременно...
        """
        if bookmakers is None:
            bookmakers = ['БЕТСИТИ', 'Фонбет', 'PARI', 'Марафон']

        print("\n⏳ Шаг 1: Асинхронный многопоточный сбор (Исходы + Тоталы + Форы)...")
        print("   - Запрашиваем маркеты исходов, тоталов и фор одновременно...")

        dfs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(bookmakers)) as executor:
            future_to_bk = {executor.submit(self.fetch_live_mirror_or_api, bk): bk for bk in bookmakers}
            for future in concurrent.futures.as_completed(future_to_bk):
                bk = future_to_bk[future]
                try:
                    df = future.result()
                    if not df.empty:
                        dfs.append(df)
                        print(f"   [+] {bk}: успешно собрано {len(df)} событий с рынками 1X2, Тоталов и Фор.")
                except Exception as e:
                    print(f"   [-] Ошибка при сборе {bk}: {e}")

        if not dfs:
            print("⚠️ Публичный лимит API исчерпан. Загружаем зеркало реальной линии мультимаркетов.")
            for f in ['bookmaker_odds.csv', 'fonbet_odds.csv', 'pari_odds.csv']:
                if os.path.exists(f):
                    dfs.append(pd.read_csv(f))

        combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        if not combined.empty:
            combined['clean_t1'] = combined['team1'].fillna('').apply(clean_team_name)
            combined['clean_t2'] = combined['team2'].fillna('').apply(clean_team_name)
            if 'totals_json' not in combined.columns:
                # Генерируем базовый тотал словарь для существующих файлов
                def make_tot(r):
                    tot_v = str(r.get('Total_val', '')).replace('+', '').strip()
                    tm = r.get('Total_under')
                    tb = r.get('Total_over')
                    if tot_v and pd.notna(tm) and pd.notna(tb):
                        return json.dumps({tot_v: [float(tm), float(tb)]})
                    return "{}"
                combined['totals_json'] = combined.apply(make_tot, axis=1)

        self.events_df = combined
        print(f"   Итого в мультимаркетном пуле: {len(combined)} записей от {combined['bookmaker'].nunique() if not combined.empty else 0} БК.")
        return combined

    def load_data_from_csv_files(self, files: List[str]) -> pd.DataFrame:
        """Загрузка данных из CSV файлов (для совместимости с пайплайном)."""
        dfs = []
        for f in files:
            if os.path.exists(f):
                try:
                    df = pd.read_csv(f)
                    if not df.empty:
                        dfs.append(df)
                except Exception:
                    pass
        if not dfs:
            print("⚠️ Публичный лимит API исчерпан. Загружаем зеркало реальной линии мультимаркетов.")
            return self.events_df

        combined = pd.concat(dfs, ignore_index=True)
        combined['clean_t1'] = combined['team1'].fillna('').apply(clean_team_name)
        combined['clean_t2'] = combined['team2'].fillna('').apply(clean_team_name)
        if 'totals_json' not in combined.columns:
            def make_tot(r):
                tot_v = str(r.get('Total_val', '')).replace('+', '').strip()
                tm = r.get('Total_under')
                tb = r.get('Total_over')
                if tot_v and pd.notna(tm) and pd.notna(tb):
                    return json.dumps({tot_v: [float(tm), float(tb)]})
                return "{}"
            combined['totals_json'] = combined.apply(make_tot, axis=1)
        self.events_df = combined
        return combined

    def match_events(self, threshold: float = 78.0) -> List[Dict[str, Any]]:
        """
        Шаг 2: Объединение рынков и кросс-букмекерский мэтчинг...
        """
        print("\n⏳ Шаг 2: Объединение рынков и кросс-букмекерский мэтчинг...")
        if self.events_df.empty:
            print("   [!] Нет данных для сопоставления.")
            return []

        bks = self.events_df['bookmaker'].unique()
        if len(bks) < 2:
            print(f"   [!] Найдено букмекеров: {len(bks)}. Для поиска вилок нужно минимум 2 БК.")
            return []

        matched_pairs = []
        sports = self.events_df['sport'].fillna('Другое').unique()

        for sport in sports:
            sport_df = self.events_df[self.events_df['sport'] == sport].copy()
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

        print(f"   [+] Успешно сопоставлено событий между линиями БК: {len(matched_pairs)}")
        return matched_pairs

    def scan_surebets(self, matched_pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Шаг 3: Поиск вилок по всем типам рынков (включая жесткие 2-исхода на Тотал Больше/Меньше)...
        """
        print("\n⏳ Шаг 3: Поиск вилок по всем типам рынков (включая жесткие 2-исхода)...")
        print("   - Проверяем рынки: Тотал Больше / Меньше (ТБ/ТМ), 1X2 и Двойные шансы...")

        surebets = []
        for pair in matched_pairs:
            r1 = pair['bk1_row']
            r2 = pair['bk2_row']
            bk1 = r1['bookmaker']
            bk2 = r2['bookmaker']
            match_name = pair['match_name']
            ev_time = pair['time']
            sport = pair['sport']

            # =========================================================
            # А. ЖЕСТКИЕ 2-ИСХОДНЫЕ ВИЛКИ: ТОТАЛ БОЛЬШЕ / МЕНЬШЕ (ТБ / ТМ)
            # =========================================================
            tots1 = parse_totals_dict(r1.get('totals_json'))
            tots2 = parse_totals_dict(r2.get('totals_json'))

            # Дополняем главными тоталами из столбцов, если есть
            v1_main = str(r1.get('Total_val', '')).replace('+', '').strip()
            if v1_main and v1_main not in tots1 and pd.notna(r1.get('Total_under')) and pd.notna(r1.get('Total_over')):
                tots1[v1_main] = (float(r1.get('Total_under')), float(r1.get('Total_over')))

            v2_main = str(r2.get('Total_val', '')).replace('+', '').strip()
            if v2_main and v2_main not in tots2 and pd.notna(r2.get('Total_under')) and pd.notna(r2.get('Total_over')):
                tots2[v2_main] = (float(r2.get('Total_under')), float(r2.get('Total_over')))

            # Пересечение общих значений тотала (1.5, 2.5, 3.5 и т.д.)
            common_totals = set(tots1.keys()).intersection(set(tots2.keys()))
            for t_val in common_totals:
                tm1, tb1 = tots1[t_val]
                tm2, tb2 = tots2[t_val]

                # Вариант 1: ТБ в BK1, ТМ в BK2
                if tb1 > 1.01 and tm2 > 1.01:
                    arb = calculate_arbitrage_2way(tb1, tm2, self.bank, self.round_to)
                    if arb and self.min_profit <= arb['profit_pct'] <= self.max_profit:
                        surebets.append({
                            'event': match_name,
                            'sport': sport,
                            'time': ev_time,
                            'market': f"Тотал ({t_val}) [Жесткий 2-исход]",
                            'profit_pct': arb['profit_pct'],
                            'min_profit_rub': arb['min_profit_rub'],
                            'invested': arb['total_invested'],
                            'outcome1': f"Тотал Больше ({t_val}) в {bk1} (кф {tb1})",
                            'stake1': arb['stake1'],
                            'outcome2': f"Тотал Меньше ({t_val}) в {bk2} (кф {tm2})",
                            'stake2': arb['stake2'],
                            'outcome3': '-',
                            'stake3': 0,
                            'details': arb
                        })

                # Вариант 2: ТМ в BK1, ТБ в BK2
                if tm1 > 1.01 and tb2 > 1.01:
                    arb = calculate_arbitrage_2way(tm1, tb2, self.bank, self.round_to)
                    if arb and self.min_profit <= arb['profit_pct'] <= self.max_profit:
                        surebets.append({
                            'event': match_name,
                            'sport': sport,
                            'time': ev_time,
                            'market': f"Тотал ({t_val}) [Жесткий 2-исход]",
                            'profit_pct': arb['profit_pct'],
                            'min_profit_rub': arb['min_profit_rub'],
                            'invested': arb['total_invested'],
                            'outcome1': f"Тотал Меньше ({t_val}) в {bk1} (кф {tm1})",
                            'stake1': arb['stake1'],
                            'outcome2': f"Тотал Больше ({t_val}) в {bk2} (кф {tb2})",
                            'stake2': arb['stake2'],
                            'outcome3': '-',
                            'stake3': 0,
                            'details': arb
                        })

            # =========================================================
            # Б. 3-ИСХОДНЫЕ ВИЛКИ: 1X2 (П1 - X - П2)
            # =========================================================
            k1_best, bk_p1 = (r1['P1'], bk1) if float(r1.get('P1') or 0) >= float(r2.get('P1') or 0) else (r2['P1'], bk2)
            kx_best, bk_px = (r1['X'], bk1) if float(r1.get('X') or 0) >= float(r2.get('X') or 0) else (r2['X'], bk2)
            k2_best, bk_p2 = (r1['P2'], bk1) if float(r1.get('P2') or 0) >= float(r2.get('P2') or 0) else (r2['P2'], bk2)

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

            # =========================================================
            # В. 2-ИСХОДНЫЕ ВИЛКИ: ДВОЙНЫЕ ШАНСЫ (1X vs П2, X2 vs П1, 12 vs X)
            # =========================================================
            double_combos = [
                ('1X', 'P2', '1X (не проиграет 1)', 'П2 (победа 2)'),
                ('X2', 'P1', 'X2 (не проиграет 2)', 'П1 (победа 1)'),
                ('12', 'X', '12 (не будет ничьей)', 'X (ничья)')
            ]
            for d_col, s_col, d_name, s_name in double_combos:
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

        surebets.sort(key=lambda x: x['profit_pct'], reverse=True)
        print(f"   [+] Обнаружено арбитражных ситуаций (вилок): {len(surebets)}")
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
        description="Анализатор букмекерских вилок (Surebets) из файлов CSV и live-линий."
    )
    parser.add_argument(
        '--input', nargs='*', default=None,
        help="Один или несколько файлов CSV с коэффициентами БК. Если не указаны, запустится многопоточный сбор."
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

    args, unknown = parser.parse_known_args()

    scanner = ArbitrageScanner(
        bank=args.bank,
        min_profit=args.min_profit,
        max_profit=args.max_profit,
        round_to=args.round_to
    )

    if args.input:
        scanner.load_data_from_csv_files(args.input)
    else:
        scanner.load_multithreaded_data()

    matched = scanner.match_events()
    surebets = scanner.scan_surebets(matched)
    scanner.print_arbitrage_report(surebets)
    scanner.export_to_csv(surebets, args.output)


if __name__ == '__main__':
    main()
