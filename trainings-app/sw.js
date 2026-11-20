/* Service Worker: macht die App offline-fähig (Cache-first, Aktualisierung im Hintergrund). */
const VERSION = "training-v1";
const DATEIEN = [
  "./", "./index.html", "./manifest.webmanifest", "./css/style.css",
  "./js/logik.js", "./js/inhalt-englisch.js", "./js/inhalt-kommunikation.js", "./js/app.js",
  "./icons/icon-192.png", "./icons/icon-512.png", "./icons/icon-maskable-512.png", "./icons/apple-touch-icon.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(DATEIEN)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then((treffer) => {
      const netz = fetch(e.request).then((antwort) => {
        if (antwort && antwort.ok) {
          const kopie = antwort.clone();
          caches.open(VERSION).then((c) => c.put(e.request, kopie));
        }
        return antwort;
      }).catch(() => treffer);
      return treffer || netz;   // sofort aus dem Cache, im Hintergrund aktualisieren
    })
  );
});
