# Modèle de données

> Toutes les valeurs numériques citées ici sont dans `config/`. Le code lit la
> config, il ne contient aucune constante de règle.

## Périmètre : actif et dormant

L'utilisateur fournit ~26 000 clubs et ~32 000 joueurs. Seuls ~96 clubs sont
simulés en v1. Dans chacun, seuls les **30 meilleurs joueurs à l'import** sont
en simulation complète. Le reste n'est pas jeté : **c'est le marché extérieur
ou un joueur en régime allégé**.

| Statut | Clubs | Comportement |
|---|---|---|
| `ACTIF` | ~96 | matches simulés, IA complète, progression, mercato actif |
| `DORMANT` | ~25 900 | aucun match, joueurs figés ou progression simplifiée, accessible au mercato |

Un club dormant :
- ne joue aucun match, n'a ni classement ni calendrier
- conserve son effectif, consultable dans l'interface
- **répond aux offres** des clubs actifs, selon une heuristique simplifiée
  (`ia.mercato.clubs_dormants`)
- peut démarcher un joueur d'un club actif en fin de contrat ou en surplus

Ses joueurs progressent selon un modèle allégé (courbe d'âge seule, sans temps de
jeu) pour éviter de simuler 30 000 trajectoires en détail tout en évitant que le
marché extérieur se fige.

Le passage `DORMANT → ACTIF` doit être une simple bascule de statut : c'est ainsi
que les divisions inférieures seront ajoutées plus tard.

```python
class StatutClub(Enum):
    ACTIF = "actif"
    DORMANT = "dormant"
```

## Entités

### Joueur

```python
@dataclass(slots=True)
class Joueur:
    id: int
    nom: str
    prenom: str
    nationalite: str          # code ISO 3 lettres
    date_naissance: Date

    poste: Poste              # poste principal
    postes_secondaires: dict[Poste, float]   # affinité 0.0-1.0

    attributs: Attributs      # les 13 valeurs 1-100, voir docs/attributs.md
    potentiel: int            # 1-100, valeur RÉELLE, jamais exposée telle quelle

    forme: float              # 0.7-1.3, dérive lentement
    fatigue: float            # 0.0-1.0, 1.0 = frais
    moral: float              # 0.0-1.0

    blessure: Blessure | None
    suspension: Suspension | None

    club_id: int | None       # None = agent libre
    contrat: Contrat | None
    statut_simulation: StatutSimulation  # ACTIF ou ALLEGE
```

Le `potentiel` est la valeur vraie. L'interface et l'IA ne manipulent qu'une
**estimation bruitée** (voir `docs/progression-demographie.md`).

### Contrat

```python
@dataclass(slots=True)
class Contrat:
    salaire_hebdo: int
    date_fin: Date
    date_signature: Date
```

### Club

```python
@dataclass(slots=True)
class Club:
    id: int
    nom: str
    nom_court: str
    pays: str
    competition_id: int

    statut: StatutClub        # ACTIF ou DORMANT
    reputation: int           # 1-100, pilote budget, attractivité, centre
    note_centre_formation: int  # 1-100

    budget_transfert: int     # euros disponibles cette saison
    masse_salariale_max: int  # euros par semaine
    solde: int

    formation_preferee: Formation
    personnalite: PersonnaliteClub
```

### PersonnaliteClub

Quatre scalaires dans [0, 1], tirés une fois à la création du monde et stables.
Ils créent la diversité de comportement de l'IA sans code spécifique par club.

```python
@dataclass(slots=True)
class PersonnaliteClub:
    appetit_risque: float      # tolérance à payer cher un potentiel incertain
    preference_jeunes: float   # 0 = confirmés, 1 = jeunes
    agressivite_salariale: float
    patience_negociation: float
```

### Competition

```python
@dataclass(slots=True)
class Competition:
    id: int
    nom: str
    pays: str
    niveau: int               # 1 en v1 pour toutes
    club_ids: list[int]
    calendrier: list[Journee]
```

### Match

```python
@dataclass(slots=True)
class Match:
    id: int
    competition_id: int
    journee: int
    date: Date
    domicile_id: int
    exterieur_id: int
    resultat: ResultatMatch | None   # None si non joué
```

### ResultatMatch

```python
@dataclass(slots=True)
class ResultatMatch:
    buts_dom: int
    buts_ext: int
    evenements: list[Evenement]      # ordre chronologique
    stats_dom: StatsEquipe
    stats_ext: StatsEquipe
    notes: dict[int, float]          # joueur_id -> note 1-10
```

Un `Evenement` porte : minute, type (but, tir, arrêt, carton, blessure,
remplacement), joueur principal, joueur secondaire éventuel, zone et couloir.
C'est la source du compte rendu de match et de toutes les statistiques.

### Monde

Objet racine, unique, qui contient tout.

```python
@dataclass(slots=True)
class Monde:
    date: Date
    saison: int
    graine: int
    joueurs: dict[int, Joueur]
    clubs: dict[int, Club]
    competitions: dict[int, Competition]
    matches: dict[int, Match]
    historique: Historique
    prochain_id: int
```

## Historique et volumétrie

Le détail par match ne doit pas s'accumuler indéfiniment.

- **Saison en cours et saison précédente** : `ResultatMatch` complet conservé
- **Au-delà** : agrégation en totaux par joueur et par saison

```python
@dataclass(slots=True)
class SaisonJoueur:
    saison: int
    club_id: int
    competition_id: int
    matches: int
    minutes: int
    buts: int
    passes_decisives: int
    note_moyenne: float
    cartons_jaunes: int
    cartons_rouges: int
```

Conserver aussi, sans limite de durée car peu volumineux :
- l'historique des transferts par joueur (date, club source, club cible, montant)
- le palmarès par club et par compétition
- la trajectoire des attributs par joueur, échantillonnée une fois par saison

À 1 752 matches par saison, le détail de deux saisons représente environ
3 500 objets `ResultatMatch`. C'est parfaitement tenable en mémoire.

## Données fournies par l'utilisateur

`data/clubs.csv` (26 760 lignes) et `data/players.csv` (32 370 lignes),
export réel d'un jeu de gestion tiers. Format réel constaté : séparateur
`;`, encodage Latin-1/cp1252 (pas UTF-8), guillemets sur chaque champ.
**Aucun club n'est codé en dur dans le code.**

**clubs.csv** — colonnes réelles

```
Unique ID, Name, Nation, Division, Status, Stad Cap, Division ID
```

Ni `reputation`, ni `note_centre_formation`, ni `budget_transfert`, ni
`masse_salariale_max` ne sont fournis. **Décision provisoire (v0)** : ces
champs sont synthétisés à partir de `Stad Cap` (+ un peu d'aléatoire),
dans un module d'import isolé, remplaçable quand de vraies valeurs seront
fournies.

Le périmètre actif est déterminé par `config/monde.json →
competitions_simulees[].division_id` croisé avec la colonne `Division ID`
des clubs — **pas** avec la colonne `Division` (texte libre, ambigu : par
exemple le texte `"Premier League"` apparaît sur 233 lignes dans tout le
monde, alors que `Division ID == 11` désigne exactement les 20 clubs de la
première division anglaise).

**players.csv** — colonnes réelles

```
Name, Nation, Position, Club, Int Caps, Int Goals, Wage, Value,
Date Of Birth, Contract End, Unique ID, Club ID
```

Aucun des 13 attributs de jeu (`passe`, `technique`, `finition`...) ni le
`potentiel` ne sont fournis. **Décision provisoire (v0)** : ils sont
synthétisés à partir de `Value`/`Wage` (comme approximation d'un niveau
global, en inversant grossièrement `ia_gestion.valorisation`) puis
répartis entre attributs via les profils de poste de
`config/attributs.json → profils_generation`, comme pour un regen. Cette
synthèse est isolée dans un module dédié pour être remplacée d'un bloc le
jour où une vraie source d'attributs est disponible.

### Sélection de l'effectif simulé

Après avoir identifié les clubs actifs, l'import conserve en régime `ACTIF` les
30 premiers joueurs de chacun de ces clubs. Le classement est déterministe :
`Value` source décroissante, puis `Wage` décroissant, puis `Unique ID` croissant.
Tous les autres joueurs restent chargés, rattachés à leur club et marqués
`ALLEGE` ; ils n'entrent ni dans les compositions, ni dans les statistiques de
la saison, ni dans la démographie détaillée. Cette règle est dans
`config/monde.json`, pas dans le code.

### Sources des regens

`data/regens/` contient les listes de prénoms et noms pondérées, générées à
partir des joueurs fournis, ainsi que `nations.csv`. En v1, ces listes couvrent
les cinq pays simulés ; le vivier externe reste abstrait. Les fichiers sont
regénérables et ne constituent pas une source éditée à la main.

**Limite connue** : synthétiser le niveau à partir de `Value` puis valider
`ia_gestion.valeur()` par benchmark contre des valeurs de marché rend ce
benchmark partiellement circulaire tant que les vraies données ne sont pas
là — la formule sera calée sur des attributs eux-mêmes dérivés de la
valeur qu'elle est censée prédire.

`Position` utilise la notation du jeu source (ex. `"AM RL, ST"`, `"D C,
DM"`, 250 valeurs distinctes), pas l'énum `Poste` du domaine — table de
correspondance à dériver de cette grammaire, à affiner une fois en place.

**Fichiers complémentaires à générer si non fournis** (nécessaires aux regens) :
- `prenoms_<pays>.csv` et `noms_<pays>.csv` avec une colonne de pondération
- `nations.csv` : code, poids de production, force du football

## Validation au chargement

**Ces contrôles ne s'appliquent qu'aux clubs actifs.** Un club dormant peut être
incomplet ou vide sans conséquence.

Refuser de démarrer si, pour un club actif :
- il a moins de 16 joueurs sous contrat
- il n'a aucun gardien
Refuser de démarrer, quel que soit le statut, si :
- un attribut sort de [1, 100]
- un `club_id` de joueur ne correspond à aucun club
- une compétition déclarée dans `monde.json` n'a pas le bon nombre de clubs

Émettre un avertissement, sans bloquer, si :
- un club actif a plus de 32 joueurs
- la masse salariale d'un club actif dépasse son plafond
- une date de fin de contrat est antérieure à la date de début de partie
  (la corriger en la reportant d'un an)

Le rapport de chargement affiche le décompte actif / dormant et la liste des
compétitions reconnues. C'est le premier écran à consulter en cas de données
inattendues.

## Persistance

Sauvegarde complète du `Monde` en JSON gzippé.

```python
def sauvegarder(monde: Monde, chemin: Path) -> None: ...
def charger(chemin: Path) -> Monde: ...
```

- `schema_version` en tête de fichier, entier incrémenté à chaque changement
- `to_dict()` / `from_dict()` explicites sur chaque entité
- Autosauvegarde à chaque passage de journée simulée
- Slots multiples, nommés par l'utilisateur
- Cible : moins de 2 s pour une sauvegarde complète (32 000 joueurs)

**Optimisation si nécessaire** : les clubs dormants changent peu. Sérialiser
séparément un socle dormant, réécrit seulement quand il a été modifié, et un
fichier de partie contenant l'état actif. Ne le faire que si la cible de 2 s
n'est pas tenue — mesurer avant d'optimiser.

Un module `migrations/` transforme un fichier d'une version vers la suivante.
Écrire la première migration dès qu'un champ change, sans exception.
