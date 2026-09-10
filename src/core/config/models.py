from __future__ import annotations

from dataclasses import field
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class StartDateConfig:
    annee: int = Field(ge=1)
    mois: int = Field(ge=1, le=12)
    jour: int = Field(ge=1, le=31)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class CompetitionConfig:
    pays: str = Field(min_length=3, max_length=3)
    nom: str = Field(min_length=1)
    niveau: int = Field(ge=1)
    nb_clubs: int = Field(ge=2)
    division_id: int


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class ActiveRosterConfig:
    joueurs_max_par_club: int = Field(ge=11)
    tri: tuple[Literal["value_source_desc", "wage_source_desc", "unique_id_asc"], ...]


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class RegenSourcesConfig:
    dossier: str
    nations: str
    prenoms_pattern: str
    noms_pattern: str

    def directory(self, workspace: Path) -> Path:
        return workspace / self.dossier


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class ImportConfig:
    effectif_actif: ActiveRosterConfig
    sources_regens: RegenSourcesConfig


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class SeasonConfig:
    debut_mois: int = Field(ge=1, le=12)
    debut_jour: int = Field(ge=1, le=31)
    fin_mois: int = Field(ge=1, le=12)
    fin_jour: int = Field(ge=1, le=31)
    jours_entre_journees: int = Field(ge=1)
    points_victoire: int = Field(ge=0)
    points_nul: int = Field(ge=0)
    points_defaite: int = Field(ge=0)
    criteres_departage: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class MarketWindowConfig:
    debut_mois: int = Field(ge=1, le=12)
    debut_jour: int = Field(ge=1, le=31)
    fin_mois: int = Field(ge=1, le=12)
    fin_jour: int = Field(ge=1, le=31)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class TransferWindowsConfig:
    ete: MarketWindowConfig
    hiver: MarketWindowConfig
    tours_par_jour: int = Field(ge=1)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class KeyDateConfig:
    mois: int = Field(ge=1, le=12)
    jour: int = Field(ge=1, le=31)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class KeyDatesConfig:
    promotion_centre_formation: KeyDateConfig
    liberation_contrats_expires: KeyDateConfig
    bilan_demographique: KeyDateConfig


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class MatchRulesConfig:
    joueurs_sur_terrain: int = Field(ge=1)
    remplacements_max: int = Field(ge=0)
    fenetres_remplacement: int = Field(ge=0)
    taille_banc: int = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class WorldConfig:
    version_config: int = Field(ge=1)
    date_depart: StartDateConfig
    competitions_simulees: tuple[CompetitionConfig, ...]
    importation: ImportConfig
    saison: SeasonConfig
    mercato: TransferWindowsConfig
    dates_cles: KeyDatesConfig
    regles_match: MatchRulesConfig


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class AnalyticEngineConfig:
    buts_attendus_base: float = Field(gt=0)
    sensibilite_ecart_force: float = Field(ge=0)
    bonus_domicile_buts: float = Field(ge=0)
    buts_attendus_min: float = Field(gt=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class AttributeBoundsConfig:
    min: int = Field(ge=1)
    max: int = Field(le=100)


@dataclass(frozen=True, slots=True)
class GameConfig:
    world: WorldConfig
    analytic_engine: AnalyticEngineConfig
    attribute_bounds: AttributeBoundsConfig
    attribute_names: frozenset[str]
    positions: frozenset[str]
    config_directory: Path
    raw_documents: dict[str, object] = field(repr=False, compare=False)
