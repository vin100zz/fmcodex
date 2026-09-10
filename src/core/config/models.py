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
class CardConfig:
    probabilite_jaune_par_turnover_defensif: float = Field(ge=0, le=1)
    probabilite_rouge_direct_par_turnover_defensif: float = Field(ge=0, le=1)
    poids_zone_defense: float = Field(ge=0)
    poids_agressivite_tacle: float = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class PossessionEngineConfig:
    chronologie: ChronologyConfig
    transitions: TransitionConfig
    densite: DensityConfig
    couloirs: LaneConfig
    occasion: ChanceConfig
    turnover: TurnoverConfig
    cartons: CardConfig


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


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class YellowThresholdConfig:
    jaunes: int = Field(gt=0)
    matches: int = Field(gt=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class SuspensionStateConfig:
    matches_rouge_min: int = Field(gt=0)
    matches_rouge_max: int = Field(gt=0)
    matches_double_jaune: int = Field(gt=0)
    seuils_cumul_jaunes: tuple[YellowThresholdConfig, ...]
    remise_a_zero_fin_saison: bool


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class LineupSelectionConfig:
    poids_composite: float = Field(ge=0)
    poids_forme: float = Field(ge=0)
    poids_fatigue: float = Field(ge=0)
    seuil_rotation_fatigue: float = Field(ge=0, le=1)
    ecart_niveau_acceptable_rotation: float = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class AgeValueFactorConfig:
    age_min: int = Field(ge=0)
    age_max: int = Field(ge=0)
    facteur: float = Field(gt=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class ContractValueDiscountConfig:
    mois_max: int = Field(gt=0)
    facteur: float = Field(gt=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class PlayerValuationConfig:
    base_euros: int = Field(gt=0)
    exposant: float = Field(gt=0)
    niveau_reference: float
    poids_potentiel_sur_niveau: float = Field(ge=0)
    courbe_age: tuple[AgeValueFactorConfig, ...]
    decote_fin_contrat: tuple[ContractValueDiscountConfig, ...]
    rarete_poste: dict[str, float]


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class RevenueConfig:
    base_par_point_reputation: int = Field(gt=0)
    bonus_classement_premier: int = Field(ge=0)
    decroissance_par_place: float = Field(gt=0)
    multiplicateur_pays: dict[str, float]


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class ClubBudgetConfig:
    part_revenus_transfert: float = Field(ge=0)
    part_solde_transfert: float = Field(ge=0)
    part_revenus_salaires: float = Field(ge=0)
    semaines_par_an: int = Field(gt=0)
    revenus: RevenueConfig


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class RosterGuardConfig:
    effectif_min: int = Field(gt=0)
    effectif_max: int = Field(gt=0)
    gardiens_min: int = Field(gt=0)
    gardiens_recommandes: int = Field(gt=0)
    plafond_salarial_strict: bool
    solde_minimal_autorise: int


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class PositionDepthTargetConfig:
    starters: int = Field(ge=0)
    rotations: int = Field(ge=0)
    backups: int = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class RosterTargetConfig:
    niveau_base: float
    poids_reputation: float = Field(ge=0)
    decote_rotation: float = Field(ge=0)
    decote_doublure: float = Field(ge=0)
    effectif_par_poste: dict[str, PositionDepthTargetConfig]


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class OfferScoreConfig:
    poids_salaire: float = Field(ge=0)
    poids_temps_de_jeu: float = Field(ge=0)
    poids_reputation_club: float = Field(ge=0)
    poids_ambition: float = Field(ge=0)
    bruit_ecart_type: float = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class MarketConfig:
    negociations_actives_max: int = Field(gt=0)
    taille_shortlist: int = Field(gt=0)
    seuil_vendeur_multiplicateur: float = Field(gt=0)
    seuil_vendeur_reduction_surplus: float = Field(ge=0)
    poids_patience_negociation: float = Field(ge=0)
    ratio_contre_offre: float = Field(gt=0)
    score_joueur: OfferScoreConfig


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class ProgressionAgeFactorConfig:
    age_min: int = Field(ge=0)
    age_max: int = Field(ge=0)
    facteur: float


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class ProgressionConfig:
    evaluation: str
    minutes_reference_par_mois: int = Field(gt=0)
    facteur_jeu_min: float = Field(ge=0, le=1)
    amplitude: float = Field(ge=0)
    bruit_ecart_type: float = Field(ge=0)
    courbe_age: tuple[ProgressionAgeFactorConfig, ...]
    poids_declin_par_attribut: dict[str, float]
    plafonne_par_potentiel: bool
    declin_plafonne: bool


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class PotentialEstimateConfig:
    bruit_max: float = Field(ge=0)
    age_convergence: int = Field(ge=0)
    facteur_reputation_observateur: float = Field(ge=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class RegenAgeRatioConfig:
    age: int = Field(ge=0)
    ratio: float = Field(gt=0)


@dataclass(frozen=True, slots=True, kw_only=True, config=ConfigDict(extra="forbid"))
class RegenGenerationConfig:
    potentiel_min: float
    potentiel_amplitude: float = Field(gt=0)
    beta_alpha_nation_moyenne: float = Field(gt=0)
    beta_beta_nation_moyenne: float = Field(gt=0)
    ratio_niveau_sur_potentiel: tuple[RegenAgeRatioConfig, ...]
    bruit_niveau_ecart_type: float = Field(ge=0)
    age_min: int = Field(ge=0)
    age_max: int = Field(ge=0)


@dataclass(frozen=True, slots=True)
class DemographicConfig:
    progression: ProgressionConfig
    potential_estimate: PotentialEstimateConfig
    regen_generation: RegenGenerationConfig
    position_distribution: dict[str, float]


@dataclass(frozen=True, slots=True)
class ManagementConfig:
    valuation: PlayerValuationConfig
    budgets: ClubBudgetConfig
    garde_fous: RosterGuardConfig
    roster_target: RosterTargetConfig
    market: MarketConfig


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
    suspension_state: SuspensionStateConfig
    lineup_selection: LineupSelectionConfig
    management: ManagementConfig
    demographics: DemographicConfig
    attribute_names: frozenset[str]
    positions: frozenset[str]
    config_directory: Path
    raw_documents: dict[str, object] = field(repr=False, compare=False)
