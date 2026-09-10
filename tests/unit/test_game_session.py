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
        statistics = self.session.competition_statistics(16, "tirs")
        self.assertTrue(statistics)
        self.assertTrue(all(item["matches"] > 0 for item in statistics))
        match = self.session.match_detail(calendar[0]["id"])
        self.assertEqual(match["id"], calendar[0]["id"])
        player = self.session.player_detail(roster[0]["id"])
        self.assertEqual(player["id"], roster[0]["id"])

    def test_club_catalog_includes_active_and_dormant_source_clubs(self) -> None:
        clubs = self.session.clubs()

        self.assertGreater(len(clubs), 96)
        self.assertEqual(len(self.session.clubs(competition_id=16)), 18)

    def test_cannot_start_a_new_season_before_the_current_one_ends(self) -> None:
        fresh_session = GameSession.create(WORKSPACE / "config", WORKSPACE / "data", seed=8)

        with self.assertRaises(ValueError):
            fresh_session.start_next_season()

    def test_advancing_a_day_plays_the_scheduled_first_round(self) -> None:
        fresh_session = GameSession.create(WORKSPACE / "config", WORKSPACE / "data", seed=9)

        fresh_session.advance_day()

        self.assertEqual(fresh_session.current_round, 1)
