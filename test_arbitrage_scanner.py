#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для обновленного модуля arbitrage_scanner.py
"""

import unittest
import os
import json
import pandas as pd
from arbitrage_scanner import (
    clean_team_name,
    calculate_arbitrage_2way,
    calculate_arbitrage_3way,
    parse_totals_dict,
    ArbitrageScanner
)

class TestArbitrageScanner(unittest.TestCase):

    def test_clean_team_name(self):
        # Удаление префиксов ФК, ХК, знаков препинания, транслитерация
        self.assertEqual(clean_team_name("ФК «Спартак» Москва"), "spartak moskva")
        self.assertEqual(clean_team_name("ХК СКА Санкт-Петербург"), "ska sankt peterburg")
        self.assertEqual(clean_team_name("FC Real Madrid (ESP)"), "real madrid esp")
        self.assertEqual(clean_team_name(""), "")
        self.assertEqual(clean_team_name(None), "")

    def test_calculate_arbitrage_2way_profitable(self):
        # k1 = 2.10, k2 = 2.15 -> 1/2.10 + 1/2.15 = 0.4762 + 0.4651 = 0.9413 < 1.0 (Вилка!)
        bank = 10000.0
        res = calculate_arbitrage_2way(2.10, 2.15, bank=bank, round_to=10)
        self.assertIsNotNone(res)
        self.assertLess(res['inv_sum'], 1.0)
        self.assertGreater(res['profit_pct'], 0)
        self.assertGreater(res['min_profit_rub'], 0)
        self.assertEqual(res['total_invested'], res['stake1'] + res['stake2'])
        # Проверяем, что при обоих исходах мы в плюсе
        self.assertGreater(res['stake1'] * 2.10, res['total_invested'])
        self.assertGreater(res['stake2'] * 2.15, res['total_invested'])

    def test_calculate_arbitrage_2way_no_arb(self):
        # Обычные коэффициенты с маржой: 1.90 и 1.90 -> 1/1.9 + 1/1.9 = 1.0526 > 1.0
        res = calculate_arbitrage_2way(1.90, 1.90, bank=10000.0)
        self.assertIsNone(res)

    def test_calculate_arbitrage_3way_profitable(self):
        # k1 = 2.80, kx = 3.60, k2 = 4.00
        # 1/2.8 + 1/3.6 + 1/4.0 = 0.3571 + 0.2778 + 0.2500 = 0.8849 < 1.0 (Вилка ~13%)
        bank = 10000.0
        res = calculate_arbitrage_3way(2.80, 3.60, 4.00, bank=bank, round_to=10)
        self.assertIsNotNone(res)
        self.assertLess(res['inv_sum'], 1.0)
        self.assertGreater(res['profit_pct'], 10.0)
        self.assertGreater(res['min_profit_rub'], 1000.0)
        self.assertEqual(res['total_invested'], res['stake1'] + res['stake2'] + res['stake3'])
        # Проверяем положительный доход по всем трем плечам
        self.assertGreater(res['stake1'] * 2.80, res['total_invested'])
        self.assertGreater(res['stake2'] * 3.60, res['total_invested'])
        self.assertGreater(res['stake3'] * 4.00, res['total_invested'])

    def test_calculate_arbitrage_3way_no_arb(self):
        res = calculate_arbitrage_3way(2.10, 3.20, 3.40, bank=10000.0)
        self.assertIsNone(res)

    def test_parse_totals_dict(self):
        json_data = json.dumps({"2.5": [1.95, 1.95], "1.5": [3.10, 1.40]})
        parsed = parse_totals_dict(json_data)
        self.assertIn("2.5", parsed)
        self.assertEqual(parsed["2.5"], (1.95, 1.95))
        self.assertEqual(parsed["1.5"], (3.10, 1.40))
        self.assertEqual(parse_totals_dict(None), {})

    def test_scanner_multitotals_and_2way_arb(self):
        # Тестируем жесткие 2-исходные вилки на Тотал Больше/Меньше
        df1 = pd.DataFrame([{
            'bookmaker': 'БК_Альфа',
            'sport': 'Футбол',
            'tournament': 'РПЛ',
            'event_id': 101,
            'event': 'Спартак — Зенит',
            'team1': 'Спартак',
            'team2': 'Зенит',
            'event_time': '2026-11-20 20:00',
            'P1': 2.50,
            'X': 3.40,
            'P2': 2.90,
            '1X': 1.40,
            '12': 1.30,
            'X2': 1.55,
            'Total_val': 2.5,
            'Total_under': 2.15,
            'Total_over': 1.75,
            'totals_json': json.dumps({
                "2.5": [2.15, 1.75],
                "3.5": [1.45, 2.80]
            })
        }])

        df2 = pd.DataFrame([{
            'bookmaker': 'БК_Бета',
            'sport': 'Футбол',
            'tournament': 'Russian Premier League',
            'event_id': 202,
            'event': 'Spartak — Zenit',
            'team1': 'Spartak',
            'team2': 'Zenit',
            'event_time': '2026-11-20 20:00',
            'P1': 2.40,
            'X': 3.30,
            'P2': 3.10,
            '1X': 1.35,
            '12': 1.30,
            'X2': 1.60,
            'Total_val': 2.5,
            'Total_under': 1.75,
            'Total_over': 2.15,
            'totals_json': json.dumps({
                "2.5": [1.75, 2.15],
                "3.5": [1.80, 2.05]
            })
        }])

        df1.to_csv('temp_test_bk1.csv', index=False)
        df2.to_csv('temp_test_bk2.csv', index=False)

        scanner = ArbitrageScanner(bank=10000, min_profit=0.1)
        scanner.load_data_from_csv_files(['temp_test_bk1.csv', 'temp_test_bk2.csv'])
        matched = scanner.match_events(threshold=75)
        self.assertEqual(len(matched), 1)

        surebets = scanner.scan_surebets(matched)
        self.assertGreater(len(surebets), 0)

        # Проверяем наличие жесткой вилки на Тотал 2.5:
        # ТМ(2.5) в БК Альфа = 2.15, ТБ(2.5) в БК Бета = 2.15 -> инверсия: 1/2.15 + 1/2.15 = 0.9302 < 1.0 (Вилка ~7.5%)
        total_arbs = [s for s in surebets if "Тотал (2.5)" in s['market']]
        self.assertTrue(len(total_arbs) > 0)

        # Очистка
        for tmp in ['temp_test_bk1.csv', 'temp_test_bk2.csv']:
            if os.path.exists(tmp):
                os.remove(tmp)

if __name__ == '__main__':
    unittest.main()
