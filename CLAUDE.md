# PoKoalaShop — brief de reprise (v4.81, 07/11/2026)

> Fichier chargé automatiquement à chaque session. **À mettre à jour à chaque version** (repères, constantes, en attente), dans le même commit que `index.html`.

## 1. Contexte
- PWA de gestion des lots Pokémon TCG vendus sur Vinted (Thomas + Cindy) + module Stock (inventaire des cartes).
- Hébergée sur GitHub Pages, données synchronisées sur Google Drive (appDataFolder).
- Thomas n'a pas de bagage en code : Claude écrit tout le code **et gère les dépôts GitHub** (push direct).
- 3 appareils : **S25** (téléphone de Thomas), **tablette** (vue grand écran), **Oppo** (dédié à PoKoalaShop, outil de Cindy).
- Exigence n°1 : fiabilité des données. « Pas de pertes, pas de confusion, pas de mélanges, rien. Tout doit être propre. »

## 2. Règles de travail (impératives)
- Brièveté : pas d'explications superflues, seulement des livrables vérifiés.
- Un correctif à la fois, vérifié avant de passer au suivant.
- Toujours incrémenter la version ; `APP_VERSION` (index.html) = `CACHE_VERSION` (sw.js).
- index.html + sw.js livrés/poussés ensemble ; `node --check` sur le JS avant chaque livraison.
- Fichiers de données d'abord, index.html en dernier.
- Nouvelle fonctionnalité : cadrer d'abord (questions → récap → attendre validation).
- Vérifier les collisions (ids, classes CSS, noms de fonctions) avant d'ajouter.
- Les tests suivent le vrai chemin de l'app (Playwright, vrais clics/saisies).
- Mesurer avant de diagnostiquer ; ne jamais corriger un problème local en changeant un mécanisme global.
- Reconnaître honnêtement les échecs.
- Mises à jour : jamais d'installation sans son accord (bannière « Installer »).

## 3. Dépôt et livraison
- Dépôt : `https://github.com/thomasdar-lgtm/PokoalaShop.git`, branche `main` (respecter cette casse).
- Contenu : `index.html` (~350 Ko, tout le code), `sw.js`, `manifest.json`, `icons/`, `pks_sets.json`, `pks_names.json`, `pks_familles.json`, `pks_especes.json`, `cards/<setId>.json` (≈205 fichiers).
- Méthode : cloner, travailler dans une copie, recopier dans le clone, puis commits séparés dans l'ordre :
  1. données (si besoin) ; 2. `sw.js` ; 3. `index.html`.
- Messages de commit en français, préfixés `vX.YZ : …`, terminés par les lignes d'attribution demandées par la session.
- Vérification après push : `git show origin/main:index.html | grep APP_VERSION` et idem `sw.js`.
- Accès réseau de l'environnement de dev (vérifié le 07/11) : GitHub, `api.tcgdex.net`, `assets.tcgdex.net`, `www.pokepedia.fr`, `api.pokemontcg.io`, `images.pokemontcg.io`, `pokeapi.co`. **Non joignable** : `assets.pokemon.com` (source d'images pokemon.fr) ⇒ cette étape de la chaîne d'images ne peut pas être testée ici. WebFetch ne renvoie que des résumés : préférer `curl`.
- Données de test réelles et tests Playwright : dossier `test/` (voir `test/LISEZMOI.md`). Les noms d'acheteurs ne sont pas sensibles (accord de Thomas) : les exports peuvent être poussés.

## 4. Architecture générale
### Constantes clés
`APP_VERSION '4.81'` · `CARDS_VER '16'` · `SETS_VER '19'` · `FAM_VER '11'` · `ESP_VER '2'` · `PREFIX 'pks_'` · `SOLO 'cindy'` · `POLL_MS 45000` · `RELECT_MAX 10 min` · `BAK_KEEP 10`, `BAK_EVERY 6 h` · `TCGDEX 'https://api.tcgdex.net/v2/fr'`.
- Les fichiers de données sont chargés avec `?v=<VER>` : modifier un fichier de données ⇒ incrémenter la constante correspondante.

### Service worker (sw.js)
- `CACHE_NAME = 'pokoalashop-v' + CACHE_VERSION` (coquille), `CACHE_DATA` (données, non versionné), `CACHE_IMG = 'pokoalashop-img2'`, `CACHE_SYM` (symboles d'extension).
- **Pas de `skipWaiting` à l'installation** (depuis 4.71) : skipWaiting uniquement sur message `'skipWaiting'` envoyé par la page.

### Stockage local
- localStorage, préfixe `LS` = `pks_` : `who`, `tk` (jeton), `dev` (id appareil), `devnom` (nom appareil), `jal` (6 derniers démarrages), `autoN`, `mvp` (mouvements en attente), `mvmig`, `mvf`, `oldstk`, `xc`, `lastbak`, `tri`, `nvtri`, `filt`, `cols`, `group`, `invdir`, `sort`, `stkc`, + clés cache/pending des lots.
- IndexedDB `pokoalashop` (v1), store `ph` (photos).
- `stoProt()` demande `navigator.storage.persist` (activé sur le S25) ; `stoPetit()` mesure le localStorage (~0,9 Mo / 5 Mo). L'étape « migrer les copies locales vers IndexedDB » est reportée : à reprendre si on approche 3 Mo.

### Identité
- `pks_who` : thomas / cindy. Fichiers lots : `pks_thomas.json`, `pks_cindy.json` (`SOLO='cindy'` évite le double comptage).
- `DEV = devId()` : identifiant d'appareil pour les fichiers Stock et Journal ; nom lisible via `devNom()` (stocké dans les fichiers stock sous `nom`). Appareils nommés : Tablette, S25, Oppo (`mvdtytc1vf7kr7`). Plusieurs anciens identifiants sans nom : voir `test/LISEZMOI.md`.
- **Reprise d'identité (4.80)** : `idVerifier()` (appelé après la 1re lecture réussie du stock) — si l'appareil n'a aucune trace `pkstk*_<DEV>` sur Drive, aucune saisie en attente et `pks_devok ≠ DEV`, fenêtre « Quel appareil es-tu ? » (`sheetIdChoix`, noms des couches + dernière activité, « Nouvel appareil » pose `devok`). Confirmation si activité < 24 h (`ID_RECENT`). `idReprendre` relit la couche choisie, la pose dans le cache `stkc`, écrit `dev`/`devnom`/`devok`, puis recharge. Pas de bouton manuel (refusé par Thomas).
- **Nom dans Compte (4.81)** : `devZone(edit)` dans `#a_devz`, sous la ligne de connexion. Nom grisé en lecture seule + bouton « Modifier » (`#a_devmod`) ; champ `#f_devnom` + « Annuler » (`#a_devx`) / « Enregistrer » (`#a_devnom`) seulement en modification, ou directement si aucun nom.

## 5. Synchronisation des lots
- `listFiles()` : strict (une erreur Drive ≠ liste vide), paginé (pageSize 1000 + nextPageToken), filtre les noms commençant par `pks_`.
- Écritures en attente `pendLots` + relecture de confirmation `pendConfirm`.
- Interrogation légère : `sigFichiers(fs)` (signature `id@modifiedTime`), `lotsSig`/`lotsSigAt`. Lecture complète si la signature change, s'il y a des écritures en attente, ou au-delà de `RELECT_MAX`.
- Sauvegardes automatiques `bak_` (10 gardées, toutes les 6 h).

## 6. Stock
### Fichiers
- Un fichier par appareil : `pkstk_<DEV>.json` (`STK_MINE`). Fusion des couches de tous les appareils à l'affichage.
- `driveList(prefix)` → `driveListQ` : strict, paginé, avec modifiedTime, filtre par préfixe. Une lecture en échec lève une erreur ⇒ l'état précédent est conservé.
- Ancien fichier `pkstk.json` (`STK_LEGACY`) : recherche stricte ; `legacyVerifie` revérifie chaque session un « non » mémorisé.
- Mode léger : `stkSig`/`stkSigAt`, `stkFetch(leger)` appelé par `stkSync(force)`.
- `stkView()` = fonction centrale d'affichage du module.

### Journal des mouvements (depuis 4.52)
- Fichiers mensuels `pkstkmv_<dev>_<AAAA-MM>.json` ; marqueur de migration `pkstkmv_<dev>_fait.json` ; anciens fichiers `pkstkmv_<dev>.json` migrés vers des mois `legacy`.
- Dédoublonnage par clé `t|c|v|e|d` ; `mvFusionMois` relit → écrit → vérifie.
- Fonctions : `mvSave`, `mvMigrer`, `mvIndex`, `mvChargerMois`. L'état `mvJ` est libéré en quittant l'écran.
- UI : panneau de dates (mois → jours), rien n'est chargé avant le choix, recherche de carte sur toutes les dates, nom de l'appareil sur chaque ligne, tri via `mvMs`/`mvOrdre` (ne pas soustraire des chaînes ISO).

### Variantes et états
- Variantes `VAR_ORDRE` (n = Normale, holo, reverse, …) ; variantes rares `VAR_RARE {p: Pokéball, m: Master Ball, c: …}` avec teintes discrètes (brique, violet, or) : classes `.stkV.vp/.vm/.vc`, `.shVrN.vp…`.
- États `ETS` (NM, …).
- Holo/Normale : en activant Holo (via `data-stkvt`), Normale se décoche tout de suite s'il n'y a aucun exemplaire Normal. Décochage différé `autoN` (`autoNNote`, `autoNAppliquer`) appliqué au changement d'écran, d'onglet ou au passage en arrière-plan. Un choix manuel de Normale retire la carte d'`autoN`. Analyse en lecture seule : `sheetHoloDiag` (histogramme par semaine).

### Recherche Stock
- Index multi-extensions `pks_names.json`. Un code d'extension (ex. « DLR ») ne fait que restreindre une recherche par nom.
- Espèces `pks_especes.json` v2 : `e` = nom FR/EN normalisé → espèce FR normalisée, `o` = ordre d'évolution PokeAPI. Fonctions `espLoad`, `especeDe(nom)` (mot entier, préfixe « Primo »), `especesDe`, `especeBase`, `carteDuMembre(c, mn)`. Corrigé : « mélofée » ne remonte plus « méloco ».
- Pastilles famille : `famPastilles`, première pastille **Tous** (`STK_TOUS = '*'`), `stkFamNoms`, `famNomOk`. Tri `parNumero` : extension principale avant sous-extensions, puis `rangEvo` (Nidoran ♂ = 33,5), puis numéro. Limite 1500 résultats en « Tous », 400 sinon.
- Cellule stickers dans les résultats : `stkStickBase`, `stkStickCell`, `stkStickMaj`, `data-stkstq` (affiche aussi 0). `STICK_SEPARE`, `STICK_FUSION` (Nidoran).
- Champs de recherche (`champRecherche` : `#q`, `#stkq`, `.fxW`) : Entrée ferme le clavier, une nouvelle saisie remonte en haut (`hautResultats`), zone de toucher agrandie des boutons effacer (`::after` sur `.srch .clr`, `.fxW .fx`, `.stkSrch .sx`).

### « Jamais fait »
- Exclut les cartes non-Pokémon (dresseurs, énergies) ; les objets restent avec le Pokémon ; les noms à suffixe sont rattachés à la famille (`faitsFam`).

## 7. Autres fonctions
- **Acheteurs** : `achListe`, suggestions `achSugg(inp, apres)` — **préfixe uniquement**, 6 max, dans les fiches Vendre / Vente multiple / Modifier. Plus de statut « expédié » : un lot est marqué vendu et part dans l'historique.
- **Mises à jour (4.71)** : `prete()` → `checkUpdate` quand `reg.waiting` ; bannière « Version X prête · Installer » ; `majInstaller()` envoie skipWaiting, pose `majDemandee`, recharge (sans purge de cache). `controllerchange` ne recharge que si `majDemandee`. Bouton `majBox`/`majBouton` (Vérifier / Installer) en haut de Compte. `hardReload` = « Réinstallation complète » (dans Dépannage).
- **Compte (4.69/4.70)** : ligne d'état · Nom de l'appareil · Mise à jour · Cet appareil (stockage) · Données · Stock (Vérifier le stock, **Télécharger le stock** `stkExport` : copie brute de tous les fichiers `pkstk*` + saisies en attente, lecture seule, tout ou rien) · Dépannage replié (`#a_dep`, `#a_depC`) : analyse holo, Désélectionner Normale, Derniers démarrages, Diagnostic images, Réinstallation, infos fichiers. Plus de liens vers les autres apps.
- **Démarrage / hors ligne** : journal de démarrage `jalDebut`/`jal`/`sheetJal` ; `gisCharger()` avec onerror et repli `demarrer()` après 3 s ; `sessionConnue`, `jetonStocke`, drapeau `demarre` ; `reauth()` sort sans consommer le délai anti-rafale si `!tokenClient`. La vitrine se met à jour en < 5 s.
- **Portrait sur téléphone (4.74)** : `estTelephone()` (petit côté < 600), `verrouPortrait()` (refusé par le S25) et message de secours `#rotMsg` « Tourne ton téléphone ». En pratique Thomas utilise une **routine Samsung** (elle reste active tant que l'app n'est pas complètement fermée ; accepté).
- **Images** : chaîne TCGdex FR → pokemon.fr (FR) → pokemontcg.io (EN) ; la visionneuse reprend la chaîne depuis la source affichée.
- **Vérification des nouvelles cartes (4.77)** : `xGet(u)` en `cache: 'no-store'` ; `majManuel` récupère le résultat même si une vérification auto tourne ; message « N extensions vérifiées ».

## 8. Ajouter une extension (procédure Règne Delta, 4.78)
1. `cards/<id>.json` : objets `{i:'me6-N', n: nom FR (« ex » → « -ex »), e: nom EN ou '', u:'N', s:'me6', r: rareté en anglais, g: 'https://assets.tcgdex.net/fr/me/me06/%03d', v: 3 ou 4, d:1}`.
2. `pks_sets.json` : insérer en tête `{id, name, serie, date, code, syms:[…], n, t:'me06'}` et ajouter n à `cardCount`.
3. `pks_names.json` : ajouter les clés FR/EN normalisées.
4. Incrémenter `SETS_VER` et `CARDS_VER`, version app, puis pousser (données → sw.js → index.html).
- Attention aux collisions de normalisation (Nidoran♀ / Nidoran♂ : corrigées à la main).

## 9. En attente
- Règne Delta (me6, DLR, 141 cartes) intégrée **sans images** : TCGdex ne l'avait pas encore publiée au 07/11 (absente de `/v2/fr/series/me`, dernière = me05). Dès publication : vérifier les images (chemin me06) et ajouter les noms EN manquants de 16 dresseurs/énergies.
- Côté Thomas/Cindy : donner le nom du Pokémon dont Cindy a saisi 2 Pokéball non pris en compte (à chercher dans le journal) ; vérifier que le total « Exemplaires » est identique sur les 3 appareils ; relancer l'analyse holo dans 1–2 semaines (la ligne « Normale encore cochée sans exemplaire » doit rester à 0).
- Ixon de Galar : le journal montre +2 Pokéball saisis sur la tablette le 16/09 à 18:32 (probables erreurs de clic), puis −2 sur le S25.
- APK écarté : on reste en PWA.
- **Changements d'identifiant d'appareil (01/11, 02/11, 06/11)** : cause = effacement des données de Chrome sur le S25 (pour le dev de Koalarcade). Toutes les PWA `thomasdar-lgtm.github.io` partagent le même stockage local : effacer les données du site efface aussi PoKoalaShop (identifiant, nom, saisies non envoyées). Consigne donnée : tester les autres apps en navigation privée. S25 actuel = `mw4pmh3rylp1ug` : en 4.80 il doit recevoir la question et reprendre « S25 » (`mvz6xb9bmb5lvt`).

## 10. Repères de versions récentes
4.52 journal mensuel · 4.60 fiabilisation des listes Stock · 4.69–4.70 réorganisation de Compte · 4.71 mises à jour sur accord · 4.74 portrait · 4.77 vérification des nouvelles cartes · 4.78 Règne Delta · 4.79 export du stock · 4.80 reprise d'identité · **4.81 nom de l'appareil verrouillé (actuelle)**.
