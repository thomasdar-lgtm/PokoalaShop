const CACHE_VERSION = '3.97';
const CACHE_NAME = 'pokoalashop-v' + CACHE_VERSION;
/* cache non versionne : la base de cartes est versionnee par son URL (?v=N),
   inutile de re-telecharger 2,7 Mo a chaque montee de version */
const CACHE_DATA = 'pokoalashop-data';
/* cache images non versionne : les visuels de cartes et les symboles d'extension
   ne changent jamais, inutile de les retelecharger a chaque montee de version */
const CACHE_IMG = 'pokoalashop-img2';
/* absences d'images memorisees quelques jours : evite de redemander a chaque
   affichage une image qui n'existe pas, tout en retentant regulierement pour
   recuperer le scan francais TCGdex des qu'il est publie */
const CACHE_MISS = 'pokoalashop-miss';
/* symboles d'extension : cache propre, rempli uniquement par le code d'origine.
   Le cache images contient des symboles stockes en mode CORS (3.88 a 3.91). */
const CACHE_SYM = 'pokoalashop-sym';
const MISS_TTL = 3 * 24 * 3600 * 1000;
/* hebergeurs qui refusent le mode CORS pendant la vie de ce service worker */
const noCors = new Set();
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
      .then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME && k !== CACHE_DATA && k !== CACHE_IMG && k !== CACHE_MISS && k !== CACHE_SYM).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  if (url.hostname.indexOf('googleapis.com') >= 0 || url.hostname.indexOf('accounts.google.com') >= 0 || url.hostname.indexOf('gstatic.com') >= 0) return;

  /* images externes */
  if (IMAGE_HOSTS.some(hh => url.hostname.indexOf(hh) >= 0)) {
    /* symboles d'extension : fonctionnement d'origine (avant 3.88), cache
       d'abord et conserve indefiniment. Le mode CORS de imgFetch les faisait
       scintiller a chaque affichage de l'onglet Stock. */
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
    /* visuels de cartes : voir imgFetch */
    e.respondWith(imgFetch(e.request));
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

/* Une image demandee par <img> sans CORS revient OPAQUE : impossible de
   distinguer une vraie image d'une erreur 404. Mettre ces reponses en cache
   figeait donc definitivement les absences TCGdex. On demande en CORS pour
   connaitre le vrai statut : seules les vraies images sont conservees, les
   absences sont retentees apres MISS_TTL. */
async function imgFetch(req) {
  const url = req.url;
  const c = await caches.open(CACHE_IMG);
  const hit = await c.match(url);
  if (hit) return hit;
  const m = await caches.open(CACHE_MISS);
  const miss = await m.match(url);
  if (miss && Date.now() - Number(miss.headers.get('x-t') || 0) < MISS_TTL) {
    return new Response('', { status: 404 });
  }
  const host = new URL(url).hostname;
  if (!noCors.has(host)) {
    try {
      const r = await fetch(url, { mode: 'cors', credentials: 'omit' });
      if (r.ok) {
        c.put(url, r.clone()).catch(() => null);
        if (miss) m.delete(url).catch(() => null);
      } else if (r.status === 404 || r.status === 403 || r.status === 410) {
        m.put(url, new Response('', { headers: { 'x-t': String(Date.now()) } })).catch(() => null);
      }
      return r;
    } catch (err) {
      /* echec CORS (et non coupure reseau) : cet hebergeur passe en mode opaque */
      if (self.navigator.onLine) noCors.add(host);
      else return new Response('', { status: 504 });
    }
  }
  try {
    const r = await fetch(req);
    if (r.ok || r.type === 'opaque') c.put(url, r.clone()).catch(() => null);
    return r;
  } catch (err) {
    return new Response('', { status: 504 });
  }
}
