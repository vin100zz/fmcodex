from pathlib import Path
from random import Random
import unittest

from core.config import load_config
from core.engine import AnalyticMatchEngine, TeamStrength


WORKSPACE = Path(__file__).resolve().parents[2]


class AnalyticEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = load_config(WORKSPACE / "config")
        cls.engine = AnalyticMatchEngine(config.analytic_engine)

    def test_equal_teams_keep_the_configured_goal_average(self) -> None:
        home_goals, away_goals = self.engine.expected_goals(
            TeamStrength(club_id=1, rating=70), TeamStrength(club_id=2, rating=70)
        )

        self.assertAlmostEqual(home_goals - away_goals, 0.30)
        self.assertAlmostEqual(home_goals + away_goals, 2.70)

    def test_stronger_team_has_higher_expected_goals(self) -> None:
        home_goals, away_goals = self.engine.expected_goals(
            TeamStrength(club_id=1, rating=80), TeamStrength(club_id=2, rating=60)
        )

        self.assertGreater(home_goals, away_goals)

    def test_simulation_is_reproducible_with_an_injected_rng(self) -> None:
        home = TeamStrength(club_id=1, rating=75)
        away = TeamStrength(club_id=2, rating=65)

        first = self.engine.simulate(home, away, Random(20260910))
        second = self.engine.simulate(home, away, Random(20260910))

        self.assertEqual(first, second)

    def test_distribution_converges_toward_expected_goals(self) -> None:
        home = TeamStrength(club_id=1, rating=70)
        away = TeamStrength(club_id=2, rating=70)
        expected_home, expected_away = self.engine.expected_goals(home, away)
        rng = Random(7)
        simulations = 10000
        scores = [self.engine.simulate(home, away, rng) for _ in range(simulations)]

        self.assertAlmostEqual(sum(score.home_goals for score in scores) / simulations, expected_home, delta=0.05)
        self.assertAlmostEqual(sum(score.away_goals for score in scores) / simulations, expected_away, delta=0.05)
