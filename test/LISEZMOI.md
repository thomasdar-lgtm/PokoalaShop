# Données de test réelles

Exports fournis par Thomas, utilisés pour les tests Playwright (jamais lus par l'app).

| Fichier | Contenu | Source |
|---|---|---|
| `lots_2026-11-07.json` | 603 lots (527 Cindy, 76 Thomas), v4.78 | Compte › Données › Télécharger mes données |
| `stock_2026-11-07.json` | 31 fichiers `pkstk*` de Drive (9 couches de stock, journal complet), exporté depuis l'appareil `mw4pmh3rylp1ug` (sans nom, sans fichier de stock) | Compte › Stock › Télécharger le stock (4.79) |

## Tests
- `t_export_stock.py` : export du stock (vrais clics, Drive simulé, contrôle qu'aucune écriture n'a lieu). Lancer `python3 test/t_export_stock.py` (succès) puis `python3 test/t_export_stock.py m2` (lecture en échec ⇒ pas de fichier).
- `t_identite.py <scénario>` (4.80) : `s25`, `vide`, `oppo` (confirmation < 24 h), `normal` (pas de question), `nouveau`, `saisie` (reprise puis saisie avec la couche illisible sur Drive : la couche écrite doit valoir Drive + la saisie).
- Pièges : enregistrer la route « tout le reste » AVANT celle de googleapis (la dernière route gagne) ; viewport ≥ 600 px de petit côté (sinon `#rotMsg` bloque les clics) ; l'erreur JS `google is not defined` vient du faux script GIS vide.

## Constats sur l'export des lots du 07/11 (non corrigés)
- 3 lots en vitrine avec une `dtVente`.
- 134 lots dont `nb` ≠ somme du détail `cards`.
- Carte `svp-205` absente des fichiers `cards/`.

## Constats sur l'export du stock du 07/11 (non corrigés)
- 9 couches de stock (`pkstk_<dev>`) + l'ancien `pkstk.json` ; noms : Tablette `mtvdndft2yzrn6`, S25 `mtvdozdjnkqs97` (ancien) et `mvz6xb9bmb5lvt` (depuis le 03/11), Oppo `mvdtytc1vf7kr7` ; sans nom : `mtvf7stmqr0ucf`, `mutq5nh2thcvoy`, `mv3ts0p6nvymjb`, `mvxtmpzk2ex8ad`.
- Deux fichiers portent le même nom `pkstkmv_mvz6xb9bmb5lvt_2026-11.json` (S25, créés le 03/11 à 13:39) : le petit (1 mouvement) est inclus dans le grand (28) ⇒ aucune perte, mais un doublon de fichier qui ne devrait pas exister.
- Anciens journaux non migrés (pas de `_fait`) : `mtvdozdjnkqs97`, `mtvf7stmqr0ucf`, `mutq5nh2thcvoy` (appareils qui n'ont plus tourné depuis 4.52).
