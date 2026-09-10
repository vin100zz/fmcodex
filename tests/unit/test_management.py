from pathlib import Path
from random import Random
import unittest

from core.ai import (
    ClubBudget,
    ClubFinancialProfile,
    MarketClub,
    PlayerEconomicProfile,
    RosterMember,
    TransferOffer,
    TransferTarget,
    assess_roster,
    can_register_signing,
    derive_club_budget,
    estimate_market_value,
    resolve_market_turn,
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

    def test_roster_assessment_reports_gaps_and_surplus(self) -> None:
        players = (
            RosterMember(player_id=1, position="GB", overall=85),
            RosterMember(player_id=2, position="GB", overall=75),
            RosterMember(player_id=3, position="GB", overall=65),
            RosterMember(player_id=4, position="GB", overall=60),
            RosterMember(player_id=5, position="BU", overall=70),
        )

        assessment = assess_roster(players, reputation=70, config=self.config)

        self.assertEqual(assessment.target_level, 75.6)
        self.assertIn(4, assessment.surplus_player_ids)
        self.assertTrue(any(need.position == "DC" and need.current_player_id is None for need in assessment.needs))
        self.assertTrue(any(need.position == "BU" and need.current_player_id == 5 for need in assessment.needs))

    def test_market_turn_resolves_competing_offers_and_counteroffers(self) -> None:
        clubs = (
            self._market_club(1, reputation=65, patience=0.5),
            self._market_club(2, reputation=80, patience=0.2),
            self._market_club(3, reputation=90, patience=0.2),
        )
        targets = (
            TransferTarget(10, seller_club_id=1, market_value=10_000_000, expected_weekly_wage=100_000, seller_surplus=0.0),
            TransferTarget(11, seller_club_id=1, market_value=10_000_000, expected_weekly_wage=100_000, seller_surplus=0.0),
        )
        offers = (
            TransferOffer(2, player_id=10, transfer_fee=17_000_000, weekly_wage=200_000, projected_playing_time=0.8, sporting_ambition=1.0),
            TransferOffer(3, player_id=10, transfer_fee=17_000_000, weekly_wage=100_000, projected_playing_time=1.0, sporting_ambition=1.0),
            TransferOffer(2, player_id=11, transfer_fee=14_000_000, weekly_wage=100_000, projected_playing_time=1.0, sporting_ambition=1.0),
        )

        result = resolve_market_turn(clubs, targets, offers, self.config, Random(7))

        self.assertEqual(len(result.completed), 1)
        self.assertEqual(result.completed[0].buyer_club_id, 2)
        self.assertEqual(result.completed[0].player_id, 10)
        self.assertEqual(len(result.counter_offers), 1)
        self.assertEqual(result.counter_offers[0].player_id, 11)

    def _market_club(self, club_id: int, reputation: int, patience: float) -> MarketClub:
        return MarketClub(
            club_id=club_id,
            financial=ClubFinancialProfile(
                reputation=reputation,
                country_code="FRA",
                previous_finish=4,
                balance=50_000_000,
                weekly_wage_bill=100_000,
            ),
            budget=ClubBudget(seasonal_revenue=100_000_000, transfer_budget=50_000_000, weekly_wage_cap=1_000_000),
            negotiation_patience=patience,
        )
