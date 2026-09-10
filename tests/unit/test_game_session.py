from pathlib import Path
import unittest

from api.session import GameSession


WORKSPACE = Path(__file__).resolve().parents[2]


class GameSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.session = GameSession.create(WORKSPACE / "config", WORKSPACE / "data", seed=7)

    def test_bootstraps_world_and_competitions(self) -> None:
        state = self.session.world_state()

        self.assertEqual(state["date"], "2026-08-10")
        self.assertEqual(len(self.session.competition_summaries()), 5)
        self.assertEqual(len(self.session.standings(16)), 18)

    def test_advancing_a_round_publishes_results_and_player_conditions(self) -> None:
        self.session.advance_round(seed=7)
        calendar = self.session.competition_calendar(16, round_number=1)
        roster = self.session.club_roster(calendar[0]["home_club_id"])

        self.assertEqual(self.session.current_round, 1)
        self.assertTrue(all(item["result"] is not None for item in calendar))
        self.assertEqual(len(roster), 30)
        self.assertTrue(any(player["fatigue"] < 1.0 for player in roster))
