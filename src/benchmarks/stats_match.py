from __future__ import annotations

from random import Random
from typing import Mapping

from benchmarks.match import BenchmarkCheck
from benchmarks.synthetic import synthetic_lineup
from core.config.models import GameConfig
from core.engine import PossessionMatchEngine


def run_stats_match_suite(config: GameConfig, iterations: int, rng: Random) -> tuple[BenchmarkCheck, ...]:
    """Measure the core event-engine distribution with equal synthetic squads."""
    if iterations <= 0:
        raise ValueError("Benchmark iterations must be positive")
    settings = _mapping(config.raw_documents["benchmarks"], "benchmarks.json")
    targets = _mapping(settings["stats_match"], "stats_match")
    formation = _text(targets["formation_reference"], "formation_reference")
    level = int(_number(targets["niveau_joueur_reference"], "niveau_joueur_reference"))
    engine = PossessionMatchEngine(config)
    home = synthetic_lineup(config, club_id=1, level=level, formation=formation)
    away = synthetic_lineup(config, club_id=2, level=level, formation=formation)
    results = tuple(engine.simulate(home, away, rng) for _ in range(iterations))

    possessions = sum(result.home_stats.possessions + result.away_stats.possessions for result in results) / (2 * iterations)
    shots = sum(result.home_stats.shots + result.away_stats.shots for result in results) / (2 * iterations)
    expected_goals = sum(
        result.home_stats.expected_goals + result.away_stats.expected_goals for result in results
    ) / (2 * iterations)
    goals = sum(result.home_goals + result.away_goals for result in results) / (2 * iterations)
    home_possession = sum(result.home_stats.possessions for result in results) / sum(
        result.home_stats.possessions + result.away_stats.possessions for result in results
    ) * 100
    return (
        _range_check("stats_match", "possessions_par_equipe", possessions, _mapping(targets["possessions_par_equipe"], "possessions")),
        _range_check("stats_match", "tirs_par_equipe", shots, _mapping(targets["tirs_par_equipe"], "tirs")),
        _range_check("stats_match", "xg_par_equipe", expected_goals, _mapping(targets["xg_par_equipe"], "xg")),
        _target_check("stats_match", "buts_par_equipe", goals, _mapping(targets["buts_par_equipe"], "buts")),
        _range_check("stats_match", "possession_pct", home_possession, _mapping(targets["possession_pct"], "possession")),
    )


def _range_check(reference_id: str, metric: str, measured: float, bounds: Mapping[str, object]) -> BenchmarkCheck:
    minimum = _number(bounds["min"], f"{metric}.min")
    maximum = _number(bounds["max"], f"{metric}.max")
    return BenchmarkCheck(
        reference_id=reference_id,
        metric=metric,
        measured=measured,
        target=(minimum + maximum) / 2,
        tolerance=(maximum - minimum) / 2,
    )


def _target_check(reference_id: str, metric: str, measured: float, target: Mapping[str, object]) -> BenchmarkCheck:
    return BenchmarkCheck(
        reference_id=reference_id,
        metric=metric,
        measured=measured,
        target=_number(target["cible"], f"{metric}.cible"),
        tolerance=_number(target["tolerance"], f"{metric}.tolerance"),
    )


def _mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return value


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be numeric")
    return float(value)


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be text")
    return value
