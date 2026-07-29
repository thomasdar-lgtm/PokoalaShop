const CACHE_VERSION = '2.25';
const CACHE_NAME = 'pokoalashop-v' + CACHE_VERSION;
const ASSETS = ['./', './index.html', './manifest.json', './icons/logo.png', './icons/icon-192.png', './icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  if (url.hostname.indexOf('googleapis.com') >= 0 || url.hostname.indexOf('accounts.google.com') >= 0 || url.hostname.indexOf('gstatic.com') >= 0) return;
  if (url.origin !== self.location.origin) return;

  e.respondWith(
    fetch(e.request)
      .then(r => {
        const copy = r.clone();
        caches.open(CACHE_NAME).then(c => c.put(e.request, copy));
        return r;
      })
      .catch(() => caches.match(e.request).then(m => m || caches.match('./index.html')))
  );
});
