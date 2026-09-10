from pathlib import Path
import unittest

from core.config import load_config
from core.world import PlayedMatch, calculate_standings


WORKSPACE = Path(__file__).resolve().parents[2]


class StandingsTests(unittest.TestCase):
    def test_orders_teams_by_configured_points_then_goal_difference(self) -> None:
        rules = load_config(WORKSPACE / "config").world.saison
        table = calculate_standings(
            (1, 2, 3),
            (
                PlayedMatch(1, 2, 2, 0),
                PlayedMatch(2, 3, 2, 1),
                PlayedMatch(3, 1, 1, 1),
            ),
            rules,
        )

        self.assertEqual([row.club_id for row in table], [1, 2, 3])
        self.assertEqual(table[0].points, 4)
        self.assertEqual(table[0].goal_difference, 2)
