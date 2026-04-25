const CACHE = 'stockeram-v7';
const STATIC = ['/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
      .then(() => self.clients.matchAll({type:'window'}).then(clients => {
        clients.forEach(c => c.postMessage({type:'sw-updated', version:CACHE}));
      }))
  );
});

self.addEventListener('fetch', e => {
  const url = e.request.url;
  // Always network-first for HTML so updates reach users immediately.
  // Use cache:'reload' to bypass HTTP cache (Cloudflare/CDN), forcing a true network fetch.
  if (url.endsWith('/') || url.includes('index.html')) {
    e.respondWith(
      fetch(new Request(e.request.url, {cache: 'reload'}))
        .then(r => { caches.open(CACHE).then(c => c.put(e.request, r.clone())); return r; })
        .catch(() => caches.match(e.request))
    );
  } else {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  }
});
