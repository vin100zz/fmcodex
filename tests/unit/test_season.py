from pathlib import Path
from random import Random
import unittest

from core.config import load_config
from core.world import (
    competition_standings,
    create_season_plan,
    import_source_data,
    play_round,
    synthesize_active_players,
)


WORKSPACE = Path(__file__).resolve().parents[2]


class SeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")
        imported = import_source_data(WORKSPACE / "data", cls.config)
        players = synthesize_active_players(imported, cls.config, Random(20260910))
        cls.plan = create_season_plan(imported, players, cls.config, Random(20260910))

    def test_plan_contains_every_v1_fixture(self) -> None:
        self.assertEqual(len(self.plan.competitions), 5)
        self.assertEqual(sum(len(competition.fixtures) for competition in self.plan.competitions), 1752)
        self.assertEqual(len(self.plan.lineups), 96)

    def test_round_plays_each_active_club_once(self) -> None:
        played = play_round(self.plan, round_number=1, config=self.config, rng=Random(7))

        self.assertEqual(len(played.fixtures), 48)
        for competition in self.plan.competitions:
            fixtures = [item for item in played.fixtures if item.fixture.competition_id == competition.id]
            participants = [club_id for fixture in fixtures for club_id in (fixture.fixture.home_club_id, fixture.fixture.away_club_id)]
            self.assertEqual(len(participants), len(set(participants)))
            table = competition_standings(competition, played.fixtures, self.config)
            self.assertEqual(sum(row.played for row in table), len(fixtures) * 2)
