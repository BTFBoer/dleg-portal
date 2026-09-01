import json
import unittest
from pathlib import Path

from app.rules import YearInput, calculate_case


POLICIES = json.loads(
    (Path(__file__).parents[1] / "app" / "policies" / "defaults.json").read_text(encoding="utf-8")
)


def year(book_year: int, income: float) -> YearInput:
    return YearInput(
        year=book_year,
        saldo_fiscale_winst=income,
        current_assets=100_000,
        current_liabilities=50_000,
        equity=30_000,
        total_assets=100_000,
    )


class LenderPolicyTests(unittest.TestCase):
    def test_requested_profiles_are_versioned_and_guarded(self):
        for key in (
            "ABN_AMRO_MATRIX_2024",
            "FLORIUS_MATRIX_2024",
            "MONEYOU_MATRIX_2024",
            "NIBC_MATRIX_2024",
        ):
            policy = POLICIES[key]
            self.assertEqual(policy["status"], "historical")
            self.assertTrue(policy["requires_manual_review"])
            self.assertTrue(policy["source"])
            self.assertTrue(policy["version"])

    def test_florius_and_moneyou_inherit_historical_abn_route(self):
        abn = POLICIES["ABN_AMRO_MATRIX_2024"]
        for key in ("FLORIUS_MATRIX_2024", "MONEYOU_MATRIX_2024"):
            policy = POLICIES[key]
            self.assertEqual(policy["inherits_from"], "ABN_AMRO_MATRIX_2024")
            for field in (
                "method",
                "cap_last_year",
                "liquidity_min",
                "quick_ratio_min",
                "solvability_min_pct",
                "starter_factor_pct_12_23",
                "starter_factor_pct_24_35",
            ):
                self.assertEqual(policy[field], abn[field])

    def test_nibc_profitability_guard_requires_one_prior_positive_year(self):
        result = calculate_case(
            entrepreneur_type="IB",
            years=[year(2023, -3_000), year(2024, -5_000), year(2025, 50_000)],
            policy=POLICIES["NIBC_MATRIX_2024"],
            current_month=9,
        )
        self.assertTrue(any("minimaal één eerder toetsjaar" in note for note in result.notes))
        self.assertTrue(any("BELEIDSVERIFICATIE VERPLICHT" in note for note in result.notes))

    def test_abn_uses_configured_quick_ratio_threshold(self):
        result = calculate_case(
            entrepreneur_type="IB",
            years=[
                YearInput(
                    year=book_year,
                    saldo_fiscale_winst=income,
                    current_assets=100_000,
                    inventories=20_000,
                    current_liabilities=100_000,
                    equity=30_000,
                    total_assets=100_000,
                )
                for book_year, income in ((2023, 40_000), (2024, 45_000), (2025, 50_000))
            ],
            policy=POLICIES["ABN_AMRO_MATRIX_2024"],
            current_month=9,
        )
        self.assertEqual(result.ratio_flags[2025]["Quick Ratio"], "Akkoord")
        self.assertTrue(any("Quick ratio getoetst op minimaal 0.80" in note for note in result.notes))

    def test_abn_starter_factor_12_to_23_months(self):
        result = calculate_case(
            entrepreneur_type="IB",
            years=[year(2024, 40_000), year(2025, 40_000)],
            policy=POLICIES["ABN_AMRO_MATRIX_2024"],
            current_month=3,
            entrepreneur_months=18,
        )
        self.assertEqual(result.final_income, 30_000)
        self.assertTrue(any("75%" in note for note in result.notes))

    def test_abn_starter_factor_24_to_35_months(self):
        result = calculate_case(
            entrepreneur_type="IB",
            years=[year(2023, 40_000), year(2024, 40_000), year(2025, 40_000)],
            policy=POLICIES["ABN_AMRO_MATRIX_2024"],
            current_month=3,
            entrepreneur_months=30,
        )
        self.assertEqual(result.final_income, 36_000)
        self.assertTrue(any("90%" in note for note in result.notes))

    def test_abn_under_12_months_requires_review(self):
        result = calculate_case(
            entrepreneur_type="IB",
            years=[year(2025, 40_000)],
            policy=POLICIES["ABN_AMRO_MATRIX_2024"],
            current_month=3,
            entrepreneur_months=8,
        )
        self.assertTrue(any("minder dan 12 maanden" in note for note in result.notes))


if __name__ == "__main__":
    unittest.main()
