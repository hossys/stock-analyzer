const CACHE = 'stockeram-v9';
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
  const url = new URL(e.request.url);

  // Never cache API requests — always go to network.
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Network-first for HTML (bypass HTTP/CDN cache via cache:'reload').
  if (url.pathname === '/' || url.pathname.endsWith('/index.html')) {
    e.respondWith(
      fetch(new Request(e.request.url, {cache: 'reload'}))
        .then(r => { caches.open(CACHE).then(c => c.put(e.request, r.clone())); return r; })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // Static assets: cache-first.
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});

// ── PUSH NOTIFICATIONS ─────────────────────────────────────────────────────
// The server sends a JSON payload like:
//   { title, body, url?, ticker?, tag? }
// We display it as a system notification. Tapping it opens the app.
self.addEventListener('push', e => {
  let data = {};
  try { data = e.data ? e.data.json() : {}; } catch { data = { body: e.data?.text() || '' }; }

  const title   = data.title   || 'Stockeram';
  const body    = data.body    || '';
  const tag     = data.tag     || data.ticker || 'stockeram-default';
  const url     = data.url     || '/';
  const options = {
    body,
    tag,
    icon:  '/apple-touch-icon.png',
    badge: '/apple-touch-icon.png',
    data:  { url },
    requireInteraction: false,
  };
  e.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const targetUrl = (e.notification.data && e.notification.data.url) || '/';
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      // Focus an existing window if one is open
      for (const c of clients) {
        if ('focus' in c) {
          c.navigate(targetUrl).catch(()=>{});
          return c.focus();
        }
      }
      // Otherwise open a new one
      if (self.clients.openWindow) return self.clients.openWindow(targetUrl);
    })
  );
});
