# Interface

## Contrainte v1

L'utilisateur est **observateur**. Aucun écran n'a de bouton d'action sur un
club : pas de composition à valider, pas d'offre à émettre. L'interface sert à
consulter et à faire avancer le temps.

Cela n'autorise pas à mélanger lecture et décision dans le code : les endpoints
sont déjà organisés pour qu'ajouter le contrôle utilisateur consiste à ajouter
des routes d'action, pas à réécrire les routes de lecture.

## Principes

**Penser en vues, pas en entités.** Un endpoint renvoie exactement ce qu'un écran
affiche, plutôt qu'un REST générique qui obligerait le front à faire quarante
requêtes pour reconstituer une page.

**Filtrage, tri et pagination côté serveur.** Ne jamais renvoyer 32 000 joueurs
au navigateur. Toute liste est paginée, y compris la recherche de joueurs qui
porte sur l'ensemble des clubs, actifs et dormants.

**Code couleur constant.** Gardien, défense, milieu, attaque gardent la même
teinte partout, de la liste d'effectif au terrain. C'est ce qui permet de lire
une composition en une seconde.

**Trois chiffres par ligne de joueur.** Âge, salaire, fin de contrat. Une
échéance à moins de 12 mois passe en rouge. C'est la liste de tâches implicite,
et elle remplace tous les écrans de gestion supprimés.

## Contrôle du temps

Barre persistante en tête d'application :

- Date courante, saison, prochaine échéance
- Boutons : avancer d'un jour, avancer à la prochaine journée de championnat,
  avancer à la fin de la fenêtre de mercato
- Journal des événements du jour : résultats, transferts, blessures

## Écrans

### Club

| Onglet | Contenu |
|---|---|
| Effectif | liste triable : poste, nom, âge, note, salaire, fin de contrat, état (blessé, suspendu, fatigue) |
| Calendrier | matches passés et à venir, résultat, adversaire, domicile/extérieur |
| Budget | budget de transfert, masse salariale et plafond, solde, revenus |
| Transferts | arrivées et départs de la saison, avec montants |
| Historique | classements passés, palmarès, transferts marquants |

En-tête : nom, pays, compétition, réputation, classement actuel, forme sur les
5 derniers matches.

### Compétition

| Onglet | Contenu |
|---|---|
| Classement | position, J, V, N, D, BP, BC, différence, points, forme |
| Calendrier | matches par journée, avec résultats |
| Statistiques | meilleurs buteurs, passeurs, meilleures notes moyennes, clean sheets, cartons |
| Historique | champions par saison, meilleur buteur par saison |

### Joueur

| Section | Contenu |
|---|---|
| Identité | nom, nationalité, âge, date de naissance, poste, postes secondaires |
| Caractéristiques | les 13 attributs, groupés par famille, avec barres |
| Potentiel | **fourchette d'estimation**, jamais la valeur réelle |
| État | blessure en cours et durée, fatigue, suspension, forme, moral |
| Contrat | club, salaire hebdomadaire, date de fin, valeur de marché estimée |
| Saison en cours | matches, minutes, buts, passes, note moyenne, cartons |
| Historique | une ligne par saison ; transferts avec montants ; courbe de la note globale par saison |

### Match

Écran de compte rendu, consultable après simulation :

- Score, compétition, journée, stade
- xG, tirs, possession, corners, cartons
- Fil chronologique des événements avec joueurs nommés
- Compositions des deux équipes avec notes individuelles

En v1 le match est simulé instantanément. Prévoir dès la conception que le
`ResultatMatch` contient tous les événements horodatés : le mode « match en
direct » se construira en rejouant ce fil, sans toucher au moteur.

### Recherche de joueurs

Vue transversale sur les 32 000 joueurs. Filtres serveur : poste, âge, niveau,
nationalité, club, statut du club (actif ou dormant), fourchette de salaire,
statut contractuel. Tri sur toute colonne, pagination obligatoire.

Un club dormant est consultable — nom, effectif, fiches joueurs — mais n'a ni
classement, ni calendrier, ni statistiques de saison. L'interface doit le
signaler explicitement plutôt que d'afficher des sections vides.

## Endpoints

```
GET  /api/monde/etat                     date, saison, prochaines échéances
POST /api/monde/avancer                  {jusqu_a: "jour" | "journee" | "fin_mercato"}
GET  /api/monde/journal?date=             événements du jour

GET  /api/clubs?competition=&statut=actif|dormant&recherche=&page=&tri=
GET  /api/clubs/{id}                      en-tête + résumé
GET  /api/clubs/{id}/effectif
GET  /api/clubs/{id}/calendrier
GET  /api/clubs/{id}/finances
GET  /api/clubs/{id}/transferts?saison=
GET  /api/clubs/{id}/historique

GET  /api/competitions
GET  /api/competitions/{id}/classement
GET  /api/competitions/{id}/calendrier?journee=
GET  /api/competitions/{id}/statistiques?type=buteurs|passeurs|notes
GET  /api/competitions/{id}/historique

GET  /api/joueurs?poste=&age_min=&age_max=&niveau_min=&nation=&club=&statut_club=&page=&tri=
GET  /api/joueurs/{id}
GET  /api/joueurs/{id}/historique

GET  /api/matches/{id}                    compte rendu complet

POST /api/partie/sauvegarder              {slot: str}
POST /api/partie/charger                  {slot: str}
GET  /api/partie/slots
```

## Front

HTML, CSS et JS vanilla. L'essentiel des écrans est constitué de tableaux
triables — un framework n'apporterait rien ici.

- Une page par écran, navigation par ancres ou petit routeur maison
- Aucun état applicatif dupliqué côté client : le serveur est la source de vérité
- Rafraîchir après chaque avancée de temps

Compter environ la moitié du temps total du projet sur l'interface si l'on veut
quelque chose d'agréable à utiliser. Ne pas commencer avant que le harnais de
calibrage donne des résultats corrects.
