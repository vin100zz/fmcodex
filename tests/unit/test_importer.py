from pathlib import Path
import unittest

from core.config import load_config
from core.domain import SimulationStatus
from core.world import import_source_data


WORKSPACE = Path(__file__).resolve().parents[2]


class ImporterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")
        cls.report = import_source_data(WORKSPACE / "data", cls.config)

    def test_identifies_the_configured_active_clubs(self) -> None:
        self.assertEqual(self.report.active_club_count, 96)

    def test_selects_exactly_thirty_players_for_each_active_club(self) -> None:
        self.assertEqual(self.report.active_player_count, 2880)
        selected = [player for player in self.report.players if player.simulation_status is SimulationStatus.ACTIVE]
        counts: dict[int, int] = {}
        for player in selected:
            self.assertIsNotNone(player.club_id)
            counts[player.club_id] = counts.get(player.club_id, 0) + 1
        self.assertEqual(len(counts), 96)
        self.assertTrue(all(count == 30 for count in counts.values()))

    def test_decodes_accented_source_names(self) -> None:
        self.assertTrue(any(player.name == "Mbappé, Kylian" for player in self.report.players))

    def test_maps_every_source_position(self) -> None:
        self.assertEqual(self.report.unknown_position_count, 0)
