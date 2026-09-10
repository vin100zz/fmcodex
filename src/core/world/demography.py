from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from random import Random

from core.config.models import GameConfig
from core.engine import Attributes


@dataclass(frozen=True, slots=True)
class CareerPlayer:
    player_id: int
    full_name: str
    nation_code: str
    position: str
    age: int
    overall: float
    potential: float
    attributes: Attributes


@dataclass(frozen=True, slots=True)
class PotentialRange:
    minimum: float
    maximum: float


@dataclass(frozen=True, slots=True)
class NameEntry:
    value: str
    weight: float


@dataclass(frozen=True, slots=True)
class NationNamePool:
    first_names: tuple[NameEntry, ...]
    last_names: tuple[NameEntry, ...]


def load_nation_name_pool(directory: Path, nation_code: str) -> NationNamePool:
    """Load the generated UTF-8 weighted name lists for one regen nation."""
    return NationNamePool(
        first_names=_read_name_entries(directory / f"prenoms_{nation_code}.csv"),
        last_names=_read_name_entries(directory / f"noms_{nation_code}.csv"),
    )


def progress_player_month(
    player: CareerPlayer, minutes_played: int, config: GameConfig, rng: Random
) -> CareerPlayer:
    """Advance a detailed player by one configured monthly progression step."""
    progression = config.demographics.progression
    age_factor = _age_progression_factor(player.age, config)
    playing_factor = progression.facteur_jeu_min + (1 - progression.facteur_jeu_min) * min(
        max(minutes_played, 0) / progression.minutes_reference_par_mois, 1.0
    )
    delta = (
        age_factor
        * playing_factor
        * (player.potential - player.overall)
        / config.attribute_bounds.max
        * progression.amplitude
        + rng.gauss(0, progression.bruit_ecart_type)
    )
    values = {
        name: _bounded_attribute(
            getattr(player.attributes, name)
            + delta * (1.0 if delta >= 0 else progression.poids_declin_par_attribut[name]),
            config,
        )
        for name in config.attribute_names
    }
    attributes = Attributes(**values)
    overall = _overall(attributes, player.position, config)
    if progression.plafonne_par_potentiel and delta >= 0:
        overall = min(overall, player.potential)
    return CareerPlayer(
        player_id=player.player_id,
        full_name=player.full_name,
        nation_code=player.nation_code,
        position=player.position,
        age=player.age,
        overall=overall,
        potential=player.potential,
        attributes=attributes,
    )


def estimate_potential(player: CareerPlayer, observer_reputation: float | None, config: GameConfig) -> PotentialRange:
    """Return an intentionally uncertain potential range for UI and AI consumers."""
    estimate = config.demographics.potential_estimate
    convergence = min(max(player.age - 15, 0), estimate.age_convergence - 15)
    uncertainty = estimate.bruit_max * (1 - convergence / max(1, estimate.age_convergence - 15))
    if observer_reputation is not None:
        uncertainty *= 1.3 - estimate.facteur_reputation_observateur * observer_reputation / 100
    return PotentialRange(
        minimum=max(config.attribute_bounds.min, player.potential - uncertainty),
        maximum=min(config.attribute_bounds.max, player.potential + uncertainty),
    )


def generate_regen(
    player_id: int,
    nation_code: str,
    names: NationNamePool,
    existing_full_names: frozenset[str],
    config: GameConfig,
    rng: Random,
) -> CareerPlayer:
    """Generate one unique youth player from configured demographic distributions."""
    generation = config.demographics.regen_generation
    age = rng.randint(generation.age_min, generation.age_max)
    potential = generation.potentiel_min + generation.potentiel_amplitude * rng.betavariate(
        generation.beta_alpha_nation_moyenne, generation.beta_beta_nation_moyenne
    )
    position = rng.choices(
        tuple(config.demographics.position_distribution),
        weights=tuple(config.demographics.position_distribution.values()),
        k=1,
    )[0]
    ratio = next(item.ratio for item in generation.ratio_niveau_sur_potentiel if item.age == age)
    overall = max(
        config.attribute_bounds.min,
        min(
            potential,
            potential * ratio * rng.gauss(1.0, generation.bruit_niveau_ecart_type),
        ),
    )
    full_name = _unique_name(names, existing_full_names, rng)
    attributes = _regen_attributes(position, overall, config, rng)
    return CareerPlayer(
        player_id=player_id,
        full_name=full_name,
        nation_code=nation_code,
        position=position,
        age=age,
        overall=_overall(attributes, position, config),
        potential=potential,
        attributes=attributes,
    )


def _age_progression_factor(age: int, config: GameConfig) -> float:
    for bracket in config.demographics.progression.courbe_age:
        if bracket.age_min <= age <= bracket.age_max:
            return bracket.facteur
    raise ValueError(f"Age {age} is outside the configured progression curve")


def _overall(attributes: Attributes, position: str, config: GameConfig) -> float:
    weights = config.raw_documents["attributs"]["note_globale"][position]
    return sum(float(weight) * getattr(attributes, attribute) for attribute, weight in weights.items())


def _regen_attributes(position: str, overall: float, config: GameConfig, rng: Random) -> Attributes:
    profiles = config.raw_documents["attributs"]["profils_generation"]
    offsets = profiles["profils"][position]
    noise = float(profiles["bruit_ecart_type"])
    return Attributes(
        **{
            name: _bounded_attribute(overall + float(offsets.get(name, offsets.get("_autres", 0))) + rng.gauss(0, noise), config)
            for name in config.attribute_names
        }
    )


def _unique_name(names: NationNamePool, existing: frozenset[str], rng: Random) -> str:
    attempts = len(names.first_names) + len(names.last_names)
    for _ in range(attempts):
        first = rng.choices(names.first_names, weights=tuple(item.weight for item in names.first_names), k=1)[0].value
        last = rng.choices(names.last_names, weights=tuple(item.weight for item in names.last_names), k=1)[0].value
        full_name = f"{first} {last}"
        if full_name not in existing:
            return full_name
    raise ValueError("Unable to generate a unique regen name")


def _read_name_entries(path: Path) -> tuple[NameEntry, ...]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            rows = tuple(csv.DictReader(file, delimiter=";"))
    except OSError as error:
        raise ValueError(f"Cannot read regen name pool {path}: {error}") from error
    try:
        entries = tuple(NameEntry(value=row["name"], weight=float(row["weight"])) for row in rows)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid regen name pool {path}") from error
    if not entries or any(not entry.value or entry.weight <= 0 for entry in entries):
        raise ValueError(f"Regen name pool {path} must contain positive weighted names")
    return entries


def _bounded_attribute(value: float, config: GameConfig) -> int:
    return round(max(config.attribute_bounds.min, min(config.attribute_bounds.max, value)))
