# Configuration

## Règle

**Aucune valeur de règle de jeu n'est écrite dans le code.** Le code contient des
formules ; les nombres sont des données.

```python
# INTERDIT
comp = 0.45 * j.passe + 0.30 * j.technique + 0.15 * j.vision + 0.10 * j.vitesse

# ATTENDU
comp = sum(poids * getattr(j, attr) for attr, poids in cfg.composites.progression_attaque.items())
```

Le second est aussi plus court, et il permet d'ajouter un attribut au composite
sans toucher au code.

### Ce qui va en config

Coefficients, seuils, courbes, matrices, distributions, cibles de calibrage,
définitions de formations, tables de correspondance.

### Ce qui reste dans le code

Structure des formules, machines à états, ordre des phases, invariants de règle
du football (11 joueurs, 5 remplacements en 3 fenêtres — ces derniers peuvent
aller en config s'ils sont susceptibles de varier).

## Catalogue

| Fichier | Contenu |
|---|---|
| `config/monde.json` | date initiale, périmètre simulé, import des effectifs, calendrier, fenêtres de mercato |
| `config/attributs.json` | liste des attributs, composites, profils de poste |
| `config/implications.json` | matrices d'implication verticale et latérale |
| `config/formations.json` | définitions des formations |
| `config/moteur_match.json` | coefficients du moteur, xG, densité, couloirs |
| `config/etats.json` | fatigue, blessures, suspensions, forme, moral |
| `config/ia_gestion.json` | valorisation, budgets, mercato, contrats, garde-fous |
| `config/demographie.json` | progression, déclin, regens, retraite |
| `config/benchmarks.json` | cibles de calibrage et tolérances |

## Chargement

```
core/config/
  modeles/         un fichier par domaine (monde.py, attributs.py, ...),
                    dataclass(frozen=True, slots=True) generes et valides
                    par pydantic.dataclasses.dataclass — schema de
                    validation et modele typé sont la même définition,
                    pas deux couches dupliquées comme envisagé plus haut
  coherence.py     controles qui dépassent un seul champ ou un seul fichier
  fusion.py        fusion profonde pour les dossiers de surcharge, retrait
                    des clés "_note"
  chargeur.py      orchestration : lit, fusionne, valide, assemble un Config
  erreurs.py       ConfigInvalide
```

Chaque module de `modeles/` interdit les clés inconnues (`extra="forbid"`),
ce qui couvre à la fois le rôle de « schéma » et celui de « modèle typé »
sans dupliquer les champs deux fois.

```python
@dataclass(frozen=True, slots=True)
class Config:
    monde: ConfigMonde
    attributs: ConfigAttributs
    implications: ConfigImplications
    formations: ConfigFormations
    moteur: ConfigMoteur
    etats: ConfigEtats
    ia: ConfigIA
    demographie: ConfigDemographie
    benchmarks: ConfigBenchmarks

def charger_config(dossier: Path) -> Config: ...
```

Le chargeur **échoue au démarrage** si un fichier est invalide, incomplet ou
contient une clé inconnue. Pas de valeur par défaut silencieuse : une clé
manquante est une erreur, jamais un zéro implicite.

## Contrôles de cohérence au chargement

Au-delà de la validation de schéma :

- La somme des poids de chaque composite vaut 1.0 (tolérance 1e-6)
- Tout attribut cité dans un composite existe dans `attributs.json`
- Toute formation cite des postes existants et compte 11 joueurs
- Toute part de distribution somme à 1.0
- Les bornes min/max sont ordonnées

Ces contrôles évitent les heures de calibrage passées à chercher un bug qui était
une faute de frappe dans un JSON.

## Surcharge

Le chargeur accepte un dossier de surcharge, fusionné par-dessus la base :

```python
cfg = charger_config(Path("config"), surcharge=Path("benchmarks/variantes/k_prog_haut"))
```

Un fichier de surcharge ne contient que les clés modifiées. Usage :

- Balayage de paramètre dans les benchmarks
- Tests qui ont besoin d'une règle extrême
- Variantes de difficulté ou de réalisme

## Versionnement

`config/monde.json` porte un champ `version_config`. Il est copié dans la
sauvegarde. Charger une partie avec une config de version différente affiche un
avertissement : les résultats ne seront pas reproductibles à l'identique.

## Édition

Les fichiers sont destinés à être modifiés à la main pendant le calibrage.
Conséquences :

- Un commentaire par bloc via une clé `"_note"` ignorée par le chargeur
- Jamais de valeur exprimée sous forme dérivée d'une autre (pas de « 0.45 car
  1 − 0.55 ») : chaque nombre est explicite
- Regrouper par domaine de sens, pas par ordre d'apparition dans le code
