const CACHE_NAME = 'memora-patient-v2';
const STATIC_ASSETS = [
    '/patient',
    '/static/patient.css',
    '/static/icon-192.png',
    '/static/icon-512.png',
    '/static/apple-touch-icon.png',
    '/static/manifest.json',
    '/static/offline.html'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;
    
    // For API calls, do not intercept or just fallback to offline
    if (event.request.url.includes('/api/')) {
        return;
    }

    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request).catch(() => {
                // Return offline page for HTML requests
                if (event.request.headers.get('accept').includes('text/html')) {
                    return caches.match('/static/offline.html');
                }
            });
        })
    );
});
