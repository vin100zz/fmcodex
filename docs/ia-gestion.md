# IA de gestion

> Toutes les valeurs numériques de ce document sont dans `config/ia_gestion.json`.
> Les tableaux ci-dessous documentent les valeurs initiales ; la source de
> vérité est le JSON. Aucune constante ne doit apparaître dans le code.

En v1, **les 96 clubs sont pilotés par cette IA**. C'est elle qui produit
l'essentiel de ce que l'utilisateur observe.

Toute l'IA repose sur deux fonctions et une boucle de marché.

## 1. Valeur intrinsèque

Indépendante du club. Sert de référence de prix.

```python
def valeur(joueur) -> int:
    niveau = note_globale(joueur)                    # moyenne pondérée par poste
    pot = estimation_potentiel(joueur)
    base = 1.0e6 * exp(0.115 * (max(niveau, pot * 0.75) - 55))
    return int(base * courbe_age(joueur.age) * rarete_poste(joueur.poste))
```

**La convexité en talent est essentielle.** Un joueur à 90 ne vaut pas 1.2 fois
un joueur à 75, il vaut environ 5 fois plus. Sans cela, les gros clubs achètent
dix bons joueurs au lieu d'une star et le marché n'a plus de sommet.

### Courbe d'âge

| Âge | Multiplicateur |
|---|---|
| 17 – 20 | 1.45 |
| 21 – 23 | 1.35 |
| 24 – 26 | 1.15 |
| 27 – 29 | 1.00 |
| 30 – 31 | 0.70 |
| 32 – 33 | 0.42 |
| 34+ | 0.18 |

Un joueur de 19 ans à 70 vaut plus qu'un joueur de 31 ans à 75. Interpoler
linéairement entre les paliers.

### Décote de fin de contrat

```python
mois_restants = contrat.date_fin - date_courante
if mois_restants < 6:  valeur *= 0.15
elif mois_restants < 12: valeur *= 0.45
elif mois_restants < 18: valeur *= 0.75
```

C'est ce qui alimente naturellement le marché : à un an de la fin, vendre à 45 %
vaut mieux que perdre le joueur libre.

## 2. Utilité marginale

C'est elle, et non la valeur, qui déclenche les décisions.

```python
def utilite(joueur, club) -> float:
    avec = note_meilleur_onze(club.effectif + [joueur])
    sans = note_meilleur_onze(club.effectif)
    return avec - sans
```

Un club avec trois excellents gardiens tire une utilité quasi nulle d'un
quatrième. **Cette seule idée corrige l'accumulation compulsive au même poste**,
qui est le grand classique du genre.

Moduler ensuite par la personnalité du club :

```python
utilite_ajustee = utilite * (1 + 0.35 * personnalite.preference_jeunes * jeunesse(joueur))
                          * (1 + 0.30 * personnalite.appetit_risque * incertitude_potentiel(joueur))
```

## 3. Profil cible et besoins

Chaque club vise un niveau dérivé de sa réputation :

```python
def niveau_cible(club) -> float:
    return 42 + 0.48 * club.reputation
```

Profil cible par poste : nombre de titulaires, de rotations, de doublures, et
niveau attendu pour chacun.

| Rang au poste | Niveau attendu |
|---|---|
| Titulaire | niveau_cible |
| Rotation | niveau_cible − 6 |
| Doublure | niveau_cible − 14 |

La comparaison effectif réel / profil cible produit deux listes classées :

- **Manques** : postes sous-dotés, triés par écart au profil
- **Surplus** : joueurs au-delà de la profondeur nécessaire, trop payés, âgés, ou
  mécontents

Le club vend les surplus pour financer les manques.

## 4. Budgets

Deux budgets séparés, et c'est le second qui fait tout le travail.

```python
budget_transfert = revenus_saison * 0.30 + solde * 0.40 + ventes_realisees
masse_salariale_max = revenus_saison * 0.62 / 52
```

Revenus dérivés de la réputation, du classement de la saison précédente et du
pays. **Le plafond salarial est appliqué strictement** : sans lui, l'IA explose
en cinq saisons. Un club ne peut pas signer si le nouveau salaire fait dépasser
le plafond — il doit vendre d'abord.

## 5. Boucle de mercato

Deux fenêtres : été (6 semaines) et hiver (3 semaines). La fenêtre tourne par
**tours de jour**.

```
Bilan de l'effectif  →  Shortlist de cibles  →  Offre au vendeur
                                                      ↓
Transfert conclu  ←  Choix du joueur  ←  Réponse du vendeur
        (refus ou signature ailleurs → retour à la shortlist)
```

### Règle structurante

**Tous les clubs jouent le même tour avant que quoi que ce soit ne se résolve.**
Traiter les clubs séquentiellement fait que le premier de la liste rafle toutes
les meilleures cibles.

Chaque tour se déroule en trois phases distinctes :

```python
def tour_mercato(monde, rng):
    intentions = [club_evalue(c, monde, rng) for c in monde.clubs.values()]
    offres     = [c.emettre_offres(i, rng) for c, i in zip(clubs, intentions)]
    resoudre(offres, monde, rng)
```

Limiter chaque club à **3 négociations actives**. Sinon les gros clubs
pré-réservent tout le marché et bloquent les autres.

### Réponse du vendeur

```python
def repondre_offre(club, joueur, offre) -> Reponse:
    seuil = valeur(joueur) * (1.35 - 0.25 * surplus(club, joueur))
    seuil *= (1 + 0.4 * club.personnalite.patience_negociation)
    if offre >= seuil:            return ACCEPTE
    if offre >= seuil * 0.75:     return CONTRE_OFFRE(seuil)
    return REFUSE
```

### Choix du joueur

Indispensable, sinon le club le plus riche gagne toujours. C'est ce qui rend le
mercato vivant.

```python
def score_offre(joueur, club, salaire_propose) -> float:
    return (0.38 * ratio_salaire(salaire_propose, joueur)
          + 0.30 * temps_jeu_projete(joueur, club)
          + 0.22 * (club.reputation / 100)
          + 0.10 * ambition_sportive(club))
```

Ajouter un bruit gaussien d'écart-type 0.05. `temps_jeu_projete` compare le
niveau du joueur à l'effectif d'accueil à son poste — un cadre n'accepte pas
d'être doublure, même très bien payé.

### Agents libres

Un joueur en fin de contrat non renouvelé devient libre au 1er juillet. Il n'y a
pas de frais de transfert, seule la négociation salariale compte. Les clubs les
évaluent en priorité en début de fenêtre estivale.

## 6. Contrats et renouvellements

Même moteur, sans club acheteur. Évalué chaque semaine.

### Satisfaction du joueur

```python
def satisfaction(joueur, club) -> float:
    s_salaire = joueur.contrat.salaire_hebdo / salaire_attendu(joueur)
    s_jeu     = minutes_saison(joueur) / minutes_attendues(joueur)
    s_club    = club.reputation / reputation_attendue(joueur)
    return 0.40 * clamp(s_salaire, 0, 1.5) + 0.40 * clamp(s_jeu, 0, 1.5) + 0.20 * clamp(s_club, 0, 1.5)
```

`minutes_attendues` dépend du niveau du joueur relativement à son effectif : un
joueur nettement meilleur que ses concurrents s'attend à jouer.

### Décisions

- Satisfaction < 0.65 ou contrat à moins de 12 mois → ouverture d'une négociation
- Le joueur demande `valeur_salariale(joueur) * (1 + 0.15 * ego)`
- Le club renouvelle si `utilite(joueur, club)` justifie le coût sur la durée
- Sinon : mise sur liste de transfert, ou départ libre à échéance

C'est ce cycle — et non un système d'entraînement — qui produit le renouvellement
naturel des effectifs.

## 7. Garde-fous

C'est ici que les simulations amateurs meurent, généralement vers la saison 10.

| Garde-fou | Mise en œuvre |
|---|---|
| Plafond de masse salariale | strict, bloque la signature |
| Taille d'effectif 18 – 30 | force la vente au-dessus de 30, l'achat sous 18 |
| Minimum 2 gardiens, 3 recommandés | contrainte dure |
| Utilité décroissante par poste | assurée par le calcul marginal |
| Temps de jeu comme besoin du joueur | les stars quittent les bancs |
| Valorisation du potentiel | les vétérans ne restent pas hors de prix |

## 8. Sélection de la composition

Avant chaque match, `AIController.choisir_composition` :

1. Écarter blessés et suspendus
2. Choisir la formation : `club.formation_preferee`, sauf si l'effectif
   disponible ne la remplit pas — prendre alors la mieux remplie
3. Pour chaque poste, classer les disponibles par
   `composite_poste * forme * fatigue * malus_poste`
4. Appliquer la rotation : si un joueur est sous 0.65 de fatigue et qu'un
   remplaçant est à moins de 6 points de niveau, faire tourner
5. Hauteur de bloc : dérivée de l'écart de réputation avec l'adversaire et du
   fait de jouer à domicile

## 9. Validation

Suite `economie` de `docs/benchmarks.md`, 25 saisons sans interface. Cibles dans
`config/benchmarks.json`.

Si le talent se concentre ou si les salaires explosent, le problème est presque
toujours dans les garde-fous, pas dans les heuristiques.
