from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Mapping

from benchmarks.fixtures import RatingFixture
from core.config.models import GameConfig
from core.engine import AnalyticMatchEngine, TeamStrength


class BenchmarkError(ValueError):
    """Raised when a match benchmark has an invalid configuration."""


@dataclass(frozen=True, slots=True)
class BenchmarkCheck:
    reference_id: str
    metric: str
    measured: float
    target: float
    tolerance: float

    @property
    def passed(self) -> bool:
        return abs(self.measured - self.target) <= self.tolerance


def run_match_suite(
    config: GameConfig, fixture: RatingFixture, iterations: int, rng: Random
) -> tuple[BenchmarkCheck, ...]:
    if iterations <= 0:
        raise BenchmarkError("Benchmark iterations must be positive")
    benchmarks = _mapping(config.raw_documents["benchmarks"], "benchmarks.json")
    references = _list(benchmarks["affrontements_reference"], "affrontements_reference")
    engine = AnalyticMatchEngine(config.analytic_engine)
    ratings = fixture.by_club_id()
    checks: list[BenchmarkCheck] = []
    for reference in references:
        definition = _mapping(reference, "reference match")
        home = _team(definition, "domicile", ratings)
        away = _team(definition, "exterieur", ratings)
        outcomes = _simulate_outcomes(engine, home, away, iterations, rng)
        targets = (("victoire", outcomes[0]), ("nul", outcomes[1]), ("defaite", outcomes[2]))
        tolerances = _list(definition["tolerance"], f"{definition['id']}.tolerance")
        if len(tolerances) != len(targets):
            raise BenchmarkError(f"Reference {definition['id']} has invalid tolerances")
        for index, (metric, measured) in enumerate(targets):
            checks.append(
                BenchmarkCheck(
                    reference_id=_text(definition["id"], "reference id"),
                    metric=metric,
                    measured=measured,
                    target=_number(definition[metric], metric),
                    tolerance=_number(tolerances[index], "tolerance"),
                )
            )
    return tuple(checks)


def _simulate_outcomes(
    engine: AnalyticMatchEngine, home: TeamStrength, away: TeamStrength, iterations: int, rng: Random
) -> tuple[float, float, float]:
    home_wins = draws = away_wins = 0
    for _ in range(iterations):
        score = engine.simulate(home, away, rng)
        if score.home_goals > score.away_goals:
            home_wins += 1
        elif score.home_goals == score.away_goals:
            draws += 1
        else:
            away_wins += 1
    return home_wins / iterations, draws / iterations, away_wins / iterations


def _team(definition: Mapping[str, object], side: str, ratings: Mapping[int, ClubRating]) -> TeamStrength:
    club_key = f"{side}_club_id"
    synthetic_key = f"{side}_synthetique"
    if club_key in definition:
        club_id = int(_number(definition[club_key], club_key))
        try:
            rating = ratings[club_id]
        except KeyError as error:
            raise BenchmarkError(f"Fixture does not contain club {club_id}") from error
        return TeamStrength(club_id=club_id, rating=rating.rating)
    synthetic = _mapping(definition.get(synthetic_key), synthetic_key)
    return TeamStrength(
        club_id=int(_number(synthetic["club_id"], f"{synthetic_key}.club_id")),
        rating=_number(synthetic["rating"], f"{synthetic_key}.rating"),
    )


def _mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise BenchmarkError(f"{context} must be an object")
    return value


def _list(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise BenchmarkError(f"{context} must be a list")
    return value


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BenchmarkError(f"{context} must be numeric")
    return float(value)


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise BenchmarkError(f"{context} must be non-empty text")
    return value
