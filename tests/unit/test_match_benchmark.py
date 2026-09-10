from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
import unittest

from benchmarks.fixtures import build_fixture, load_fixture, save_fixture
from benchmarks.match import run_match_suite
from core.config import load_config
from core.world import derive_active_club_ratings, import_source_data


WORKSPACE = Path(__file__).resolve().parents[2]


class MatchBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")
        imported = import_source_data(WORKSPACE / "data", cls.config)
        cls.fixture = build_fixture(
            derive_active_club_ratings(imported, cls.config),
            WORKSPACE / "data" / "players.csv",
            cls.config.world.version_config,
        )

    def test_fixture_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ratings.json"
            save_fixture(self.fixture, path)
            self.assertEqual(load_fixture(path), self.fixture)

    def test_match_suite_reports_all_reference_metrics(self) -> None:
        checks = run_match_suite(self.config, self.fixture, 100, Random(7))

        self.assertEqual(len(checks), 15)
        self.assertEqual({check.metric for check in checks}, {"victoire", "nul", "defaite"})
