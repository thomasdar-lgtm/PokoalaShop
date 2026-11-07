# Données de test réelles

Exports fournis par Thomas, utilisés pour les tests Playwright (jamais lus par l'app).

| Fichier | Contenu | Source |
|---|---|---|
| `lots_2026-11-07.json` | 603 lots (527 Cindy, 76 Thomas), v4.78 | Compte › Données › Télécharger mes données |
| `stock_AAAA-MM-JJ.json` | à venir : tous les fichiers `pkstk*` de Drive | Compte › Stock › Télécharger le stock (4.79) |

## Tests
- `t_export_stock.py` : export du stock (vrais clics, Drive simulé, contrôle qu'aucune écriture n'a lieu). Lancer `python3 test/t_export_stock.py` (succès) puis `python3 test/t_export_stock.py m2` (lecture en échec ⇒ pas de fichier).
- Pièges : enregistrer la route « tout le reste » AVANT celle de googleapis (la dernière route gagne) ; viewport ≥ 600 px de petit côté (sinon `#rotMsg` bloque les clics) ; l'erreur JS `google is not defined` vient du faux script GIS vide.

## Constats sur l'export des lots du 07/11 (non corrigés)
- 3 lots en vitrine avec une `dtVente`.
- 134 lots dont `nb` ≠ somme du détail `cards`.
- Carte `svp-205` absente des fichiers `cards/`.
