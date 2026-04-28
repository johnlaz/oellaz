const CACHE  = 'oel-v10.0';
const ASSETS = ['/', '/index.html', '/manifest.json',
                '/icons/icon.svg', '/icons/icon-192.png', '/icons/icon-512.png'];

// Install — pre-cache shell assets
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

// Activate — delete every old cache version
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Fetch strategy
// • index.html   → network-first  (always pick up new deployments)
// • API / localhost → pass-through (never cache)
// • other assets → cache-first
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  const passThrough = [
    'api.groq.com', 'corsproxy.io', 'allorigins.win', 'codetabs.com',
    'cors.sh', 'fonts.googleapis.com', 'fonts.gstatic.com', 'localhost',
    'maps.googleapis.com', 'cdnjs.cloudflare.com'
  ];
  if (passThrough.some(h => url.hostname.includes(h))) return;

  if (url.pathname === '/' || url.pathname === '/index.html') {
    e.respondWith(
      fetch(e.request)
        .then(resp => {
          if (resp && resp.status === 200) {
            caches.open(CACHE).then(c => c.put(e.request, resp.clone()));
          }
          return resp;
        })
        .catch(() => caches.match('/index.html'))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        if (resp && resp.status === 200 && resp.type !== 'opaque') {
          caches.open(CACHE).then(c => c.put(e.request, resp.clone()));
        }
        return resp;
      }).catch(() => caches.match('/index.html'));
    })
  );
});
