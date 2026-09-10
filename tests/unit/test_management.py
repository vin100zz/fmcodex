from pathlib import Path
import unittest

from core.ai import (
    ClubFinancialProfile,
    PlayerEconomicProfile,
    can_register_signing,
    derive_club_budget,
    estimate_market_value,
)
from core.config import load_config


WORKSPACE = Path(__file__).resolve().parents[2]


class ManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")

    def test_market_value_rewards_youth_and_convex_talent(self) -> None:
        young = PlayerEconomicProfile(75, 75, 20, "BU", contract_months_remaining=24)
        veteran = PlayerEconomicProfile(75, 75, 31, "BU", contract_months_remaining=24)
        strong = PlayerEconomicProfile(90, 90, 20, "BU", contract_months_remaining=24)

        young_value = estimate_market_value(young, self.config)
        veteran_value = estimate_market_value(veteran, self.config)
        strong_value = estimate_market_value(strong, self.config)

        self.assertGreater(young_value, veteran_value)
        self.assertGreater(strong_value / young_value, 4.0)

    def test_short_contract_discount_is_applied(self) -> None:
        regular = PlayerEconomicProfile(75, 75, 26, "MC", contract_months_remaining=24)
        expiring = PlayerEconomicProfile(75, 75, 26, "MC", contract_months_remaining=6)

        self.assertLess(estimate_market_value(expiring, self.config), estimate_market_value(regular, self.config))

    def test_budget_and_hard_signing_constraints(self) -> None:
        club = ClubFinancialProfile(
            reputation=70,
            country_code="FRA",
            previous_finish=4,
            balance=10_000_000,
            weekly_wage_bill=100_000,
        )
        budget = derive_club_budget(club, self.config)

        self.assertGreater(budget.transfer_budget, 0)
        self.assertGreater(budget.weekly_wage_cap, club.weekly_wage_bill)
        self.assertTrue(can_register_signing(club, budget, 1_000_000, 10_000, self.config))
        self.assertFalse(can_register_signing(club, budget, budget.transfer_budget + 1, 10_000, self.config))
        self.assertFalse(can_register_signing(club, budget, 1_000_000, budget.weekly_wage_cap, self.config))
