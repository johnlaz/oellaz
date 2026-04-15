const CACHE = 'oel-v9.1';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icons/icon.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

// Install — cache all core assets
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

// Activate — clean up old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch — network-first for HTML (always get latest), cache-first for other assets
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Never intercept: APIs, proxies, fonts, localhost
  const passThrough = [
    'api.groq.com', 'corsproxy.io', 'allorigins.win', 'cors.sh',
    'cors-anywhere.herokuapp.com', 'fonts.googleapis.com',
    'fonts.gstatic.com', 'localhost', 'maps.googleapis.com',
    'cdnjs.cloudflare.com'
  ];
  if (passThrough.some(h => url.hostname.includes(h))) return;

  // Network-first for index.html so updates always reach the user
  if (url.pathname === '/' || url.pathname === '/index.html') {
    e.respondWith(
      fetch(e.request).then(resp => {
        if (resp && resp.status === 200) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Cache-first for other same-origin assets (icons, manifest)
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        if (resp && resp.status === 200 && resp.type !== 'opaque') {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => caches.match('/index.html'));
    })
  );
});
