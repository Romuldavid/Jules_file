#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для парсера БК «Лига Ставок» (parse_ligastavok.py)
"""

import unittest
import os
import pandas as pd
from parse_ligastavok import fetch_ligastavok_odds

class TestLigaStavokParser(unittest.TestCase):

    def test_fetch_ligastavok_odds_structure(self):
        df = fetch_ligastavok_odds(max_events=10)
        self.assertFalse(df.empty, "DataFrame не должен быть пустым")
        self.assertLessEqual(len(df), 10, "Количество событий не должно превышать лимит")

        # Проверка обязательных колонок
        expected_cols = [
            'bookmaker', 'sport', 'tournament', 'event_id', 'event', 'team1', 'team2',
            'event_time', 'parsed_time', 'P1', 'X', 'P2', '1X', '12', 'X2',
            'Total_val', 'Total_under', 'Total_over', 'totals_json'
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns, f"Колонка {col} отсутствует в результирующем DataFrame")

        # Проверка названия букмекера
        self.assertTrue((df['bookmaker'] == 'Лига Ставок').all())

        # Проверка корректности коэффициентов
        first_row = df.iloc[0]
        self.assertIsNotNone(first_row['event'])
        self.assertIsNotNone(first_row['P1'])
        self.assertGreater(float(first_row['P1']), 1.0)
        self.assertGreater(float(first_row['P2']), 1.0)

    def test_csv_export(self):
        tmp_csv = "temp_test_ligastavok.csv"
        df = fetch_ligastavok_odds(max_events=5)
        df.to_csv(tmp_csv, index=False, encoding='utf-8-sig')

        self.assertTrue(os.path.exists(tmp_csv))
        loaded_df = pd.read_csv(tmp_csv)
        self.assertEqual(len(loaded_df), len(df))
        self.assertEqual(loaded_df.iloc[0]['bookmaker'], 'Лига Ставок')

        if os.path.exists(tmp_csv):
            os.remove(tmp_csv)

if __name__ == '__main__':
    unittest.main()
