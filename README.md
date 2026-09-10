# Football Manager Light — spécifications

Simulateur de football de gestion, usage personnel, mono-utilisateur.
Version allégée : on garde effectif, contrats, transferts, matches, sélection et
remplacements. On supprime entraînement, conférences de presse et discussions
individuelles avec les joueurs.

## Périmètre de la v1

**Inclus**
- 5 championnats simulés : France, Espagne, Italie, Angleterre, Allemagne
- Première division uniquement pour chacun (~96 clubs actifs)
- Saison complète en championnat, matches aller-retour
- Effectifs, contrats, mercato, progression et déclin des joueurs
- Génération de joueurs (regens), fatigue, blessures, suspensions
- **L'utilisateur est observateur** : il ne dirige aucun club, il consulte

**Hors périmètre v1** (mais l'architecture doit les rendre possibles)
- Contrôle d'un club par l'utilisateur
- Divisions inférieures actives, promotion et relégation
- Coupes nationales et compétitions européennes
- Prêts, clauses libératoires, agents

## Données et volumes

L'utilisateur fournit un jeu de données **bien plus large que le périmètre
simulé** :

| Grandeur | Valeur |
|---|---|
| Clubs fournis | ~26 000 |
| Joueurs fournis | ~32 000 |
| Clubs **actifs** (simulés) | ~96 |
| Joueurs en simulation complète | 2 880 (30 × 96 clubs) |
| Matches par saison | ~1 752 |
| Regens par an | ~190 |

Cette asymétrie est une chance, pas une contrainte : **les 25 900 clubs non
simulés constituent le marché extérieur**. Sans eux, l'économie des 5
championnats serait fermée et aucun club ne recruterait à l'étranger ou en
division inférieure.

Voir `docs/modele-donnees.md` pour la distinction actif / dormant.

Ces volumes restent petits pour un serveur : 32 000 joueurs représentent 40 à
80 Mo en mémoire avec `dataclass(slots=True)`. **Tout tient en mémoire, aucune
base de données.**

## Pile technique

- **Serveur** : Python 3.12, FastAPI, état en mémoire dans le processus
- **Cœur de simulation** : fonctions pures, RNG injecté, aucun I/O
- **Front** : HTML / CSS / JavaScript vanilla, sans framework
- **Persistance** : sauvegarde de partie en JSON gzippé, pas de base

## Trois exigences transverses

Elles priment sur la rapidité d'écriture. Un code qui les respecte sera plus long
à produire et beaucoup moins long à faire évoluer.

### Testabilité

Une responsabilité par fichier et par classe. Aucune fonction du cœur ne fait
d'I/O, n'imprime, ni ne lit l'horloge système. Tout aléa passe par un `Random`
injecté. Conséquence : chaque règle de jeu est testable isolément, sans monde
complet ni serveur.

### Extensibilité

Le projet sera enrichi de façon itérative. Les points d'extension connus
(divisions multiples, coupes, contrôle utilisateur, prêts) doivent être des
implémentations d'interfaces existantes, pas des `if` ajoutés dans le code
métier. Voir `docs/architecture.md`.

### Configurabilité

**Aucune valeur de règle de jeu n'est écrite dans le code.** Tous les
coefficients, seuils, courbes, matrices et cibles vivent dans `config/*.json`,
chargés au démarrage et validés par schéma. Le code contient des formules ; les
nombres sont des données.

Cette règle est absolue : si Claude Code écrit `0.45 * passe`, c'est une erreur —
il faut `cfg.composites.progression.attaque.passe`. Voir `docs/configuration.md`.

## Conséquence architecturale du mode observateur

L'utilisateur étant observateur, **les 96 clubs actifs sont pilotés par l'IA**.
Toute décision de club passe par une interface unique :

```python
class ClubController(Protocol):
    def choisir_composition(self, club: Club, match: Match) -> Composition: ...
    def decider_remplacement(self, club: Club, etat: EtatMatch) -> Remplacement | None: ...
    def evaluer_besoins(self, club: Club) -> list[Besoin]: ...
    def repondre_offre(self, club: Club, offre: Offre) -> Reponse: ...
```

En v1, `AIController` est la seule implémentation. L'ajout du contrôle
utilisateur consistera à écrire `HumanController` et à changer une affectation.
**Aucun code métier ne doit tester « est-ce le club de l'utilisateur ».**

## Structure du dépôt

```
config/          fichiers JSON de règles — voir docs/configuration.md
src/
  core/          cœur de simulation, fonctions pures
    domain/      entités et value objects, sans logique de processus
    engine/      moteur de match
    ai/          décisions de club
    world/       progression, démographie, calendrier, mercato
    config/      chargement et validation des fichiers config
  api/           FastAPI, couche mince au-dessus de core
  benchmarks/    harnais de calibrage — voir docs/benchmarks.md
web/             front statique
tests/
  unit/          tests unitaires, rapides, déterministes
  integration/   tests de scénarios sur plusieurs saisons
data/            données fournies par l'utilisateur (clubs, joueurs, noms)
migrations/      transformations de schéma de sauvegarde
```

Layout `src/` : le code s'importe toujours comme `core.xxx`, `api.xxx`,
`benchmarks.xxx` (pas `src.core.xxx`) — seul l'emplacement physique change,
via `pythonpath = ["src"]` dans `pyproject.toml`. `web/` reste hors de
`src/` : ce n'est pas du code Python installable.

`core` ne doit jamais importer depuis `api`, `web` ou `benchmarks`.

## Déterminisme

Toute la simulation est reproductible.

```python
def simuler_match(dom: Equipe, ext: Equipe, cfg: Config, rng: Random) -> ResultatMatch: ...
```

Jamais d'appel au module `random` global. Une graine de partie est stockée dans
la sauvegarde ; rejouer la même partie avec la même graine et la même config doit
produire exactement les mêmes résultats. C'est ce qui rend les benchmarks
exploitables et les bugs reproductibles.

## Conventions

- Code, noms de variables et commentaires **en anglais**
- Type hints partout, `dataclass(slots=True)` pour les entités
- Attributs de joueur sur une échelle **1-100**
- Dates : objet `Date` de jeu, pas `datetime`
- Montants en euros, entiers, pas de flottants
- Nommage des fichiers de config : un domaine par fichier, clés en `snake_case`

## Documents de spécification

| Fichier | Contenu |
|---|---|
| `docs/architecture.md` | Couches, responsabilités, interfaces, testabilité |
| `docs/configuration.md` | Catalogue des fichiers config, chargement, validation |
| `docs/benchmarks.md` | Harnais de calibrage et cibles |
| `docs/modele-donnees.md` | Entités, actif/dormant, persistance, données fournies |
| `docs/attributs.md` | Les 13 attributs et leurs composites |
| `docs/moteur-match.md` | Simulation par possessions, zones, couloirs, formations |
| `docs/etats-joueur.md` | Fatigue, blessures, suspensions |
| `docs/ia-gestion.md` | Valorisation, besoins, mercato, contrats |
| `docs/progression-demographie.md` | Progression, déclin, regens, marché extérieur |
| `docs/ui.md` | Écrans et endpoints |

## Ordre de construction

1. Chargement de la config + validation par schéma
2. Modèle de données + import des données fournies (actif / dormant)
3. Moteur de match analytique (Poisson) — oracle de référence
4. **Harnais de benchmarks**
5. Moteur de match par possessions, calibré contre les cibles
6. Progression, déclin, fatigue, blessures, suspensions
7. IA de gestion et mercato
8. Démographie et regens
9. API puis front

Ne pas passer à l'étape suivante tant que les benchmarks de l'étape courante ne
passent pas au vert. Le harnais arrive **avant** le moteur de production :
pendant les premières semaines, il est le produit.
