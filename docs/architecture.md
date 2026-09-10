# Architecture

## Objectif

Le projet sera enrichi de façon itérative pendant longtemps. L'architecture doit
rendre chaque ajout local : nouvelle fonctionnalité = nouveau fichier ou nouvelle
implémentation d'interface, pas une modification dispersée dans le code existant.

## Couches

```
web/          ──▶  api/  ──▶  core/  ◀──  benchmarks/
                                 │
                              config/
```

| Couche | Responsabilité | Interdits |
|---|---|---|
| `core/domain` | entités, value objects, règles invariantes | I/O, processus, config globale |
| `core/engine` | simuler un match | connaître le calendrier, la saison, le mercato |
| `core/ai` | décider pour un club | modifier le monde directement |
| `core/world` | faire avancer le temps, orchestrer | contenir des règles de match |
| `core/config` | charger et valider la config | logique métier |
| `api` | exposer des vues, router | contenir des règles de jeu |
| `web` | afficher | dupliquer l'état serveur |
| `benchmarks` | mesurer et calibrer | être importé par `core` |

**Règle de dépendance** : les flèches vont vers `core`, jamais l'inverse.
`core` n'importe rien de `api`, `web` ou `benchmarks`.

## Une responsabilité par fichier

Exemple pour le moteur de match — chaque fichier fait une seule chose :

```
core/engine/
  possession.py        machine à états d'une possession
  notes_zones.py       agrégation qualité × densité par zone et couloir
  composites.py        attributs → composites
  couloirs.py          choix et changement de couloir
  occasion.py          résolution centre / frappe
  coups_arretes.py     branche corners et coups francs
  selection_joueur.py  tirage pondéré du joueur impliqué
  chronologie.py       durée des possessions, temps additionnel
  match.py             orchestration, assemblage du ResultatMatch
  analytique.py        moteur Poisson de référence
```

Test : si un fichier dépasse ~200 lignes ou si son nom nécessite un « et », il
porte deux responsabilités.

## Interfaces d'extension

Chaque point d'évolution connu est déjà une interface en v1, avec une seule
implémentation. Ajouter la fonctionnalité = ajouter une implémentation.

### ClubController

Décrit dans `CLAUDE.md`. `AIController` en v1, `HumanController` plus tard.

### MoteurMatch

```python
class MoteurMatch(Protocol):
    def simuler(self, dom: Equipe, ext: Equipe, cfg: Config, rng: Random) -> ResultatMatch: ...
```

Deux implémentations dès la v1 : `MoteurPossession` et `MoteurAnalytique`. Le
second sert d'oracle et de mode rapide pour simuler les compétitions non suivies.

### Competition

```python
class Competition(Protocol):
    def generer_calendrier(self, clubs: list[Club], saison: int, rng: Random) -> list[Journee]: ...
    def classement(self, matches: list[Match]) -> Classement: ...
    def appliquer_fin_saison(self, monde: Monde) -> list[EvenementSaison]: ...
```

`Championnat` en v1. `Coupe` et `CompetitionEuropeenne` plus tard, sans toucher
au reste. La promotion/relégation est un `EvenementSaison` produit par
`appliquer_fin_saison`, donc localisée.

### RegleTransfert

```python
class RegleTransfert(Protocol):
    def est_applicable(self, joueur: Joueur, source: Club, cible: Club) -> bool: ...
    def appliquer(self, transfert: Transfert, monde: Monde) -> None: ...
```

`TransfertSec` en v1. `Pret`, `ClauseLiberatoire` plus tard.

### Evenement

Hiérarchie fermée d'événements de match (`But`, `Tir`, `Arret`, `Carton`,
`Blessure`, `Remplacement`). Ajouter un type d'événement ne doit pas obliger à
modifier le moteur : le moteur produit, les consommateurs filtrent par type.

## Injection de la configuration

La config est un paramètre, jamais un singleton importé.

```python
# BON
def note_zone(equipe, zone, couloir, phase, cfg: ConfigMoteur) -> float: ...

# INTERDIT
from core.config import CONFIG
def note_zone(equipe, zone, couloir, phase) -> float:
    return ... * CONFIG.d_ref ...
```

Raison : un test doit pouvoir passer une config modifiée, et un benchmark doit
pouvoir balayer un paramètre sans variable globale.

Les objets de config sont des `dataclass(frozen=True)` typés, produits par le
chargeur depuis les JSON. **Le code métier ne manipule jamais de `dict`.**

## Injection de l'aléatoire

Même principe. `Random` est un paramètre explicite, jamais le module global.

Pour les tests, un `RngFixe` implémentant la même interface et renvoyant une
séquence prédéterminée permet de tester une branche précise sans statistiques.

## Mutation du monde

Le cœur ne mute pas le monde en place au fil de l'eau. Il **retourne des
événements**, appliqués ensuite par un applicateur unique.

```python
def jouer_journee(monde: Monde, cfg: Config, rng: Random) -> list[Evenement]: ...
def appliquer(monde: Monde, evenements: list[Evenement]) -> None: ...
```

Bénéfices : les fonctions de simulation restent pures et testables, le journal
d'événements de l'interface est gratuit, et l'annulation devient possible.

## Testabilité

### Tests unitaires (`tests/unit/`)

Rapides, déterministes, sans monde complet. Chaque règle isolément.

Utiliser des **fabriques de test** plutôt que des fixtures figées :

```python
def un_joueur(**overrides) -> Joueur: ...
def un_club(nb_joueurs=25, **overrides) -> Club: ...
def un_onze(formation="4-3-3", niveau=70) -> list[Joueur]: ...
```

Un test qui doit construire vingt-cinq joueurs à la main signale un couplage trop
fort.

### Tests d'intégration (`tests/integration/`)

Scénarios sur plusieurs saisons, graine fixée, assertions sur des invariants :
la population reste stable, aucun club ne dépasse son plafond salarial, aucun
effectif ne descend sous 16 joueurs, aucun joueur n'a d'attribut hors bornes.

Ce sont des tests d'invariants, pas de valeurs exactes.

### Benchmarks (`benchmarks/`)

Distincts des tests : ils mesurent des distributions et prennent des minutes.
Voir `docs/benchmarks.md`.

## Performance

Le profil de charge est concentré : le moteur de match représente l'essentiel du
temps CPU. Boucles serrées, non vectorisables (chaque possession dépend de la
précédente).

Ordre des optimisations, si le besoin se présente :

1. Simuler en mode analytique les compétitions que l'utilisateur ne suit pas
2. Précalculer les agrégats de zone (déjà spécifié : recalcul aux seuls
   changements)
3. Profiler avant toute réécriture
4. En dernier recours, extraire `core/engine/possession.py` vers une extension
   native

Ne jamais réécrire tout le projet dans un autre langage : l'isolement du moteur
rend cette extraction locale.

## Chargement des données

Les 32 000 joueurs et 26 000 clubs sont chargés une fois. Les clubs non simulés
sont **dormants** : présents en mémoire, jamais simulés, accessibles au mercato.

Séparer strictement :

```
core/world/import/
  lecteurs.py       CSV/JSON → dict brut
  validation.py     contrôles d'intégrité
  construction.py   dict → entités du domaine
  perimetre.py      détermination actif / dormant
```

Un changement de format de données fourni ne doit toucher que `lecteurs.py`.
