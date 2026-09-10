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
    formation_initiale: str
    sources_regens: RegenSourcesConfig


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class SeasonConfig:
    debut_mois: int = Field(ge=1, le=12)
    debut_jour: int = Field(ge=1, le=31)
    fin_mois: int = Field(ge=1, le=12)
    fin_jour: int = Field(ge=1, le=31)
    jours_entre_journees: int = Field(ge=1)
    matches_par_adversaire: int = Field(ge=1)
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


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class ChronologyConfig:
    duree_match_secondes: int = Field(gt=0)
    duree_possession_min: int = Field(gt=0)
    duree_possession_moyenne: float = Field(gt=0)
    duree_possession_forme_gamma: float = Field(gt=0)
    temps_additionnel_min: int = Field(ge=0)
    temps_additionnel_max: int = Field(ge=0)
    secondes_par_arret_de_jeu: int = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class TransitionConfig:
    k_prog: float = Field(ge=0)
    k_occ: float = Field(ge=0)
    bonus_domicile: float = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class DensityConfig:
    reference: float = Field(gt=0)
    exposant: float = Field(gt=0)
    note_plancher: float = Field(gt=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class LaneConfig:
    beta_softmax: float = Field(ge=0)
    probabilite_changement_aile: float = Field(ge=0, le=1)
    poids_vision_changement_aile: float = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class ChanceConfig:
    xg_base_centre: float = Field(gt=0, lt=1)
    xg_base_frappe: float = Field(gt=0, lt=1)
    multiplicateur_contre: float = Field(gt=0)
    sensibilite_tireur_gardien: float = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class TurnoverConfig:
    zone_declenchant_contre: str
    malus_defensif_contre: float = Field(ge=0)
    malus_defensif_couloir_concerne: float = Field(ge=0)
    duree_malus_possessions: int = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class PossessionEngineConfig:
    chronologie: ChronologyConfig
    transitions: TransitionConfig
    densite: DensityConfig
    couloirs: LaneConfig
    occasion: ChanceConfig
    turnover: TurnoverConfig


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class ImplicationConfig:
    zones: tuple[str, ...]
    couloirs: tuple[str, ...]
    vertical_attaque: dict[str, tuple[float, ...]]
    vertical_defense: dict[str, tuple[float, ...]]
    lateral: dict[str, tuple[float, ...]]


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class InitialPlayerStateConfig:
    form: float = Field(gt=0)
    fatigue: float = Field(ge=0, le=1)
    morale: float = Field(ge=0, le=1)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class DefaultBlockHeightConfig:
    min: float = Field(ge=-1, le=1)
    max: float = Field(ge=-1, le=1)
    defaut: float = Field(ge=-1, le=1)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class BlockIntensityConfig:
    bloc_bas: float = Field(gt=0)
    equilibre: float = Field(gt=0)
    pressing_haut: float = Field(gt=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class FatigueStateConfig:
    initiale: float = Field(ge=0, le=1)
    consommation_par_minute: float = Field(gt=0)
    resistance_base: float = Field(gt=0)
    resistance_facteur_endurance: float = Field(ge=0)
    intensite_par_hauteur_bloc: BlockIntensityConfig
    recuperation_base_par_jour: float = Field(ge=0)
    recuperation_facteur_endurance: float = Field(ge=0)
    facteur_age_jeune: float = Field(gt=0)
    seuil_age_jeune: int = Field(ge=0)
    facteur_age_vieux: float = Field(gt=0)
    seuil_age_vieux: int = Field(ge=0)
    seuil_alerte: float = Field(ge=0, le=1)
    fatigue_retour_de_blessure: float = Field(ge=0, le=1)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class InjurySeverityConfig:
    nom: str
    part: float = Field(gt=0)
    jours_min: int = Field(gt=0)
    jours_max: int = Field(gt=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class InjuryStateConfig:
    probabilite_base_par_possession: float = Field(ge=0, le=1)
    facteur_fatigue_max: float = Field(gt=0)
    fragilite_min: float = Field(gt=0)
    fragilite_max: float = Field(gt=0)
    probabilite_quotidienne_hors_match: float = Field(ge=0, le=1)
    gravites: tuple[InjurySeverityConfig, ...]
    fatigue_retour_de_blessure: float = Field(ge=0, le=1)
    forme_retour_de_blessure: float = Field(gt=0)


@dataclass(frozen=True, slots=True)
class GameConfig:
    world: WorldConfig
    analytic_engine: AnalyticEngineConfig
    attribute_bounds: AttributeBoundsConfig
    possession_engine: PossessionEngineConfig
    implications: ImplicationConfig
    composites: dict[str, dict[str, float]]
    morale_match_amplitude: float
    initial_player_state: InitialPlayerStateConfig
    default_block_height: DefaultBlockHeightConfig
    fatigue_state: FatigueStateConfig
    injury_state: InjuryStateConfig
    attribute_names: frozenset[str]
    positions: frozenset[str]
    config_directory: Path
    raw_documents: dict[str, object] = field(repr=False, compare=False)
