/* Dream AI offline shell.
 * Caches the app shell so a previously visited page still opens without network.
 * API calls are never cached.
 */
const CACHE = "dreamai-shell-v1.5.0";
const SHELL = [
  "/",
  "/index.html",
  "/offline.html",
  "/manifest.webmanifest",
  "/assets/css/app.css?v=1.5.0",
  "/assets/js/app.js?v=1.5.0",
  "/assets/vendor/marked.min.js?v=1.2.0",
  "/assets/vendor/purify.min.js?v=1.2.0",
  "/assets/vendor/prism.bundle.js?v=1.2.0",
  "/assets/img/mark.svg",
  "/favicon.ico",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put("/index.html", copy));
          return response;
        })
        .catch(async () => {
          return (await caches.match("/index.html")) || (await caches.match("/offline.html")) || Response.error();
        }),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((hit) => {
      if (hit) return hit;
      return fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => caches.match("/offline.html"));
    }),
  );
});
