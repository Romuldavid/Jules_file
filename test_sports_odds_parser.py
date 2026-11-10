#!/usr/bin/env python3
"""
Unit and integration tests for sports_odds_parser.py
"""

import csv
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from sports_odds_parser import (
    OFFICIAL_BOOKMAKERS,
    BaseBookmakerParser,
    BetcityParser,
    MarathonbetParser,
    MultiBookmakerAggregator,
    ProtectedBookmakerParser,
    export_to_csv,
)


class TestSportsOddsParser(unittest.TestCase):

    def test_official_bookmakers_list(self):
        """Verifies that all required official bookmakers are present in the list."""
        required = [
            "Winline",
            "PARI",
            "Фонбет (Fonbet)",
            "Лига Ставок",
            "BetBoom (БетБум)",
            "Марафон (Marathonbet)",
            "БЕТСИТИ (Betcity)",
            "Мелбет (Melbet)",
            "Леон (Leon)",
            "OLIMPBET (Олимп)",
            "Беттери (Bettery)",
            "Зенит (Zenit)",
            "Тенниси (Tennisi)",
            "Балтбет (Baltbet)",
            "Бет-М (Bet-M)",
            "24Bet",
        ]
        for name in required:
            self.assertIn(name, OFFICIAL_BOOKMAKERS)

    def test_betcity_odds_extraction(self):
        """Tests market extraction logic for 1X2, double chance, handicap, and totals."""
        parser = BetcityParser()
        raw_markets = {
            "69": {
                "name": "Фактический исход",
                "data": {
                    "1": {"blocks": {"Wm": {"P1": {"kf": 2.15}, "X": {"kf": 3.40}, "P2": {"kf": 3.10}}}}
                },
            },
            "70": {
                "name": "Двойной исход",
                "data": {
                    "1": {"blocks": {"WXm": {"1X": {"kf": 1.35}, "12": {"kf": 1.30}, "X2": {"kf": 1.65}}}}
                },
            },
            "71": {
                "name": "Фора",
                "data": {
                    "1": {
                        "blocks": {
                            "F1m": {
                                "Kf_F1": {"kf": 1.90},
                                "F1": -0.5,
                                "Kf_F2": {"kf": 1.90},
                                "F2": 0.5,
                            }
                        }
                    }
                },
            },
            "72": {
                "name": "Тотал",
                "data": {
                    "1": {
                        "blocks": {
                            "T1m": {
                                "Tot": 2.5,
                                "Tm": {"kf": 1.85},
                                "Tb": {"kf": 1.95},
                            }
                        }
                    }
                },
            },
        }

        odds = parser._extract_odds(raw_markets)
        self.assertEqual(odds.get("P1"), 2.15)
        self.assertEqual(odds.get("X"), 3.40)
        self.assertEqual(odds.get("P2"), 3.10)
        self.assertEqual(odds.get("1X"), 1.35)
        self.assertEqual(odds.get("12"), 1.30)
        self.assertEqual(odds.get("X2"), 1.65)
        self.assertEqual(odds.get("Handicap1_val"), -0.5)
        self.assertEqual(odds.get("Handicap1_kf"), 1.90)
        self.assertEqual(odds.get("Handicap2_val"), 0.5)
        self.assertEqual(odds.get("Handicap2_kf"), 1.90)
        self.assertEqual(odds.get("Total_val"), 2.5)
        self.assertEqual(odds.get("Total_under"), 1.85)
        self.assertEqual(odds.get("Total_over"), 1.95)

    def test_marathon_odds_extraction(self):
        """Tests odds parsing from Marathon coupon row HTML."""
        parser = MarathonbetParser()
        html = """
        <div class="bg coupon-row" data-event-name="Ливерпуль - Арсенал" data-event-treeid="12345">
          <table>
            <td class="price" data-market-type="RESULT">2.10</td>
            <td class="price" data-market-type="RESULT">3.50</td>
            <td class="price" data-market-type="RESULT">3.20</td>
            <td class="price" data-market-type="DOUBLE_CHANCE">1.35</td>
            <td class="price" data-market-type="DOUBLE_CHANCE">1.28</td>
            <td class="price" data-market-type="DOUBLE_CHANCE">1.70</td>
            <td class="price" data-market-type="HANDICAP">(-0.5) 2.05</td>
            <td class="price" data-market-type="HANDICAP">(+0.5) 1.80</td>
            <td class="price" data-market-type="TOTAL">(2.5) 1.90</td>
            <td class="price" data-market-type="TOTAL">(2.5) 1.90</td>
          </table>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser").select_one("div.coupon-row")
        odds = parser._extract_marathon_odds(soup)
        self.assertEqual(odds.get("P1"), 2.10)
        self.assertEqual(odds.get("X"), 3.50)
        self.assertEqual(odds.get("P2"), 3.20)
        self.assertEqual(odds.get("1X"), 1.35)
        self.assertEqual(odds.get("12"), 1.28)
        self.assertEqual(odds.get("X2"), 1.70)
        self.assertEqual(odds.get("Handicap1_val"), -0.5)
        self.assertEqual(odds.get("Handicap1_kf"), 2.05)
        self.assertEqual(odds.get("Total_val"), 2.5)
        self.assertEqual(odds.get("Total_under"), 1.90)
        self.assertEqual(odds.get("Total_over"), 1.90)

    @patch("requests.get")
    def test_betcity_parser_fetch_events_mock(self, mock_get):
        """Tests fetch_events parsing with mocked API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "reply": {
                "sports": {
                    "1": {
                        "name_sp": "Футбол",
                        "chmps": {
                            "10": {
                                "name_ch": "РПЛ",
                                "evts": {
                                    "1001": {
                                        "name_ht": "Спартак",
                                        "name_at": "Зенит",
                                        "date_ev_str": "2026-11-20 19:00",
                                        "main": {
                                            "69": {
                                                "data": {
                                                    "1": {
                                                        "blocks": {
                                                            "Wm": {
                                                                "P1": {"kf": 2.80},
                                                                "X": {"kf": 3.50},
                                                                "P2": {"kf": 2.45},
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        },
                                    }
                                },
                            }
                        },
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        parser = BetcityParser()
        events = parser.fetch_events(sport="Футбол")
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["sport"], "Футбол")
        self.assertEqual(ev["tournament"], "РПЛ")
        self.assertEqual(ev["event"], "Спартак — Зенит")
        self.assertEqual(ev["team1"], "Спартак")
        self.assertEqual(ev["team2"], "Зенит")
        self.assertEqual(ev["P1"], 2.80)
        self.assertEqual(ev["X"], 3.50)
        self.assertEqual(ev["P2"], 2.45)

    def test_multi_bookmaker_aggregator(self):
        """Tests multi bookmaker aggregator registry."""
        agg = MultiBookmakerAggregator()
        self.assertIn("БЕТСИТИ", agg.parsers)
        self.assertIn("Марафон", agg.parsers)
        # All official bookmakers should be registered
        for bk in OFFICIAL_BOOKMAKERS:
            matched = any(bk in key or key in bk for key in agg.parsers)
            self.assertTrue(matched, f"Bookmaker {bk} not found in aggregator")

    def test_export_to_csv(self):
        """Tests CSV export and verifies header and row integrity with UTF-8 BOM."""
        sample_events = [
            {
                "bookmaker": "БЕТСИТИ",
                "sport": "Хоккей",
                "tournament": "КХЛ",
                "event_id": "999",
                "event": "ЦСКА — СКА",
                "team1": "ЦСКА",
                "team2": "СКА",
                "event_time": "2026-11-20 19:30",
                "parsed_time": "2026-11-10 14:00:00",
                "P1": 2.20,
                "X": 3.90,
                "P2": 2.75,
                "1X": 1.40,
                "12": 1.25,
                "X2": 1.60,
                "Handicap1_val": 0,
                "Handicap1_kf": 1.70,
                "Handicap2_val": 0,
                "Handicap2_kf": 2.10,
                "Total_val": 4.5,
                "Total_under": 2.05,
                "Total_over": 1.75,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test_odds.csv")
            export_to_csv(sample_events, csv_path)

            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 1)
                row = rows[0]
                self.assertEqual(row["bookmaker"], "БЕТСИТИ")
                self.assertEqual(row["sport"], "Хоккей")
                self.assertEqual(row["event"], "ЦСКА — СКА")
                self.assertEqual(float(row["P1"]), 2.20)
                self.assertEqual(float(row["Total_val"]), 4.5)


if __name__ == "__main__":
    unittest.main()
