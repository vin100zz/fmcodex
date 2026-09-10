# Fatigue, blessures, suspensions

> Toutes les valeurs numériques de ce document sont dans `config/etats.json`.
> Les tableaux ci-dessous documentent les valeurs initiales ; la source de
> vérité est le JSON. Aucune constante ne doit apparaître dans le code.

## Pourquoi ces mécanismes sont obligatoires

Sans eux, la sélection est un problème résolu : on aligne toujours son meilleur
onze, et la décision disparaît. L'entraînement étant supprimé du jeu, **c'est la
fatigue qui doit porter la rotation**.

## Fatigue

Valeur dans [0.0, 1.0], 1.0 = frais. Multiplie tous les composites.

### Consommation en match

```python
def consommer(joueur, minutes, intensite):
    base = 0.0042 * minutes                    # ~0.38 sur 90 minutes
    resistance = 0.7 + 0.6 * (joueur.endurance / 100)
    return base * intensite / resistance
```

`intensite` vient de la hauteur de bloc : 0.85 en bloc bas, 1.0 en équilibré,
1.20 en pressing haut. Un pressing haut coûte cher — c'est le prix de la
récupération avancée.

Un joueur de 90 d'endurance perd environ 0.30 sur un match complet, un joueur de
40 environ 0.45.

### Récupération

```python
def recuperer(joueur, jours):
    vitesse = 0.10 + 0.05 * (joueur.endurance / 100)
    facteur_age = 1.15 if joueur.age < 24 else (0.85 if joueur.age > 31 else 1.0)
    joueur.fatigue = min(1.0, joueur.fatigue + jours * vitesse * facteur_age)
```

Environ 3 à 4 jours pour récupérer complètement d'un match. C'est ce qui rend une
semaine à deux matches réellement contraignante et force la rotation.

### Effet en match

La fatigue est recalculée par **paliers de 5 minutes**, pas en continu, pour ne
pas recalculer les agrégats de zone à chaque possession.

Un joueur sous 0.55 déclenche une alerte visible dans l'interface de match et un
signal pour l'IA de remplacement.

## Blessures

### Survenue

Deux sources.

**En match**, à chaque possession impliquant le joueur :

```python
p_blessure = P_BASE * (1.9 - joueur.fatigue) * fragilite(joueur) * intensite
```

`P_BASE` calibré pour environ **1.1 blessure par match** toutes équipes
confondues. La fatigue quasi double le risque : c'est le lien qui rend la
rotation rationnelle et pas seulement esthétique.

**Hors match**, faible probabilité quotidienne, indépendante de la fatigue.
Représente 15 à 20 % des blessures.

### Gravité

Tirée dans une distribution à forte asymétrie droite :

| Gravité | Part | Durée |
|---|---|---|
| Légère | 55 % | 3 – 10 jours |
| Moyenne | 32 % | 2 – 6 semaines |
| Grave | 11 % | 2 – 5 mois |
| Très grave | 2 % | 6 – 12 mois |

### Effets

```python
@dataclass(slots=True)
class Blessure:
    date_debut: Date
    date_fin: Date
    gravite: Gravite
    description: str
```

- Indisponible jusqu'à `date_fin`
- Au retour, la fatigue repart à 0.5 et la forme à 0.85
- Une blessure de plus de 3 mois après 30 ans applique une **pénalité permanente**
  de 2 à 5 points sur `vitesse` et `endurance`
- Une `fragilite` par joueur, tirée à la création et stable, multiplie le risque
  entre 0.6 et 1.8 — certains joueurs sont durablement fragiles

### Cibles

| Métrique | Cible |
|---|---|
| Blessures par club et par saison | 12 – 18 |
| Joueurs indisponibles simultanément par club | 2 – 4 |
| Blessures longues (> 2 mois) par club et par saison | 0.8 – 1.5 |

## Suspensions

### Cartons

Générés lors des turnovers défensifs, pondérés par la zone et le composite
défensif du joueur impliqué.

| Métrique | Cible par match |
|---|---|
| Cartons jaunes | 3.5 – 4.5 |
| Cartons rouges | 0.10 – 0.15 |

### Règles

- Rouge direct : 1 à 3 matches selon la gravité tirée
- Deux jaunes dans un même match : expulsion + 1 match
- Cumul de 5 jaunes sur la saison : 1 match, compteur remis à zéro
- Cumul de 10 jaunes : 2 matches
- Compteur de jaunes remis à zéro en fin de saison

```python
@dataclass(slots=True)
class Suspension:
    matches_restants: int
    motif: str
```

Décrémenté à chaque match de la compétition concernée, joué ou non par le club.

### Effet d'une expulsion en match

Le joueur est retiré du onze, les agrégats de zone sont recalculés. La perte de
densité est absorbée automatiquement par `facteur_densite` — aucun malus
artificiel à ajouter. L'équipe réduite passe en bloc bas de force
(`h = max(h - 0.5, -1.0)`).

## Forme

Marche aléatoire lente, bornée à [0.7, 1.3], avec retour à la moyenne :

```python
def maj_forme(joueur, note_derniere_perf, rng):
    cible = 1.0 + 0.06 * (note_derniere_perf - 6.5)
    joueur.forme += 0.25 * (cible - joueur.forme) + rng.gauss(0, 0.03)
    joueur.forme = clamp(joueur.forme, 0.7, 1.3)
```

Un joueur en série de bonnes performances entre en forme. C'est le seul
mécanisme de « momentum » du jeu, et il suffit.

## Moral

Dérive lentement selon : temps de jeu réel comparé à l'attente du joueur,
résultats du club, satisfaction contractuelle. Amplitude d'effet en match limitée
à ±5 % — le moral doit surtout alimenter l'IA des contrats et les demandes de
départ, pas dominer les résultats.

## Décision de remplacement (IA)

Évaluée toutes les 5 minutes à partir de la 55e.

Déclencheurs, par priorité :

1. Blessure — remplacement immédiat, obligatoire
2. Joueur sous 0.50 de fatigue et remplaçant disponible à ce poste
3. Joueur averti, sous 0.60 de fatigue, en zone défensive — risque de second jaune
4. Ajustement tactique : mené à moins de 20 minutes de la fin, entrée d'un profil
   offensif et hausse de la hauteur de bloc
5. Économie : mène de deux buts, entrée d'un profil défensif, repos pour un cadre

Maximum 5 remplacements, en 3 fenêtres, comme dans le règlement réel.
