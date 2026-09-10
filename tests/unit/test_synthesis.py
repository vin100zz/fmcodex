from pathlib import Path
from random import Random
import unittest

from core.config import load_config
from core.world import build_lineup, import_source_data, synthesize_active_players


WORKSPACE = Path(__file__).resolve().parents[2]


class SynthesisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")
        imported = import_source_data(WORKSPACE / "data", cls.config)
        cls.players = synthesize_active_players(imported, cls.config, Random(20260910))

    def test_synthesizes_every_active_player_with_bounded_attributes(self) -> None:
        self.assertEqual(len(self.players), 2880)
        for player in self.players.values():
            for attribute in self.config.attribute_names:
                value = getattr(player.attributes, attribute)
                self.assertGreaterEqual(value, self.config.attribute_bounds.min)
                self.assertLessEqual(value, self.config.attribute_bounds.max)

    def test_builds_a_complete_lineup_for_each_active_club(self) -> None:
        imported = import_source_data(WORKSPACE / "data", self.config)
        active_ids = [club.id for club in imported.clubs if club.status.value == "active"]
        lineups = [
            build_lineup(club_id, self.players, self.config, formation="4-3-3", block_height=0.0)
            for club_id in active_ids
        ]

        self.assertEqual(len(lineups), 96)
        self.assertTrue(all(len(lineup.players) == 11 for lineup in lineups))
        self.assertTrue(all(any(player.position == "GB" for player in lineup.players) for lineup in lineups))
