from __future__ import annotations

from dataclasses import dataclass
from math import exp
from random import Random

from core.config.models import AnalyticEngineConfig


@dataclass(frozen=True, slots=True)
class TeamStrength:
    club_id: int
    rating: float


@dataclass(frozen=True, slots=True)
class MatchScore:
    home_goals: int
    away_goals: int
    expected_home_goals: float
    expected_away_goals: float


class AnalyticMatchEngine:
    """Reference Poisson engine used for fast simulations and calibration."""

    def __init__(self, config: AnalyticEngineConfig) -> None:
        self._config = config

    def simulate(self, home: TeamStrength, away: TeamStrength, rng: Random) -> MatchScore:
        expected_home, expected_away = self.expected_goals(home, away)
        return MatchScore(
            home_goals=_poisson(expected_home, rng),
            away_goals=_poisson(expected_away, rng),
            expected_home_goals=expected_home,
            expected_away_goals=expected_away,
        )

    def expected_goals(self, home: TeamStrength, away: TeamStrength) -> tuple[float, float]:
        strength_effect = self._config.sensibilite_ecart_force * (home.rating - away.rating)
        home_goals = (
            self._config.buts_attendus_base
            + self._config.bonus_domicile_buts / 2
            + strength_effect
        )
        away_goals = (
            self._config.buts_attendus_base
            - self._config.bonus_domicile_buts / 2
            - strength_effect
        )
        minimum = self._config.buts_attendus_min
        return max(minimum, home_goals), max(minimum, away_goals)


def _poisson(expected_goals: float, rng: Random) -> int:
    threshold = exp(-expected_goals)
    product = 1.0
    goals = 0
    while product > threshold:
        goals += 1
        product *= rng.random()
    return goals - 1
