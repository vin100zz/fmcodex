from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import exp
from random import Random

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


@dataclass(frozen=True, slots=True)
class RosterMember:
    player_id: int
    position: str
    overall: float


@dataclass(frozen=True, slots=True)
class RosterNeed:
    position: str
    depth: str
    target_level: float
    current_player_id: int | None
    current_level: float | None


@dataclass(frozen=True, slots=True)
class RosterAssessment:
    target_level: float
    needs: tuple[RosterNeed, ...]
    surplus_player_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MarketClub:
    club_id: int
    financial: ClubFinancialProfile
    budget: ClubBudget
    negotiation_patience: float


@dataclass(frozen=True, slots=True)
class TransferTarget:
    player_id: int
    seller_club_id: int
    market_value: int
    expected_weekly_wage: int
    seller_surplus: float


@dataclass(frozen=True, slots=True)
class TransferOffer:
    buyer_club_id: int
    player_id: int
    transfer_fee: int
    weekly_wage: int
    projected_playing_time: float
    sporting_ambition: float


@dataclass(frozen=True, slots=True)
class CompletedTransfer:
    buyer_club_id: int
    seller_club_id: int
    player_id: int
    transfer_fee: int
    weekly_wage: int


@dataclass(frozen=True, slots=True)
class CounterOffer:
    buyer_club_id: int
    seller_club_id: int
    player_id: int
    requested_fee: int


@dataclass(frozen=True, slots=True)
class MarketTurnResult:
    completed: tuple[CompletedTransfer, ...]
    counter_offers: tuple[CounterOffer, ...]
    refused_offer_count: int


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


def assess_roster(
    players: tuple[RosterMember, ...], reputation: float, config: GameConfig
) -> RosterAssessment:
    """Compare an actual roster with its configured positional depth targets."""
    target = config.management.roster_target
    target_level = target.niveau_base + target.poids_reputation * reputation
    by_position = {
        position: tuple(sorted((player for player in players if player.position == position), key=lambda player: (-player.overall, player.player_id)))
        for position in target.effectif_par_poste
    }
    needs: list[RosterNeed] = []
    surplus: list[int] = []
    for position, depth_target in target.effectif_par_poste.items():
        requirements = (
            *(("starter", target_level) for _ in range(depth_target.starters)),
            *(("rotation", target_level - target.decote_rotation) for _ in range(depth_target.rotations)),
            *(("backup", target_level - target.decote_doublure) for _ in range(depth_target.backups)),
        )
        actual = by_position[position]
        for index, (depth, required_level) in enumerate(requirements):
            current = actual[index] if index < len(actual) else None
            if current is None or current.overall < required_level:
                needs.append(
                    RosterNeed(
                        position=position,
                        depth=depth,
                        target_level=required_level,
                        current_player_id=None if current is None else current.player_id,
                        current_level=None if current is None else current.overall,
                    )
                )
        surplus.extend(player.player_id for player in actual[len(requirements) :])
    unknown_positions = {player.position for player in players} - set(target.effectif_par_poste)
    if unknown_positions:
        raise ValueError(f"Unknown roster positions: {', '.join(sorted(unknown_positions))}")
    return RosterAssessment(
        target_level=target_level,
        needs=tuple(sorted(needs, key=lambda need: (need.current_level is not None, need.current_level or -1, need.position))),
        surplus_player_ids=tuple(sorted(surplus)),
    )


def resolve_market_turn(
    clubs: tuple[MarketClub, ...],
    targets: tuple[TransferTarget, ...],
    offers: tuple[TransferOffer, ...],
    config: GameConfig,
    rng: Random,
) -> MarketTurnResult:
    """Resolve one simultaneous market turn without giving an ordering advantage to clubs."""
    club_by_id = {club.club_id: club for club in clubs}
    target_by_id = {target.player_id: target for target in targets}
    if len(club_by_id) != len(clubs) or len(target_by_id) != len(targets):
        raise ValueError("Market clubs and targets must have unique identifiers")
    _validate_offers(offers, club_by_id, target_by_id, config)
    accepted: dict[int, list[TransferOffer]] = defaultdict(list)
    counters: list[CounterOffer] = []
    refused = 0
    for offer in offers:
        target = target_by_id[offer.player_id]
        seller = club_by_id[target.seller_club_id]
        threshold = _seller_threshold(target, seller, config)
        if offer.transfer_fee >= threshold:
            accepted[target.player_id].append(offer)
        elif offer.transfer_fee >= threshold * config.management.market.ratio_contre_offre:
            counters.append(
                CounterOffer(
                    buyer_club_id=offer.buyer_club_id,
                    seller_club_id=target.seller_club_id,
                    player_id=target.player_id,
                    requested_fee=round(threshold),
                )
            )
        else:
            refused += 1
    proposed = [
        _choose_player_offer(target_by_id[player_id], candidate_offers, club_by_id, config, rng)
        for player_id, candidate_offers in accepted.items()
    ]
    remaining_transfer_budget = {club.club_id: club.budget.transfer_budget for club in clubs}
    current_wage_bill = {club.club_id: club.financial.weekly_wage_bill for club in clubs}
    remaining_balance = {club.club_id: club.financial.balance for club in clubs}
    completed: list[CompletedTransfer] = []
    for offer in sorted(proposed, key=lambda item: (item.player_id, item.buyer_club_id)):
        buyer = club_by_id[offer.buyer_club_id]
        if offer.transfer_fee > remaining_transfer_budget[buyer.club_id]:
            refused += 1
            continue
        adjusted_financial = ClubFinancialProfile(
            reputation=buyer.financial.reputation,
            country_code=buyer.financial.country_code,
            previous_finish=buyer.financial.previous_finish,
            balance=remaining_balance[buyer.club_id],
            weekly_wage_bill=current_wage_bill[buyer.club_id],
        )
        if not can_register_signing(adjusted_financial, buyer.budget, offer.transfer_fee, offer.weekly_wage, config):
            refused += 1
            continue
        target = target_by_id[offer.player_id]
        completed.append(
            CompletedTransfer(
                buyer_club_id=buyer.club_id,
                seller_club_id=target.seller_club_id,
                player_id=target.player_id,
                transfer_fee=offer.transfer_fee,
                weekly_wage=offer.weekly_wage,
            )
        )
        remaining_transfer_budget[buyer.club_id] -= offer.transfer_fee
        current_wage_bill[buyer.club_id] += offer.weekly_wage
        remaining_balance[buyer.club_id] -= offer.transfer_fee
    return MarketTurnResult(
        completed=tuple(completed),
        counter_offers=tuple(sorted(counters, key=lambda item: (item.player_id, item.buyer_club_id))),
        refused_offer_count=refused,
    )


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


def _validate_offers(
    offers: tuple[TransferOffer, ...],
    clubs: dict[int, MarketClub],
    targets: dict[int, TransferTarget],
    config: GameConfig,
) -> None:
    offered_by_club: dict[int, int] = defaultdict(int)
    for offer in offers:
        if offer.buyer_club_id not in clubs or offer.player_id not in targets:
            raise ValueError("Transfer offer references an unknown buyer or target")
        if offer.buyer_club_id == targets[offer.player_id].seller_club_id:
            raise ValueError("A club cannot bid for its own player")
        if offer.transfer_fee < 0 or offer.weekly_wage < 0:
            raise ValueError("Transfer fees and wages must be non-negative")
        if not 0 <= offer.projected_playing_time <= 1 or not 0 <= offer.sporting_ambition <= 1:
            raise ValueError("Offer player projections must be within zero and one")
        if not 0 <= targets[offer.player_id].seller_surplus <= 1:
            raise ValueError("Seller surplus must be within zero and one")
        offered_by_club[offer.buyer_club_id] += 1
    if any(count > config.management.market.negociations_actives_max for count in offered_by_club.values()):
        raise ValueError("A club exceeded its configured active-negotiation limit")


def _seller_threshold(target: TransferTarget, seller: MarketClub, config: GameConfig) -> float:
    market = config.management.market
    return target.market_value * (
        market.seuil_vendeur_multiplicateur - market.seuil_vendeur_reduction_surplus * target.seller_surplus
    ) * (1 + market.poids_patience_negociation * seller.negotiation_patience)


def _choose_player_offer(
    target: TransferTarget,
    offers: list[TransferOffer],
    clubs: dict[int, MarketClub],
    config: GameConfig,
    rng: Random,
) -> TransferOffer:
    score = config.management.market.score_joueur
    return max(
        offers,
        key=lambda offer: (
            score.poids_salaire * offer.weekly_wage / max(1, target.expected_weekly_wage)
            + score.poids_temps_de_jeu * offer.projected_playing_time
            + score.poids_reputation_club * clubs[offer.buyer_club_id].financial.reputation / 100
            + score.poids_ambition * offer.sporting_ambition
            + rng.gauss(0, score.bruit_ecart_type),
            -offer.buyer_club_id,
        ),
    )
