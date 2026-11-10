#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для модуля arbitrage_scanner.py
"""

import unittest
import os
import pandas as pd
from arbitrage_scanner import (
    clean_team_name,
    calculate_arbitrage_2way,
    calculate_arbitrage_3way,
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
        # Обычные кэфы: 2.10, 3.20, 3.40 -> 0.476 + 0.3125 + 0.294 = 1.08 > 1.0
        res = calculate_arbitrage_3way(2.10, 3.20, 3.40, bank=10000.0)
        self.assertIsNone(res)

    def test_scanner_end_to_end_mock(self):
        # Создаем тестовые данные для двух БК
        df1 = pd.DataFrame([{
            'bookmaker': 'БК_Тест_А',
            'sport': 'Футбол',
            'tournament': 'Лига Чемпионов',
            'event_id': 101,
            'event': 'Реал Мадрид — Барселона',
            'team1': 'Реал Мадрид',
            'team2': 'Барселона',
            'event_time': '2026-11-20 22:00',
            'P1': 2.20,
            'X': 3.50,
            'P2': 3.20,
            '1X': 1.35,
            '12': 1.30,
            'X2': 1.70,
            'Total_val': 2.5,
            'Total_under': 2.10,
            'Total_over': 1.75
        }])

        df2 = pd.DataFrame([{
            'bookmaker': 'БК_Тест_Б',
            'sport': 'Футбол',
            'tournament': 'UEFA Champions League',
            'event_id': 202,
            'event': 'ФК Real Madrid — FC Barcelona',
            'team1': 'Real Madrid',
            'team2': 'FC Barcelona',
            'event_time': '2026-11-20 22:00',
            'P1': 1.90,
            'X': 3.50,
            'P2': 4.20,
            '1X': 1.25,
            '12': 1.30,
            'X2': 1.95,
            'Total_val': 2.5,
            'Total_under': 1.75,
            'Total_over': 2.15
        }])

        df1.to_csv('temp_bk1.csv', index=False)
        df2.to_csv('temp_bk2.csv', index=False)

        scanner = ArbitrageScanner(bank=10000, min_profit=0.1)
        scanner.load_data(['temp_bk1.csv', 'temp_bk2.csv'])
        matched = scanner.match_events(threshold=75)
        self.assertEqual(len(matched), 1)

        surebets = scanner.scan_surebets(matched)
        self.assertGreater(len(surebets), 0)

        # Проверяем экспорт
        scanner.export_to_csv(surebets, 'temp_surebets.csv')
        self.assertTrue(os.path.exists('temp_surebets.csv'))
        exported_df = pd.read_csv('temp_surebets.csv')
        self.assertEqual(len(exported_df), len(surebets))

        # Очистка
        for tmp in ['temp_bk1.csv', 'temp_bk2.csv', 'temp_surebets.csv']:
            if os.path.exists(tmp):
                os.remove(tmp)

if __name__ == '__main__':
    unittest.main()
