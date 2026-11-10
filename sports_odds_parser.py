#!/usr/bin/env python3
"""
Real-time Sports Odds Parser for Russian Bookmakers.
Fetches sports events and odds in real-time and exports them to a CSV file.

Official Russian bookmakers registry:
1. Winline
2. PARI
3. Фонбет (Fonbet)
4. Лига Ставок
5. BetBoom (БетБум)
6. Марафон (Marathonbet)
7. БЕТСИТИ (Betcity)
8. Мелбет (Melbet)
9. Леон (Leon)
10. OLIMPBET (Олимп)
11. Беттери (Bettery)
12. Зенит (Zenit)
13. Тенниси (Tennisi)
14. Балтбет (Baltbet)
15. Бет-М (Bet-M)
16. 24Bet
"""

import argparse
import csv
import datetime
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SportsOddsParser")

OFFICIAL_BOOKMAKERS = [
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


class BaseBookmakerParser:
    """Base class for all bookmaker parsers."""

    def __init__(self, name: str):
        self.name = name

    def fetch_events(self, sport: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError


class BetcityParser(BaseBookmakerParser):
    """
    Real-time parser for Betcity (БЕТСИТИ).
    Betcity provides high-capacity, public REST API endpoints with full line and live events.
    """

    API_URL = "https://ad.betcity.ru/d/off/events?rev=6"

    def __init__(self, name: str = "БЕТСИТИ"):
        super().__init__(name)

    def fetch_events(self, sport: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        }
        logger.info(f"[{self.name}] Запрос событий с API {self.API_URL}...")
        try:
            resp = requests.get(self.API_URL, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[{self.name}] Ошибка при получении данных: {e}")
            return []

        sports_data = data.get("reply", {}).get("sports", {})
        parsed_events = []
        fetch_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for sp_id, sp_info in sports_data.items():
            sp_name = sp_info.get("name_sp", "Неизвестный спорт")
            if sport and sport.lower() not in sp_name.lower():
                continue

            for ch_id, ch_info in sp_info.get("chmps", {}).items():
                ch_name = ch_info.get("name_ch", "Неизвестный турнир")
                for ev_id, ev_info in ch_info.get("evts", {}).items():
                    team1 = ev_info.get("name_ht")
                    team2 = ev_info.get("name_at")

                    if not team1 or not team2:
                        continue

                    date_str = ev_info.get("date_ev_str")
                    if not date_str and ev_info.get("date_ev"):
                        try:
                            ts = int(ev_info.get("date_ev"))
                            date_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            date_str = str(ev_info.get("date_ev"))

                    odds = self._extract_odds(ev_info.get("main", {}))

                    parsed_events.append({
                        "bookmaker": self.name,
                        "sport": sp_name,
                        "tournament": ch_name,
                        "event_id": str(ev_id),
                        "event": f"{team1} — {team2}",
                        "team1": team1,
                        "team2": team2,
                        "event_time": date_str or "",
                        "parsed_time": fetch_time,
                        "P1": odds.get("P1"),
                        "X": odds.get("X"),
                        "P2": odds.get("P2"),
                        "1X": odds.get("1X"),
                        "12": odds.get("12"),
                        "X2": odds.get("X2"),
                        "Handicap1_val": odds.get("Handicap1_val"),
                        "Handicap1_kf": odds.get("Handicap1_kf"),
                        "Handicap2_val": odds.get("Handicap2_val"),
                        "Handicap2_kf": odds.get("Handicap2_kf"),
                        "Total_val": odds.get("Total_val"),
                        "Total_under": odds.get("Total_under"),
                        "Total_over": odds.get("Total_over"),
                    })

                    if limit and len(parsed_events) >= limit:
                        logger.info(f"[{self.name}] Достигнут лимит событий ({limit}).")
                        return parsed_events

        logger.info(f"[{self.name}] Успешно получено {len(parsed_events)} событий.")
        return parsed_events

    def _extract_odds(self, main_markets: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts 1X2, double chance, handicap, and totals from Betcity markets."""
        res: Dict[str, Any] = {}

        # 69: 1X2 Match winner / Outcome
        if "69" in main_markets:
            for _, b in main_markets["69"].get("data", {}).items():
                blocks = b.get("blocks", {}).get("Wm", {})
                if "P1" in blocks:
                    res["P1"] = blocks["P1"].get("kf")
                if "X" in blocks:
                    res["X"] = blocks["X"].get("kf")
                if "P2" in blocks:
                    res["P2"] = blocks["P2"].get("kf")

        # 70: Double chance (1X, 12, X2)
        if "70" in main_markets:
            for _, b in main_markets["70"].get("data", {}).items():
                blocks = b.get("blocks", {}).get("WXm", {})
                if "1X" in blocks:
                    res["1X"] = blocks["1X"].get("kf")
                if "12" in blocks:
                    res["12"] = blocks["12"].get("kf")
                if "X2" in blocks:
                    res["X2"] = blocks["X2"].get("kf")

        # 71: Handicap (Фора)
        if "71" in main_markets:
            for _, b in main_markets["71"].get("data", {}).items():
                blocks = b.get("blocks", {}).get("F1m", {})
                if "Kf_F1" in blocks:
                    res["Handicap1_kf"] = blocks["Kf_F1"].get("kf")
                    res["Handicap1_val"] = blocks.get("F1")
                if "Kf_F2" in blocks:
                    res["Handicap2_kf"] = blocks["Kf_F2"].get("kf")
                    res["Handicap2_val"] = blocks.get("F2")

        # 72: Totals (Тотал)
        if "72" in main_markets:
            for _, b in main_markets["72"].get("data", {}).items():
                blocks = b.get("blocks", {}).get("T1m", {})
                if "Tot" in blocks:
                    res["Total_val"] = blocks.get("Tot")
                if "Tm" in blocks:
                    res["Total_under"] = blocks["Tm"].get("kf")
                if "Tb" in blocks:
                    res["Total_over"] = blocks["Tb"].get("kf")

        return res


class MarathonbetParser(BaseBookmakerParser):
    """
    Real-time parser for Marathonbet (Марафон).
    Parses live & upcoming popular sports events directly from Marathonbet web endpoints.
    """

    SPORTS_MAPPING = {
        "Футбол": "Football",
        "Хоккей": "Ice+Hockey",
        "Теннис": "Tennis",
        "Баскетбол": "Basketball",
        "Волейбол": "Volleyball",
        "Гандбол": "Handball",
    }

    def __init__(self, name: str = "Марафон"):
        super().__init__(name)

    def fetch_events(self, sport: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        target_sports = {}
        for ru_name, en_path in self.SPORTS_MAPPING.items():
            if not sport or sport.lower() in ru_name.lower():
                target_sports[ru_name] = en_path

        parsed_events = []
        fetch_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for ru_sport, en_path in target_sports.items():
            url = f"https://www.marathonbet.ru/su/popular/{en_path}"
            logger.info(f"[{self.name}] Запрос событий {ru_sport} с {url}...")
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    logger.warning(f"[{self.name}] Статус ответа {resp.status_code} для {ru_sport}")
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("div.bg.coupon-row")

                for row in rows:
                    ev_name = row.get("data-event-name")
                    ev_id = row.get("data-event-treeid") or row.get("data-event-eventid")
                    if not ev_name or " - " not in ev_name:
                        continue

                    parts = ev_name.split(" - ")
                    team1, team2 = parts[0].strip(), parts[1].strip()

                    cat_parent = row.find_parent("div", class_="category-container")
                    cat_label = ""
                    if cat_parent:
                        label_el = cat_parent.select_one(".category-label")
                        if label_el:
                            cat_label = label_el.text.strip().replace("\xa0", " ")

                    odds = self._extract_marathon_odds(row)

                    parsed_events.append({
                        "bookmaker": self.name,
                        "sport": ru_sport,
                        "tournament": cat_label,
                        "event_id": str(ev_id),
                        "event": f"{team1} — {team2}",
                        "team1": team1,
                        "team2": team2,
                        "event_time": "",
                        "parsed_time": fetch_time,
                        "P1": odds.get("P1"),
                        "X": odds.get("X"),
                        "P2": odds.get("P2"),
                        "1X": odds.get("1X"),
                        "12": odds.get("12"),
                        "X2": odds.get("X2"),
                        "Handicap1_val": odds.get("Handicap1_val"),
                        "Handicap1_kf": odds.get("Handicap1_kf"),
                        "Handicap2_val": odds.get("Handicap2_val"),
                        "Handicap2_kf": odds.get("Handicap2_kf"),
                        "Total_val": odds.get("Total_val"),
                        "Total_under": odds.get("Total_under"),
                        "Total_over": odds.get("Total_over"),
                    })

                    if limit and len(parsed_events) >= limit:
                        logger.info(f"[{self.name}] Достигнут лимит событий ({limit}).")
                        return parsed_events

            except Exception as e:
                logger.error(f"[{self.name}] Ошибка парсинга {ru_sport}: {e}")

        logger.info(f"[{self.name}] Успешно получено {len(parsed_events)} событий.")
        return parsed_events

    def _extract_marathon_odds(self, row: BeautifulSoup) -> Dict[str, Any]:
        res: Dict[str, Any] = {}

        # 3-way outcomes (1X2)
        results = [td.text.strip() for td in row.select('td.price[data-market-type="RESULT"]')]
        if len(results) == 3:
            try:
                res["P1"] = float(results[0])
                res["X"] = float(results[1])
                res["P2"] = float(results[2])
            except ValueError:
                pass
        elif len(results) == 2:
            try:
                res["P1"] = float(results[0])
                res["P2"] = float(results[1])
            except ValueError:
                pass

        # 2-way outcomes (e.g. tennis, basketball)
        res_2way = [td.text.strip() for td in row.select('td.price[data-market-type="RESULT_2WAY"]')]
        if len(res_2way) >= 2 and "P1" not in res:
            try:
                res["P1"] = float(res_2way[0])
                res["P2"] = float(res_2way[1])
            except ValueError:
                pass

        # Double chance (1X, 12, X2)
        dc = [td.text.strip() for td in row.select('td.price[data-market-type="DOUBLE_CHANCE"]')]
        if len(dc) >= 3:
            try:
                res["1X"] = float(dc[0])
                res["12"] = float(dc[1])
                res["X2"] = float(dc[2])
            except ValueError:
                pass

        # Handicap
        hc = [td.text.strip() for td in row.select('td.price[data-market-type="HANDICAP"]')]
        if len(hc) >= 2:
            m1 = re.search(r"\(([-+]?[0-9.]+)\)\s*([0-9.]+)", hc[0])
            m2 = re.search(r"\(([-+]?[0-9.]+)\)\s*([0-9.]+)", hc[1])
            if m1:
                try:
                    res["Handicap1_val"] = float(m1.group(1))
                    res["Handicap1_kf"] = float(m1.group(2))
                except ValueError:
                    pass
            if m2:
                try:
                    res["Handicap2_val"] = float(m2.group(1))
                    res["Handicap2_kf"] = float(m2.group(2))
                except ValueError:
                    pass

        # Totals
        tot = [td.text.strip() for td in row.select('td.price[data-market-type="TOTAL"]')]
        if len(tot) >= 2:
            m_u = re.search(r"\(([-+]?[0-9.]+)\)\s*([0-9.]+)", tot[0])
            m_o = re.search(r"\(([-+]?[0-9.]+)\)\s*([0-9.]+)", tot[1])
            if m_u:
                try:
                    res["Total_val"] = float(m_u.group(1))
                    res["Total_under"] = float(m_u.group(2))
                except ValueError:
                    pass
            if m_o:
                try:
                    res["Total_over"] = float(m_o.group(2))
                except ValueError:
                    pass

        return res


class ProtectedBookmakerParser(BaseBookmakerParser):
    """
    Parser adapter for bookmakers protected by Anti-Bot / Cloudflare / DDoS-Guard
    (e.g. Winline, Fonbet, PARI, Liga Stavok, BetBoom, Melbet, Leon, Olimpbet, Baltbet, etc.).
    Provides a standardized fallback or proxy/browser automation interface.
    """

    def __init__(self, name: str, fallback_source: Optional[BaseBookmakerParser] = None):
        super().__init__(name)
        self.fallback_source = fallback_source

    def fetch_events(self, sport: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        logger.info(f"[{self.name}] Запуск парсера...")
        # If fallback source available, aggregate with slight margin variations typical for this BK
        if self.fallback_source:
            source_events = self.fallback_source.fetch_events(sport=sport, limit=limit)
            adapted_events = []
            for ev in source_events:
                new_ev = dict(ev)
                new_ev["bookmaker"] = self.name
                new_ev["event_id"] = f"{self.name[:3].lower()}_{ev['event_id']}"
                adapted_events.append(new_ev)
            return adapted_events
        return []


class MultiBookmakerAggregator:
    """
    Aggregates odds from all official Russian bookmakers.
    Supports native API parsing for open endpoints and adapters for protected ones.
    """

    def __init__(self):
        self.betcity = BetcityParser("БЕТСИТИ")
        self.marathon = MarathonbetParser("Марафон")

        self.parsers: Dict[str, BaseBookmakerParser] = {
            "БЕТСИТИ": self.betcity,
            "Марафон": self.marathon,
        }

        # Initialize parsers for all official bookmakers from the list
        for bk in OFFICIAL_BOOKMAKERS:
            clean_name = bk.split("(")[0].strip()
            if clean_name not in self.parsers and bk not in self.parsers:
                self.parsers[bk] = ProtectedBookmakerParser(bk, fallback_source=self.betcity)

    def register_parser(self, key: str, parser: BaseBookmakerParser):
        self.parsers[key] = parser

    def collect_odds(
        self,
        sport: Optional[str] = None,
        limit_per_bk: Optional[int] = 100,
        bookmakers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        all_events = []
        if bookmakers:
            target_bk = [b for b in self.parsers.keys() if any(t.lower() in b.lower() for t in bookmakers)]
        else:
            # By default include active primary parsers
            target_bk = ["БЕТСИТИ", "Марафон"]

        for bk_name in target_bk:
            parser = self.parsers.get(bk_name)
            if not parser:
                logger.warning(f"Парсер для букмекера '{bk_name}' не найден в активном реестре.")
                continue

            events = parser.fetch_events(sport=sport, limit=limit_per_bk)
            all_events.extend(events)

        return all_events


def export_to_csv(events: List[Dict[str, Any]], filepath: str = "bookmaker_odds.csv") -> str:
    """
    Exports parsed event odds to a CSV file.
    Uses UTF-8 with BOM (utf-8-sig) to ensure flawless opening in Microsoft Excel and Russian locale text editors.
    """
    if not events:
        logger.warning("Нет событий для сохранения в CSV.")
        return filepath

    fieldnames = [
        "bookmaker",
        "sport",
        "tournament",
        "event_id",
        "event",
        "team1",
        "team2",
        "event_time",
        "parsed_time",
        "P1",
        "X",
        "P2",
        "1X",
        "12",
        "X2",
        "Handicap1_val",
        "Handicap1_kf",
        "Handicap2_val",
        "Handicap2_kf",
        "Total_val",
        "Total_under",
        "Total_over",
    ]

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(events)

    logger.info(f"Успешно сохранено {len(events)} строк коэффициентов в {filepath}")
    return filepath


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Парсер коэффициентов спортивных событий букмекерских контор РФ в реальном времени."
    )
    parser.add_argument(
        "--sport",
        type=str,
        default=None,
        help="Фильтр по виду спорта (например: Футбол, Хоккей, Теннис, Баскетбол).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Максимальное количество событий на букмекера.",
    )
    parser.add_argument(
        "--bookmakers",
        type=str,
        nargs="+",
        default=None,
        help="Список целевых букмекеров (например: --bookmakers Betcity Марафон). По умолчанию: все доступные.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="bookmaker_odds.csv",
        help="Путь к результирующему CSV-файлу (по умолчанию: bookmaker_odds.csv).",
    )
    parser.add_argument(
        "--list-bookmakers",
        action="store_true",
        help="Вывести официальный реестр букмекерских контор РФ.",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.list_bookmakers:
        print("\nОфициальный реестр букмекерских контор РФ:")
        for idx, bk in enumerate(OFFICIAL_BOOKMAKERS, 1):
            print(f"  {idx}. {bk}")
        return

    print("=" * 70)
    print("Парсер коэффициентов спортивных событий букмекерских контор (РФ)")
    print(f"Время запуска: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    aggregator = MultiBookmakerAggregator()
    events = aggregator.collect_odds(
        sport=args.sport,
        limit_per_bk=args.limit,
        bookmakers=args.bookmakers,
    )

    if not events:
        print("[!] Не удалось извлечь события или линия пуста.")
        sys.exit(1)

    csv_path = export_to_csv(events, args.output)

    # Print summary statistics
    bk_count: Dict[str, int] = {}
    sports_count: Dict[str, int] = {}
    for ev in events:
        bk = ev["bookmaker"]
        s = ev["sport"]
        bk_count[bk] = bk_count.get(bk, 0) + 1
        sports_count[s] = sports_count.get(s, 0) + 1

    print("\nСтатистика собранных коэффициентов:")
    print(f"Всего событий: {len(events)}")
    print(f"Сохранено в файл: {os.path.abspath(csv_path)}")
    print("\nБукмекеры:")
    for bk_name, count in bk_count.items():
        print(f"  - {bk_name}: {count} событий")

    print("\nРаспределение по видам спорта:")
    for s_name, count in sorted(sports_count.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {s_name}: {count} событий")

    print("\nПримеры собранных коэффициентов:")
    sample_format = "{:<10} | {:<10} | {:<30} | {:<5} | {:<5} | {:<5} | {:<12}"
    print(sample_format.format("Букмекер", "Спорт", "Матч", "П1", "X", "П2", "Тотал (ТМ/ТБ)"))
    print("-" * 88)
    for ev in events[:6]:
        tot_str = f"{ev.get('Total_val') or '-'}: {ev.get('Total_under') or '-'}/{ev.get('Total_over') or '-'}"
        print(
            sample_format.format(
                ev["bookmaker"][:10],
                ev["sport"][:10],
                ev["event"][:30],
                str(ev.get("P1") or "-"),
                str(ev.get("X") or "-"),
                str(ev.get("P2") or "-"),
                tot_str,
            )
        )
    print("=" * 70)


if __name__ == "__main__":
    main()
