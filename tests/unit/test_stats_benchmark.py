from pathlib import Path
from random import Random
import unittest

from benchmarks.stats_match import run_stats_match_suite
from core.config import load_config


WORKSPACE = Path(__file__).resolve().parents[2]


class StatsBenchmarkTests(unittest.TestCase):
    def test_produces_the_implemented_core_statistics(self) -> None:
        config = load_config(WORKSPACE / "config")
        checks = run_stats_match_suite(config, iterations=100, rng=Random(7))

        self.assertEqual(
            {check.metric for check in checks},
            {"possessions_par_equipe", "tirs_par_equipe", "xg_par_equipe", "buts_par_equipe", "possession_pct"},
        )
