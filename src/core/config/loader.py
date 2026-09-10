from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from core.config.models import (
    AnalyticEngineConfig,
    AttributeBoundsConfig,
    GameConfig,
    DefaultBlockHeightConfig,
    FatigueStateConfig,
    InitialPlayerStateConfig,
    InjuryStateConfig,
    LineupSelectionConfig,
    ManagementConfig,
    DemographicConfig,
    SuspensionStateConfig,
    ImplicationConfig,
    PossessionEngineConfig,
    WorldConfig,
)


class ConfigError(ValueError):
    """Raised when a configuration file is malformed or inconsistent."""


CONFIG_FILES = frozenset(
    {
        "attributs",
        "benchmarks",
        "demographie",
        "etats",
        "formations",
        "ia_gestion",
        "implications",
        "monde",
        "moteur_match",
    }
)

EXPECTED_TOP_LEVEL_KEYS: dict[str, frozenset[str]] = {
    "attributs": frozenset(
        {"liste", "bornes", "composites", "note_globale", "profils_generation", "malus_hors_poste"}
    ),
    "benchmarks": frozenset(
        {
            "execution", "affrontements_reference", "distribution_scores", "stats_match", "saison",
            "formations", "oracle", "demographie", "economie", "performance", "ordre_calibrage",
        }
    ),
    "demographie": frozenset(
        {"progression", "estimation_potentiel", "cohorte", "cible_postes", "generation", "centres_formation", "sorties"}
    ),
    "etats": frozenset({"fatigue", "blessures", "suspensions", "forme", "moral", "remplacements"}),
    "formations": frozenset({"formations", "hauteur_bloc"}),
    "ia_gestion": frozenset(
        {"valorisation", "utilite", "profil_cible", "budgets", "mercato", "contrats", "garde_fous", "personnalite_club", "selection"}
    ),
    "implications": frozenset({"zones", "couloirs", "vertical_attaque", "vertical_defense", "lateral"}),
    "monde": frozenset(
        {"version_config", "date_depart", "competitions_simulees", "importation", "saison", "mercato", "dates_cles", "regles_match"}
    ),
    "moteur_match": frozenset(
        {"chronologie", "transitions", "densite", "couloirs", "occasion", "coups_arretes", "turnover", "cartons", "recalcul_notes", "analytique"}
    ),
}


def load_config(directory: Path) -> GameConfig:
    """Load the complete configuration set and validate cross-document invariants."""
    documents = _load_documents(directory)
    world = _validate_world(documents["monde"])
    analytic_engine = _validate_analytic_engine(documents["moteur_match"])
    attribute_bounds = _validate_attribute_bounds(documents["attributs"])
    possession_engine = _validate_possession_engine(documents["moteur_match"])
    implications = _validate_implications(documents["implications"])
    composites = _validate_composites(documents["attributs"])
    morale_match_amplitude = _validate_morale_amplitude(documents["etats"])
    initial_player_state = _validate_initial_player_state(documents["etats"])
    default_block_height = _validate_default_block_height(documents["formations"])
    fatigue_state = _validate_fatigue_state(documents["etats"])
    injury_state = _validate_injury_state(documents["etats"], fatigue_state)
    suspension_state = _validate_suspension_state(documents["etats"])
    lineup_selection = _validate_lineup_selection(documents["ia_gestion"])
    management = _validate_management(documents["ia_gestion"])
    demographics = _validate_demographics(documents["demographie"])
    attribute_names = _attribute_names(documents["attributs"])
    positions = _positions(documents["formations"])
    _validate_coherence(documents, world, attribute_names, positions)
    return GameConfig(
        world=world,
        analytic_engine=analytic_engine,
        attribute_bounds=attribute_bounds,
        possession_engine=possession_engine,
        implications=implications,
        composites=composites,
        morale_match_amplitude=morale_match_amplitude,
        initial_player_state=initial_player_state,
        default_block_height=default_block_height,
        fatigue_state=fatigue_state,
        injury_state=injury_state,
        suspension_state=suspension_state,
        lineup_selection=lineup_selection,
        management=management,
        demographics=demographics,
        attribute_names=frozenset(attribute_names),
        positions=frozenset(positions),
        config_directory=directory,
        raw_documents=documents,
    )


def _load_documents(directory: Path) -> dict[str, object]:
    if not directory.is_dir():
        raise ConfigError(f"Configuration directory does not exist: {directory}")

    available = {path.stem for path in directory.glob("*.json")}
    missing = CONFIG_FILES - available
    unexpected = available - CONFIG_FILES
    if missing:
        raise ConfigError(f"Missing configuration files: {', '.join(sorted(missing))}")
    if unexpected:
        raise ConfigError(f"Unexpected configuration files: {', '.join(sorted(unexpected))}")

    documents: dict[str, object] = {}
    for name in CONFIG_FILES:
        try:
            with (directory / f"{name}.json").open(encoding="utf-8") as file:
                loaded = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise ConfigError(f"Cannot read {name}.json: {error}") from error
        document = _without_notes(loaded)
        if not isinstance(document, dict):
            raise ConfigError(f"{name}.json must contain an object")
        expected = EXPECTED_TOP_LEVEL_KEYS[name]
        keys = frozenset(document)
        if keys != expected:
            missing_keys = expected - keys
            extra_keys = keys - expected
            details = []
            if missing_keys:
                details.append(f"missing: {', '.join(sorted(missing_keys))}")
            if extra_keys:
                details.append(f"unknown: {', '.join(sorted(extra_keys))}")
            raise ConfigError(f"Invalid keys in {name}.json ({'; '.join(details)})")
        documents[name] = document
    return documents


def _without_notes(value: object) -> object:
    if isinstance(value, dict):
        return {key: _without_notes(item) for key, item in value.items() if key != "_note"}
    if isinstance(value, list):
        return [_without_notes(item) for item in value]
    return value


def _validate_world(document: object) -> WorldConfig:
    try:
        return TypeAdapter(WorldConfig).validate_python(document)
    except ValidationError as error:
        raise ConfigError(f"Invalid monde.json: {error}") from error


def _validate_analytic_engine(document: object) -> AnalyticEngineConfig:
    root = _mapping(document, "moteur_match.json")
    try:
        return TypeAdapter(AnalyticEngineConfig).validate_python(root["analytique"])
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid moteur_match.json analytic configuration: {error}") from error


def _validate_attribute_bounds(document: object) -> AttributeBoundsConfig:
    root = _mapping(document, "attributs.json")
    try:
        bounds = TypeAdapter(AttributeBoundsConfig).validate_python(root["bornes"])
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid attributs.json bounds: {error}") from error
    if bounds.min >= bounds.max:
        raise ConfigError("Attribute minimum must be lower than maximum")
    return bounds


def _validate_possession_engine(document: object) -> PossessionEngineConfig:
    root = _mapping(document, "moteur_match.json")
    required = ("chronologie", "transitions", "densite", "couloirs", "occasion", "turnover", "cartons")
    try:
        payload = {key: root[key] for key in required}
        return TypeAdapter(PossessionEngineConfig).validate_python(payload)
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid moteur_match.json possession configuration: {error}") from error


def _validate_implications(document: object) -> ImplicationConfig:
    try:
        return TypeAdapter(ImplicationConfig).validate_python(document)
    except ValidationError as error:
        raise ConfigError(f"Invalid implications.json: {error}") from error


def _validate_composites(document: object) -> dict[str, dict[str, float]]:
    root = _mapping(document, "attributs.json")
    try:
        composites = root["composites"]
        if not isinstance(composites, dict):
            raise TypeError("composites must be an object")
        return {
            str(name): {str(attribute): float(weight) for attribute, weight in _mapping(weights, str(name)).items()}
            for name, weights in composites.items()
        }
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigError(f"Invalid attributs.json composites: {error}") from error


def _validate_morale_amplitude(document: object) -> float:
    root = _mapping(document, "etats.json")
    try:
        amplitude = _number(_mapping(root["moral"], "etats.moral")["amplitude_effet_match"], "etats.moral")
    except KeyError as error:
        raise ConfigError(f"Invalid etats.json moral configuration: {error}") from error
    if not 0 <= amplitude <= 1:
        raise ConfigError("Moral match amplitude must be between 0 and 1")
    return amplitude


def _validate_initial_player_state(document: object) -> InitialPlayerStateConfig:
    root = _mapping(document, "etats.json")
    try:
        fatigue = _mapping(root["fatigue"], "etats.fatigue")
        form = _mapping(root["forme"], "etats.forme")
        moral = _mapping(root["moral"], "etats.moral")
        return TypeAdapter(InitialPlayerStateConfig).validate_python(
            {"fatigue": fatigue["initiale"], "form": form["initiale"], "morale": moral["initial"]}
        )
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid initial player state: {error}") from error


def _validate_default_block_height(document: object) -> DefaultBlockHeightConfig:
    root = _mapping(document, "formations.json")
    try:
        source = _mapping(root["hauteur_bloc"], "formations.hauteur_bloc")
        height = TypeAdapter(DefaultBlockHeightConfig).validate_python(
            {key: source[key] for key in ("min", "max", "defaut")}
        )
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid formations.json block height: {error}") from error
    if height.min > height.max or not height.min <= height.defaut <= height.max:
        raise ConfigError("Default block height must be within configured bounds")
    return height


def _validate_fatigue_state(document: object) -> FatigueStateConfig:
    root = _mapping(document, "etats.json")
    try:
        return TypeAdapter(FatigueStateConfig).validate_python(root["fatigue"])
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid etats.json fatigue configuration: {error}") from error


def _validate_injury_state(document: object, fatigue: FatigueStateConfig) -> InjuryStateConfig:
    root = _mapping(document, "etats.json")
    try:
        injuries = _mapping(root["blessures"], "etats.blessures")
        payload = {
            key: injuries[key]
            for key in (
                "probabilite_base_par_possession",
                "facteur_fatigue_max",
                "fragilite_min",
                "fragilite_max",
                "probabilite_quotidienne_hors_match",
                "gravites",
                "forme_retour_de_blessure",
            )
        }
        payload["fatigue_retour_de_blessure"] = fatigue.fatigue_retour_de_blessure
        state = TypeAdapter(InjuryStateConfig).validate_python(payload)
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid etats.json injury configuration: {error}") from error
    if abs(sum(item.part for item in state.gravites) - 1.0) > 1e-6:
        raise ConfigError("Injury severity shares must sum to 1.0")
    if any(item.jours_min > item.jours_max for item in state.gravites):
        raise ConfigError("Injury severity duration bounds are invalid")
    return state


def _validate_suspension_state(document: object) -> SuspensionStateConfig:
    root = _mapping(document, "etats.json")
    try:
        state = TypeAdapter(SuspensionStateConfig).validate_python(root["suspensions"])
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid etats.json suspension configuration: {error}") from error
    if state.matches_rouge_min > state.matches_rouge_max:
        raise ConfigError("Red-card suspension bounds are invalid")
    return state


def _validate_lineup_selection(document: object) -> LineupSelectionConfig:
    root = _mapping(document, "ia_gestion.json")
    try:
        return TypeAdapter(LineupSelectionConfig).validate_python(root["selection"])
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid ia_gestion.json lineup selection configuration: {error}") from error


def _validate_management(document: object) -> ManagementConfig:
    root = _mapping(document, "ia_gestion.json")
    try:
        payload = {
            "valuation": root["valorisation"],
            "budgets": root["budgets"],
            "garde_fous": root["garde_fous"],
            "roster_target": _roster_target_payload(root["profil_cible"]),
            "market": _market_payload(root["mercato"]),
        }
        management = TypeAdapter(ManagementConfig).validate_python(payload)
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid ia_gestion.json management configuration: {error}") from error
    if management.garde_fous.effectif_min > management.garde_fous.effectif_max:
        raise ConfigError("Management roster minimum cannot exceed maximum")
    if management.garde_fous.gardiens_min > management.garde_fous.gardiens_recommandes:
        raise ConfigError("Management goalkeeper minimum cannot exceed recommended count")
    return management


def _roster_target_payload(value: object) -> dict[str, object]:
    source = _mapping(value, "ia_gestion.profil_cible")
    try:
        depth = _mapping(source["effectif_par_poste"], "ia_gestion.profil_cible.effectif_par_poste")
        return {
            "niveau_base": source["niveau_base"],
            "poids_reputation": source["poids_reputation"],
            "decote_rotation": source["decote_rotation"],
            "decote_doublure": source["decote_doublure"],
            "effectif_par_poste": {
                position: {
                    "starters": _mapping(specification, position)["titulaires"],
                    "rotations": _mapping(specification, position)["rotations"],
                    "backups": _mapping(specification, position)["doublures"],
                }
                for position, specification in depth.items()
            },
        }
    except KeyError as error:
        raise ConfigError(f"Invalid ia_gestion.json roster target configuration: {error}") from error


def _market_payload(value: object) -> dict[str, object]:
    source = _mapping(value, "ia_gestion.mercato")
    try:
        return {
            key: source[key]
            for key in (
                "negociations_actives_max",
                "taille_shortlist",
                "seuil_vendeur_multiplicateur",
                "seuil_vendeur_reduction_surplus",
                "poids_patience_negociation",
                "ratio_contre_offre",
                "score_joueur",
            )
        }
    except KeyError as error:
        raise ConfigError(f"Invalid ia_gestion.json market configuration: {error}") from error


def _validate_demographics(document: object) -> DemographicConfig:
    root = _mapping(document, "demographie.json")
    try:
        payload = {
            "progression": root["progression"],
            "potential_estimate": root["estimation_potentiel"],
            "regen_generation": root["generation"],
            "position_distribution": root["cible_postes"],
        }
        demographics = TypeAdapter(DemographicConfig).validate_python(payload)
    except (KeyError, ValidationError) as error:
        raise ConfigError(f"Invalid demographie.json configuration: {error}") from error
    if demographics.progression.evaluation != "mensuelle":
        raise ConfigError("Player progression must be monthly")
    if demographics.regen_generation.age_min > demographics.regen_generation.age_max:
        raise ConfigError("Regen generation age bounds are invalid")
    if abs(sum(demographics.position_distribution.values()) - 1.0) > 1e-6:
        raise ConfigError("Demographic position distribution must sum to 1.0")
    return demographics


def _attribute_names(document: object) -> set[str]:
    root = _mapping(document, "attributs.json")
    categories = _mapping(root["liste"], "attributs.liste")
    names = {name for values in categories.values() for name in _string_list(values, "attributs.liste")}
    if len(names) != 13:
        raise ConfigError("attributs.json must define exactly 13 unique attributes")
    return names


def _positions(document: object) -> set[str]:
    root = _mapping(document, "formations.json")
    formations = _mapping(root["formations"], "formations.formations")
    positions = {position for formation in formations.values() for position in _string_list(formation, "formation")}
    if not positions:
        raise ConfigError("formations.json must define at least one position")
    return positions


def _validate_coherence(
    documents: Mapping[str, object],
    world: WorldConfig,
    attribute_names: set[str],
    positions: set[str],
) -> None:
    if len(world.competitions_simulees) != 5:
        raise ConfigError("v1 requires exactly five simulated competitions")
    if len({competition.division_id for competition in world.competitions_simulees}) != len(world.competitions_simulees):
        raise ConfigError("Simulated competition division IDs must be unique")
    if sum(competition.nb_clubs for competition in world.competitions_simulees) != 96:
        raise ConfigError("Simulated competition club count must be 96")
    if world.importation.effectif_actif.joueurs_max_par_club != 30:
        raise ConfigError("The v1 active roster size must be 30 players per club")
    if world.regles_match.joueurs_sur_terrain != 11:
        raise ConfigError("Match rules must use eleven players per side")

    attributes = _mapping(documents["attributs"], "attributs.json")
    composites = _mapping(attributes["composites"], "attributs.composites")
    for composite_name, weights in composites.items():
        mapping = _mapping(weights, f"composite {composite_name}")
        if set(mapping) - attribute_names:
            raise ConfigError(f"Composite {composite_name} references an unknown attribute")
        if abs(sum(_number(value, f"composite {composite_name}") for value in mapping.values()) - 1.0) > 1e-6:
            raise ConfigError(f"Composite {composite_name} weights must sum to 1.0")

    formations = _mapping(_mapping(documents["formations"], "formations.json")["formations"], "formations.formations")
    for name, formation in formations.items():
        lineup = _string_list(formation, f"formation {name}")
        if len(lineup) != world.regles_match.joueurs_sur_terrain:
            raise ConfigError(f"Formation {name} must contain eleven positions")

    implications = _mapping(documents["implications"], "implications.json")
    for section in ("vertical_attaque", "vertical_defense", "lateral"):
        matrix = _mapping(implications[section], f"implications.{section}")
        if set(matrix) != positions:
            raise ConfigError(f"implications.{section} must define every formation position")

    demographic = _mapping(documents["demographie"], "demographie.json")
    distribution = _mapping(demographic["cible_postes"], "demographie.cible_postes")
    if set(distribution) != positions:
        raise ConfigError("demographie.cible_postes must define every formation position")
    if abs(sum(_number(value, "demographie.cible_postes") for value in distribution.values()) - 1.0) > 1e-6:
        raise ConfigError("demographie.cible_postes must sum to 1.0")


def _mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ConfigError(f"{context} must be an object")
    return value


def _string_list(value: object, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{context} must be a string list")
    return tuple(value)


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{context} must contain numeric values")
    return float(value)
