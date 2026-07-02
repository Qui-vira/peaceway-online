const CACHE_NAME = "peaceway-online-pwa-v4";

// Only these never change — content-hashed by Next.js build
const IMMUTABLE_PREFIX = "/_next/static/";

// Offline fallback pages to precache
const PRECACHE_URLS = [
  "/offline",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((key) => (key !== CACHE_NAME ? caches.delete(key) : null)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Next.js static chunks are content-hashed — safe to cache forever
  if (url.pathname.startsWith(IMMUTABLE_PREFIX)) {
    event.respondWith(
      caches.match(request).then(
        (cached) => cached || fetch(request).then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(request, copy));
          return res;
        })
      )
    );
    return;
  }

  // Everything else: network-first — users always get latest on good connection
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache a copy for offline fallback
        const copy = response.clone();
        caches.open(CACHE_NAME).then((c) => c.put(request, copy));
        return response;
      })
      .catch(() =>
        caches.match(request).then(
          (cached) => cached || caches.match("/offline") || Response.error()
        )
      )
  );
});
