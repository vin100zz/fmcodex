from pathlib import Path
from random import Random
import unittest

from core.config import load_config
from core.engine import Attributes, Lineup, MatchPlayer, PossessionMatchEngine


WORKSPACE = Path(__file__).resolve().parents[2]


class PossessionEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")
        cls.engine = PossessionMatchEngine(cls.config)

    def test_is_reproducible_with_a_fixed_rng(self) -> None:
        home = _lineup(1, 70)
        away = _lineup(2, 70)

        first = self.engine.simulate(home, away, Random(20260910))
        second = self.engine.simulate(home, away, Random(20260910))

        self.assertEqual(first, second)

    def test_result_has_consistent_timeline_and_statistics(self) -> None:
        result = self.engine.simulate(_lineup(1, 70), _lineup(2, 70), Random(7))

        self.assertEqual(tuple(event.second for event in result.events), tuple(sorted(event.second for event in result.events)))
        self.assertEqual(result.home_stats.shots + result.away_stats.shots, sum(event.kind == "shot" for event in result.events))
        self.assertEqual(result.home_goals + result.away_goals, sum(event.kind == "goal" for event in result.events))
        self.assertGreater(result.home_stats.possessions + result.away_stats.possessions, 0)

    def test_higher_quality_team_creates_more_expected_goals_over_many_matches(self) -> None:
        strong = _lineup(1, 85)
        weak = _lineup(2, 55)
        rng = Random(13)
        matches = [self.engine.simulate(strong, weak, rng) for _ in range(250)]

        self.assertGreater(
            sum(match.home_stats.expected_goals for match in matches),
            sum(match.away_stats.expected_goals for match in matches),
        )


def _lineup(club_id: int, level: int) -> Lineup:
    positions = ("GB", "DL", "DC", "DC", "DR", "MDC", "MC", "MC", "AILG", "BU", "AILD")
    attributes = Attributes(
        passe=level,
        technique=level,
        finition=level,
        tacle=level,
        jeu_tete=level,
        vision=level,
        placement=level,
        sang_froid=level,
        vitesse=level,
        endurance=level,
        reflexes=level,
        sorties=level,
        relance=level,
    )
    return Lineup(
        club_id=club_id,
        players=tuple(
            MatchPlayer(
                id=club_id * 100 + index,
                position=position,
                attributes=attributes,
                form=1.0,
                fatigue=1.0,
                morale=0.5,
            )
            for index, position in enumerate(positions)
        ),
        block_height=0.0,
    )
