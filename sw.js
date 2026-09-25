const CACHE_VERSION = '4.06';
const CACHE_NAME = 'pokoalashop-v' + CACHE_VERSION;
/* cache non versionne : la base de cartes est versionnee par son URL (?v=N),
   inutile de re-telecharger 2,7 Mo a chaque montee de version */
const CACHE_DATA = 'pokoalashop-data';
/* cache images non versionne : les visuels de cartes et les symboles d'extension
   ne changent jamais, inutile de les retelecharger a chaque montee de version */
const CACHE_IMG = 'pokoalashop-img2';
/* symboles d'extension : cache propre, rempli uniquement par le code d'origine.
   Le cache images contient des symboles stockes en mode CORS (3.88 a 3.91). */
const CACHE_SYM = 'pokoalashop-sym';
const IMAGE_HOSTS = ['assets.tcgdex.net', 'images.pokemontcg.io', 'images.scrydex.com', 'archives.bulbagarden.net'];
const ASSETS = ['./', './index.html', './manifest.json', './icons/logo.png', './icons/icon-192.png', './icons/icon-512.png', './icons/icon-maskable-512.png'];

self.addEventListener('install', e => {
  /* addAll echoue en bloc des qu'un seul fichier manque, et l'installation
     entiere est alors rejetee : le nouveau service worker n'est jamais active
     et la mise a jour n'arrive jamais. On met en cache un par un, et on
     s'active quoi qu'il arrive. */
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(c => Promise.all(ASSETS.map(u => c.add(u).catch(() => null))))
      .catch(() => null)
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('message', e => {
  if (e.data === 'skipWaiting') self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME && k !== CACHE_DATA && k !== CACHE_IMG && k !== CACHE_SYM).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  if (url.hostname.indexOf('googleapis.com') >= 0 || url.hostname.indexOf('accounts.google.com') >= 0 || url.hostname.indexOf('gstatic.com') >= 0) return;

  /* images externes */
  if (IMAGE_HOSTS.some(hh => url.hostname.indexOf(hh) >= 0)) {
    /* symboles d'extension : cache dedie, conserve indefiniment */
    if (url.pathname.indexOf('symbol') >= 0) {
      e.respondWith(
        caches.open(CACHE_SYM).then(c =>
          c.match(e.request).then(hit => hit || fetch(e.request).then(r => {
            if (r.ok || r.type === 'opaque') c.put(e.request, r.clone());
            return r;
          }).catch(() => hit))
        )
      );
      return;
    }
    /* visuels de cartes : cache d'abord, une seule requete.
       La version 3.88 demandait d'abord l'image en mode CORS pour connaitre
       son vrai statut : les images partant toutes en parallele, ce premier
       appel echouait pour chacune et doublait le nombre de requetes. */
    e.respondWith(
      caches.open(CACHE_IMG).then(c =>
        c.match(e.request).then(hit => hit || fetch(e.request).then(r => {
          if (r.ok || r.type === 'opaque') c.put(e.request, r.clone());
          return r;
        }).catch(() => hit))
      )
    );
    return;
  }

  if (url.origin !== self.location.origin) return;

  /* donnees de cartes : cache d'abord, la cle inclut le ?v=N */
  if (/\/(pks_sets|pks_names|pks_familles)\.json$/.test(url.pathname) || url.pathname.indexOf('/cards/') >= 0) {
    e.respondWith(
      caches.open(CACHE_DATA).then(c =>
        c.match(e.request).then(hit => hit || fetch(e.request).then(r => {
          if (r.ok) c.put(e.request, r.clone());
          return r;
        }))
      )
    );
    return;
  }

  /* la page et le manifeste sont servis par GitHub Pages avec un max-age :
     sans 'reload', le fetch peut etre satisfait par le cache HTTP du navigateur
     et la mise a jour n'arrive jamais */
  const isShell = e.request.mode === 'navigate' ||
                  /\/(index\.html|manifest\.json)$/.test(url.pathname) ||
                  url.pathname.endsWith('/');
  const req = isShell ? new Request(e.request.url, { cache: 'reload', credentials: 'same-origin' })
                      : e.request;

  e.respondWith(
    fetch(req)
      .then(r => {
        const copy = r.clone();
        caches.open(CACHE_NAME).then(c => c.put(e.request, copy));
        return r;
      })
      .catch(() => caches.match(e.request).then(m => m || caches.match('./index.html')))
  );
});

