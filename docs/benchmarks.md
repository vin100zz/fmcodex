# Benchmarks

## Rôle

Les benchmarks ne sont pas des tests. Un test vérifie une règle sur un cas ; un
benchmark mesure une **distribution** sur des dizaines de milliers de
simulations et la compare à une cible.

C'est le seul moyen de savoir si le moteur et l'IA produisent un monde crédible.
Le harnais est écrit **avant** le moteur de production et reste le premier outil
de travail pendant tout le projet.

## Structure

```
benchmarks/
  runner.py            exécution, parallélisation, graine
  cibles.py            chargement de config/benchmarks.json
  rapport.py           sortie console + JSON + CSV
  variantes/           dossiers de surcharge de config
  suites/
    match.py           distribution des résultats d'un affrontement
    saison.py          points, champion, écart-type
    stats_match.py     tirs, xG, possession, cartons
    formations.py      matrice formation contre formation
    oracle.py          moteur possession contre moteur analytique
    demographie.py     population sur 30 saisons
    economie.py        masse salariale, transferts, concentration
    performance.py     temps CPU par match et par saison
```

## Invocation

```bash
python -m benchmarks.runner --suite match --iterations 10000
python -m benchmarks.runner --suite tout --rapport rapports/2026-09-10.json
python -m benchmarks.runner --suite match --balayage moteur.k_prog=0.03:0.09:0.01
```

Sortie console : une ligne par cible, verte ou rouge, avec valeur mesurée,
cible, tolérance et écart.

```
match/psg_dom_toulouse    victoire  0.732   cible 0.75 ±0.05   OK
match/psg_dom_toulouse    nul       0.211   cible 0.20 ±0.04   OK
match/psg_dom_toulouse    defaite   0.057   cible 0.05 ±0.03   OK
stats/tirs_par_equipe     12.8      cible 13.0 ±1.0            OK
stats/xg_par_equipe        1.61      cible  1.40 ±0.15         ECHEC  (+0.21)
```

Sortie JSON pour l'historisation, CSV pour tracer l'évolution d'un paramètre lors
d'un balayage.

## Suite `match` — affrontements de référence

C'est la suite que tu consultes en premier. Elle simule N fois un affrontement
donné avec des effectifs figés et compare la distribution victoire / nul /
défaite.

Les affrontements de référence sont déclarés dans `config/benchmarks.json`, avec
la cible attendue. Les clubs réels y sont référencés par leur `Unique ID` de
`data/clubs.csv`, jamais par leur nom : celui-ci peut changer ou être dupliqué
dans l'export source. Exemples :

| Affrontement | V | N | D |
|---|---|---|---|
| PSG domicile contre Toulouse | 0.75 | 0.20 | 0.05 |
| PSG extérieur contre Toulouse | 0.62 | 0.24 | 0.14 |
| Deux clubs de niveau égal, domicile | 0.45 | 0.27 | 0.28 |
| Manchester City domicile contre Burnley | 0.78 | 0.16 | 0.06 |
| Real Madrid domicile contre Barcelone | 0.44 | 0.27 | 0.29 |

Vérifier aussi la distribution des scores, pas seulement l'issue : un moteur qui
donne le bon taux de victoire avec des 5-0 systématiques est faux.

| Métrique | Cible |
|---|---|
| Score le plus fréquent | 1-0 ou 2-1 |
| Part des matches à 0 but | 7 – 9 % |
| Part des matches à 4 buts ou plus | 22 – 28 % |
| Écart de buts moyen | 1.3 – 1.6 |

**Effectifs figés** : la suite doit utiliser un instantané des effectifs stocké
dans `benchmarks/effectifs/`, pas l'état courant du monde. Sinon les résultats
changent à chaque mercato et deviennent incomparables.

## Suite `stats_match`

Vérifie que le match ressemble à un match avant de vérifier qui gagne.
**À valider en premier** : ne pas toucher aux coefficients de talent tant que ces
chiffres ne sont pas justes.

| Métrique (par match, par équipe) | Cible |
|---|---|
| Possessions | 100 – 120 |
| Tirs | 12 – 14 |
| xG cumulé | 1.3 – 1.5 |
| Buts | 1.35 |
| Possession | 45 – 55 % |
| Avantage domicile | +0.30 but |
| Buts sur coup de pied arrêté | 25 – 30 % |
| Cartons jaunes | 1.75 – 2.25 |
| Cartons rouges | 0.05 – 0.08 |
| Répartition par couloir | 33 % ±5 chacun |
| xG par attaque, axe contre aile | axe supérieur |

## Suite `saison`

Simule N saisons complètes. Plus révélateur que la validation match par match.

| Métrique | Cible |
|---|---|
| Points du champion | 80 – 90 |
| Points du dernier | 25 – 35 |
| Écart-type des points | 12 – 16 |
| Buts du meilleur buteur | 22 – 30 |
| Titres du club le plus fort sur 100 saisons | 55 – 80 % |
| Corrélation réputation / classement | 0.70 – 0.85 |

La dernière ligne est importante : une corrélation de 0.95 signifie un
championnat sans surprise, une corrélation de 0.4 un championnat aléatoire.

## Suite `formations`

Chaque formation contre chaque autre, **effectifs strictement identiques des deux
côtés**. Produit une matrice de taux de victoire.

**Critère** : aucune formation ne dépasse 55 % de victoires contre l'ensemble du
champ, aucune ne descend sous 45 %.

Levier de correction : l'exposant de `facteur_densite`
(`moteur.densite.exposant`, 0.5 par défaut). Le baisser vers 0.4 si les
formations défensives dominent, le monter vers 0.6 si toutes les formations sont
indiscernables.

C'est le benchmark le plus rentable du projet. Un déséquilibre de formation
contamine ensuite toute l'IA de transferts, qui se met à recruter uniquement le
profil alimentant la formation dominante.

## Suite `oracle`

Compare le moteur par possessions au moteur analytique de Poisson sur les mêmes
affrontements. Les distributions doivent être compatibles (test de
Kolmogorov-Smirnov, ou simple comparaison des trois taux à ±0.04).

Un écart signale un bug dans le moteur par possessions, pas un désaccord de
modèle.

## Suite `demographie`

30 saisons sans interface. Compare l'année 1 et l'année 30.

| Indicateur | Critère |
|---|---|
| Effectif total actif | stable à ±5 % |
| Pyramide des âges | forme stable |
| Histogramme des niveaux | superposable |
| Parts par poste | ±2 points |
| Parts par nation | ±3 points |
| **Joueurs au-dessus de 85** | **±20 %** |
| Âge moyen des effectifs | 25 – 27 |

Le nombre de joueurs au-dessus de 85 est **l'indicateur canari** : statistique de
queue, il dérive en premier. Le surveiller à chaque modification du modèle de
progression.

## Suite `economie`

25 saisons. Vérifie que l'IA de gestion ne dégénère pas.

| Indicateur | Critère |
|---|---|
| Part des joueurs > 80 dans les 3 meilleurs clubs | ≤ 25 % |
| Masse salariale moyenne | pas de dérive exponentielle |
| Transferts par club et par fenêtre estivale | 3 – 7 |
| Clubs différents champions sur 25 saisons, par pays | ≥ 4 |
| Clubs au solde négatif en permanence | 0 |
| Transferts depuis les clubs dormants | 25 – 40 % du total |

La dernière ligne valide que le marché extérieur fonctionne : si elle tombe à
zéro, l'économie des 5 championnats s'est refermée.

## Suite `performance`

| Métrique | Cible |
|---|---|
| Un match, moteur possession | < 20 ms |
| Une saison complète (1 752 matches) | < 40 s |
| 100 saisons en mode analytique | < 60 s |
| Chargement des données (32 000 joueurs) | < 10 s |
| Sauvegarde complète | < 2 s |

Si la simulation d'une saison dépasse la minute, le calibrage devient pénible et
c'est la boucle de travail entière qui se dégrade. Traiter la performance comme
une cible, pas comme une optimisation.

## Balayage de paramètre

```bash
python -m benchmarks.runner --suite match --balayage moteur.k_prog=0.03:0.09:0.01
```

Le runner génère une surcharge de config par valeur, exécute la suite, et sort un
CSV exploitable. C'est la méthode de calibrage : on ne devine pas un coefficient,
on balaie et on lit la courbe.

Ordre de calibrage recommandé :

1. `stats_match` — le match ressemble à un match
2. `formations` — aucune formation ne domine
3. `match` — les bons favoris gagnent dans les bonnes proportions
4. `saison` — le championnat est crédible
5. `demographie` et `economie` — le monde tient dans la durée

Ne jamais calibrer une étape avant que la précédente soit verte : les
coefficients des étapes suivantes dépendent des précédentes.

## Reproductibilité

Chaque exécution enregistre : graine, version de config, empreinte des effectifs
utilisés, révision du code. Un rapport non reproductible ne vaut rien pour
comparer deux versions du moteur.
