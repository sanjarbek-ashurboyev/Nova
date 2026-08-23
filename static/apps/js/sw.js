// Nova service worker.
// Deliberately minimal: it takes control cleanly and clears caches left by any
// earlier version. It does NOT intercept fetches, so nothing can be served
// stale. Add a fetch handler here when offline support is actually wanted.
const CACHE_PREFIX = 'nova-';

self.addEventListener('install', function (event) {
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(keys.map(function (key) {
                if (key.startsWith(CACHE_PREFIX)) {
                    return caches.delete(key);
                }
            }));
        }).then(function () {
            return self.clients.claim();
        })
    );
});
