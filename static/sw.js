/* MerryMeal service worker.
 *
 * Conservative cache strategy — only the static shell + the dashboard
 * are pre-cached. Everything else falls back to network with a stale-
 * while-revalidate hint via cache.match on read errors, so a flaky
 * connection still shows the last-good page instead of the browser's
 * "no internet" screen.
 *
 * Bumping CACHE_VERSION invalidates the previous shell on activate.
 * Bump it whenever you change the precache list, the manifest, or any
 * file referenced from base.html / app_base.html so installed clients
 * pick up the new shell on their next page view.
 */
const CACHE_VERSION = "v3";
const SHELL_CACHE = `merrymeal-shell-${CACHE_VERSION}`;
const PRECACHE_URLS = [
  "/",
  "/dashboard/",
  "/static/dist/output.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  // Pre-cache the shell, then skip the waiting phase so the new SW
  // takes over without forcing a tab reload.
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) =>
        // ``catch`` per URL — a 404 on one (e.g. /static/dist/output.css
        // missing in a freshly-pulled checkout before Tailwind runs)
        // must NOT abort the entire install.
        Promise.all(
          PRECACHE_URLS.map((url) =>
            cache.add(url).catch(() => null)
          )
        )
      )
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  // Drop old shell caches so version bumps don't leak storage.
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith("merrymeal-shell-") && k !== SHELL_CACHE)
            .map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Only handle GET — POST/PUT/DELETE must always go to the network so
  // we never accidentally cache a CSRF-locked form submission.
  if (request.method !== "GET") return;

  // Don't touch cross-origin requests (Mapbox tiles, Google Fonts,
  // unpkg HTMX/Alpine). Browser cache + CDN handle those.
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Network-first for HTML so members always see fresh data when
  // online; fall back to cached shell when the network errors out.
  if (request.headers.get("accept")?.includes("text/html")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() =>
          caches.match(request).then((r) => r || caches.match("/dashboard/"))
        )
    );
    return;
  }

  // Cache-first for everything else (CSS, icons) so the installed app
  // opens instantly even on a cold network.
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.ok && response.type === "basic") {
          const copy = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
        }
        return response;
      });
    })
  );
});
