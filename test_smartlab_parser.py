import unittest
import pandas as pd
from smartlab_parser import clean_number, filter_undervalued_dividend_stocks


class TestSmartlabParser(unittest.TestCase):
    def test_clean_number(self):
        self.assertEqual(clean_number("4 179"), 4179.0)
        self.assertEqual(clean_number("11.2%"), 11.2)
        self.assertEqual(clean_number("-0.3"), -0.3)
        self.assertEqual(clean_number("505%"), 505.0)
        self.assertIsNone(clean_number("-"))
        self.assertIsNone(clean_number(""))
        self.assertIsNone(clean_number(None))

    def test_filter_undervalued_stocks(self):
        sample_data = pd.DataFrame([
            {"name": "Company A", "pe": 5.0, "div_yield_ao_pct": 12.0, "net_debt_ebitda": 1.0},
            {"name": "Company B", "pe": 25.0, "div_yield_ao_pct": 2.0, "net_debt_ebitda": 4.5},
            {"name": "Company C", "pe": 8.0, "div_yield_ao_pct": 9.0, "net_debt_ebitda": 2.0},
        ])

        filtered = filter_undervalued_dividend_stocks(
            sample_data, max_pe=10.0, min_div_yield=7.0, max_debt_ebitda=2.5
        )
        self.assertEqual(len(filtered), 2)
        self.assertIn("Company A", filtered["name"].values)
        self.assertIn("Company C", filtered["name"].values)
        self.assertNotIn("Company B", filtered["name"].values)


if __name__ == "__main__":
    unittest.main()
