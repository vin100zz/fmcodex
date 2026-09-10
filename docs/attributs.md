# Attributs et composites

> Toutes les valeurs numériques de ce document sont dans `config/attributs.json` et `config/implications.json`.
> Les tableaux ci-dessous documentent les valeurs initiales ; la source de
> vérité est le JSON. Aucune constante ne doit apparaître dans le code.

## Principe

Un attribut n'entre **jamais directement** dans une probabilité. Il traverse
trois étages :

```
attribut → composite (par phase de jeu)
         → agrégat d'équipe (par zone et couloir)
         → probabilité de transition
```

Le même attribut sert à plusieurs endroits avec des poids différents. La vitesse
pèse lourd en contre, peu en progression placée, pas du tout sur un tir.

## Les 13 attributs

Échelle 1-100. Toute valeur affichée est un entier.

### Techniques

| Attribut | Utilisé dans |
|---|---|
| `passe` | progression, création d'occasion |
| `technique` | progression, création, tir |
| `finition` | résolution du tir |
| `tacle` | défense, toutes zones |
| `jeu_tete` | centres, coups de pied arrêtés |

### Mentaux

| Attribut | Utilisé dans |
|---|---|
| `vision` | création d'occasion, changement d'aile |
| `placement` | défense, position du gardien |
| `sang_froid` | tir, penalty, fin de match |

### Physiques

| Attribut | Utilisé dans |
|---|---|
| `vitesse` | progression, contres, replis défensifs |
| `endurance` | pente de la courbe de fatigue |

### Gardien

Attributs dédiés : sans eux, le gardien est noté sur des critères qui ne le
concernent pas et sa valorisation par l'IA est absurde.

| Attribut | Utilisé dans |
|---|---|
| `reflexes` | arrêt |
| `sorties` | centres, coups de pied arrêtés |
| `relance` | zone de départ de la possession de son équipe |

## Ce qui est délibérément exclu

Agressivité, leadership, esprit d'équipe, flair, pied faible, marquage distinct
de l'interception, spécialiste corners distinct du spécialiste coups francs.

**Règle d'ajout** : pour ajouter un attribut, il faut pouvoir nommer en une
phrase la transition exacte qu'il modifie et son poids dans le composite. Sinon
il est décoratif — il apparaîtra sur la fiche du joueur sans jamais changer un
résultat.

## États (multiplicateurs, pas des attributs)

| État | Plage | Effet |
|---|---|---|
| `forme` | 0.7 – 1.3 | multiplie tous les composites |
| `fatigue` | 0.0 – 1.0 | multiplie tous les composites, 1.0 = frais |
| `moral` | 0.0 – 1.0 | multiplie faiblement, amplitude ±5 % maximum |

Voir `docs/etats-joueur.md` pour leur dynamique.

## Composites

Chaque composite est une combinaison linéaire d'attributs, normalisée sur 1-100.

### Progression

```python
comp_prog_att = 0.45*passe + 0.30*technique + 0.15*vision + 0.10*vitesse
comp_prog_def = 0.45*placement + 0.35*tacle + 0.20*vitesse
```

### Création d'occasion

```python
comp_occ_att = 0.50*vision + 0.30*technique + 0.20*passe
comp_occ_def = 0.60*placement + 0.40*tacle
```

### Tir (individuel, pas agrégé)

```python
comp_tir = 0.60*finition + 0.25*sang_froid + 0.15*technique
comp_arret = 0.70*reflexes + 0.30*placement
```

### Centre et tête (individuel)

```python
comp_tete = 0.65*jeu_tete + 0.20*placement + 0.15*sang_froid
comp_sortie = 0.60*sorties + 0.40*placement
```

## Collectif ou individuel

Distinction structurante, à respecter strictement :

| Transition | Résolution |
|---|---|
| Progression | agrégat de zone (collectif) |
| Création d'occasion | agrégat de zone (collectif) |
| Tir | **deux joueurs nommés** : tireur contre gardien |
| Tête sur centre | **deux joueurs nommés** : réceptionneur contre gardien |

Si le tir est résolu sur un agrégat, un buteur à 90 de finition disparaît dans la
moyenne de l'équipe. Le tireur est tiré au sort, pondéré par son implication dans
la zone et le couloir concernés.

## Matrice d'implication

Chaque joueur porte deux vecteurs, dérivés de son poste. Ils sont **séparables** :

```python
impl[j][zone][couloir] = impl_vert[j][zone] * impl_lat[j][couloir]
```

Sept nombres par joueur et par phase (4 verticaux + 3 latéraux) au lieu de douze.

### Implication verticale — attaque

Zones : 1 défense, 2 milieu bas, 3 milieu haut, 4 zone de vérité.

| Poste | Z1 | Z2 | Z3 | Z4 |
|---|---|---|---|---|
| GB | 0.10 | 0.05 | 0.00 | 0.00 |
| DC | 0.30 | 0.25 | 0.05 | 0.05 |
| DL / DR | 0.25 | 0.40 | 0.30 | 0.10 |
| MDC | 0.20 | 0.55 | 0.30 | 0.05 |
| MC | 0.10 | 0.45 | 0.50 | 0.15 |
| MOC | 0.05 | 0.25 | 0.60 | 0.40 |
| AIL | 0.05 | 0.20 | 0.55 | 0.55 |
| BU | 0.00 | 0.05 | 0.35 | 0.80 |

### Implication verticale — défense

| Poste | Z1 | Z2 | Z3 | Z4 |
|---|---|---|---|---|
| GB | 0.90 | 0.05 | 0.00 | 0.00 |
| DC | 0.85 | 0.35 | 0.05 | 0.00 |
| DL / DR | 0.70 | 0.45 | 0.15 | 0.00 |
| MDC | 0.45 | 0.70 | 0.25 | 0.00 |
| MC | 0.25 | 0.60 | 0.35 | 0.05 |
| MOC | 0.10 | 0.30 | 0.35 | 0.10 |
| AIL | 0.05 | 0.25 | 0.30 | 0.10 |
| BU | 0.00 | 0.05 | 0.20 | 0.15 |

Les zones sont numérotées **du point de vue de l'équipe qui possède le ballon**
en attaque, et du point de vue de son propre but en défense.

### Implication latérale

Couloirs : gauche, axe, droite.

| Poste | G | A | D |
|---|---|---|---|
| GB | 0.20 | 0.60 | 0.20 |
| DC | 0.25 | 0.50 | 0.25 |
| DL | 0.75 | 0.25 | 0.00 |
| DR | 0.00 | 0.25 | 0.75 |
| MDC / MC | 0.20 | 0.60 | 0.20 |
| MOC | 0.20 | 0.60 | 0.20 |
| AIL G | 0.70 | 0.30 | 0.00 |
| AIL D | 0.00 | 0.30 | 0.70 |
| BU | 0.15 | 0.70 | 0.15 |

## Joueur hors poste

Un joueur aligné à un poste qui n'est pas le sien subit un malus multiplicatif
sur ses composites :

```python
affinite = 1.0 if poste == joueur.poste else joueur.postes_secondaires.get(poste, 0.0)
malus = 0.70 + 0.30 * affinite
```

Un joueur sans affinité conserve 70 % de son niveau. Il utilise la matrice
d'implication du poste **où il est aligné**, pas du sien.

## Profils d'attributs à la génération

Les attributs d'un regen se répartissent autour de son niveau cible selon un
profil de poste, avec du bruit. Deux joueurs de même note globale doivent avoir
des profils différents — c'est ce qui rend les choix de recrutement intéressants.

Décalages par rapport au niveau cible, en points :

| Poste | Attributs renforcés | Attributs affaiblis |
|---|---|---|
| GB | reflexes +15, sorties +12, relance +8 | tous les autres −25 |
| DC | tacle +12, placement +10, jeu_tete +10 | finition −18, vision −8 |
| DL/DR | vitesse +10, endurance +8, passe +5 | finition −15, jeu_tete −8 |
| MDC | tacle +10, placement +10, passe +8 | finition −12 |
| MC | passe +12, vision +8, endurance +8 | jeu_tete −6 |
| MOC | vision +14, technique +12, passe +8 | tacle −15 |
| AIL | vitesse +14, technique +12 | tacle −12, jeu_tete −8 |
| BU | finition +16, sang_froid +10, jeu_tete +6 | tacle −18, placement −10 |

Ajouter ensuite un bruit gaussien d'écart-type 6 sur chaque attribut, puis
borner à [1, 100].
