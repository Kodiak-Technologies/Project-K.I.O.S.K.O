// Service worker de la app instalable (PWA).
// - La página (index.html) se pide primero a la red: cada publicación nueva llega
//   sola. Sin conexión se usa la última copia (el POS offline sigue funcionando).
// - Los archivos con hash de /assets y los íconos se sirven desde la caché: nunca
//   cambian (un cambio genera otro nombre de archivo).
// - No toca las llamadas al backend: van a otro dominio (Cloud Run).
// vite.config.ts reemplaza __VERSION__ en cada build: así el navegador detecta la
// versión nueva y se borra la caché anterior.
const VERSION = "__VERSION__";
const CACHE = `tienda-${VERSION}`;

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.addAll(["/", "/manifest.webmanifest", "/icons/icon-192.png"]))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((claves) =>
        Promise.all(claves.filter((k) => k.startsWith("tienda-") && k !== CACHE).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Navegación: red primero; sin conexión, la última copia de la portada.
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copia = res.clone();
            caches.open(CACHE).then((c) => c.put("/", copia));
          }
          return res;
        })
        .catch(() => caches.match("/"))
    );
    return;
  }

  // Archivos inmutables (con hash) e íconos: caché primero.
  if (url.pathname.startsWith("/assets/") || url.pathname.startsWith("/icons/")) {
    e.respondWith(
      caches.match(req).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            if (res.ok) {
              const copia = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copia));
            }
            return res;
          })
      )
    );
  }
});
