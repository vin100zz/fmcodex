from __future__ import annotations

from dataclasses import dataclass
from math import exp

from core.config.models import GameConfig


@dataclass(frozen=True, slots=True)
class PlayerEconomicProfile:
    overall: float
    potential: float
    age: int
    position: str
    contract_months_remaining: int | None


@dataclass(frozen=True, slots=True)
class ClubFinancialProfile:
    reputation: float
    country_code: str
    previous_finish: int
    balance: int
    weekly_wage_bill: int


@dataclass(frozen=True, slots=True)
class ClubBudget:
    seasonal_revenue: int
    transfer_budget: int
    weekly_wage_cap: int


def estimate_market_value(player: PlayerEconomicProfile, config: GameConfig) -> int:
    """Estimate a transferable player's value from the configured market model."""
    valuation = config.management.valuation
    position_factor = valuation.rarete_poste.get(player.position)
    if position_factor is None:
        raise ValueError(f"Unknown valuation position: {player.position}")
    level = max(player.overall, player.potential * valuation.poids_potentiel_sur_niveau)
    value = valuation.base_euros * exp(valuation.exposant * (level - valuation.niveau_reference))
    value *= _age_factor(player.age, config)
    value *= position_factor
    if player.contract_months_remaining is not None:
        value *= _contract_factor(player.contract_months_remaining, config)
    return max(0, round(value))


def derive_club_budget(club: ClubFinancialProfile, config: GameConfig) -> ClubBudget:
    """Derive independent transfer and wage budgets under the configured safeguards."""
    revenue = config.management.budgets.revenus
    country_factor = revenue.multiplicateur_pays.get(club.country_code)
    if country_factor is None:
        raise ValueError(f"Unknown revenue country: {club.country_code}")
    if club.previous_finish < 1:
        raise ValueError("Previous finish must be positive")
    seasonal_revenue = round(
        (
            revenue.base_par_point_reputation * club.reputation
            + revenue.bonus_classement_premier * revenue.decroissance_par_place ** (club.previous_finish - 1)
        )
        * country_factor
    )
    budgets = config.management.budgets
    return ClubBudget(
        seasonal_revenue=seasonal_revenue,
        transfer_budget=max(0, round(seasonal_revenue * budgets.part_revenus_transfert + club.balance * budgets.part_solde_transfert)),
        weekly_wage_cap=round(seasonal_revenue * budgets.part_revenus_salaires / budgets.semaines_par_an),
    )


def can_register_signing(
    club: ClubFinancialProfile,
    budget: ClubBudget,
    transfer_fee: int,
    weekly_wage: int,
    config: GameConfig,
) -> bool:
    """Apply the hard transfer, wage and balance constraints before a deal is made."""
    safeguards = config.management.garde_fous
    if transfer_fee < 0 or weekly_wage < 0 or transfer_fee > budget.transfer_budget:
        return False
    if safeguards.plafond_salarial_strict and club.weekly_wage_bill + weekly_wage > budget.weekly_wage_cap:
        return False
    return club.balance - transfer_fee >= safeguards.solde_minimal_autorise


def _age_factor(age: int, config: GameConfig) -> float:
    for bracket in config.management.valuation.courbe_age:
        if bracket.age_min <= age <= bracket.age_max:
            return bracket.facteur
    raise ValueError(f"Age {age} is outside the configured valuation curve")


def _contract_factor(months_remaining: int, config: GameConfig) -> float:
    for discount in config.management.valuation.decote_fin_contrat:
        if months_remaining <= discount.mois_max:
            return discount.facteur
    return 1.0
