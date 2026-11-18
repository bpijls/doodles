// Service worker for the doodles portal. build.py fills in VERSION (a hash of every built file) and
// PRECACHE (every file in _site/), so each deploy installs a fresh cache and drops the old one.
//
// Strategy
//   pages + doodles.json (same origin, HTML/JSON): network first, cache fallback -> always fresh online,
//                                                   still works offline
//   other same-origin files (thumbs, icons, assets): cache first, refreshed in the background
//   cross-origin scripts/styles/fonts/images (CDNs a doodle uses): same, kept in a runtime cache so a
//                                                   doodle opened once keeps working offline. Other
//                                                   cross-origin requests (APIs) are never touched.
const VERSION = "/*VERSION*/";
const PRECACHE = /*PRECACHE*/[];
const CACHE = `doodles-${VERSION}`;
const RUNTIME = "doodles-runtime";  // survives deploys: CDN files are versioned by URL anyway
const RUNTIME_MAX = 150;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE.map((p) => new Request(p, { cache: "reload" }))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE && k !== RUNTIME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) return cached;
    if (request.mode === "navigate") {
      const portal = await cache.match("./");
      if (portal) return portal;
    }
    throw err;
  }
}

async function trim(cache) {
  const keys = await cache.keys();
  await Promise.all(keys.slice(0, Math.max(0, keys.length - RUNTIME_MAX)).map((k) => cache.delete(k)));
}

async function staleWhileRevalidate(request, cacheName, event) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const refresh = fetch(request).then((response) => {
    // Opaque (no-cors) responses have status 0 but are fine to replay to the same page.
    if (response.ok || response.type === "opaque") {
      cache.put(request, response.clone());
      if (cacheName === RUNTIME) trim(cache);
    }
    return response;
  });
  if (cached) {
    event.waitUntil(refresh.catch(() => {}));
    return cached;
  }
  return refresh;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.protocol !== "https:" && url.protocol !== "http:") return;

  if (url.origin !== self.location.origin) {
    // Only static assets: a doodle's API calls must never be answered from a cache.
    if (["script", "style", "font", "image"].includes(request.destination)) {
      event.respondWith(staleWhileRevalidate(request, RUNTIME, event));
    }
    return;
  }
  const accept = request.headers.get("accept") || "";
  const fresh = request.mode === "navigate" || accept.includes("text/html")
    || url.pathname.endsWith(".json") || url.pathname.endsWith(".webmanifest");
  event.respondWith(fresh ? networkFirst(request) : staleWhileRevalidate(request, CACHE, event));
});
