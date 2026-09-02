/* 오프라인에서도 지난번에 본 식단이 뜨게 하는 최소 서비스워커.
   식단은 주 1회만 바뀌므로, 페이지는 네트워크 우선 + 캐시 폴백이면 충분하다. */
var CACHE = "pvv-menu-v6";
var SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png"
];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll(SHELL);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        return k === CACHE ? null : caches.delete(k);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;

  /* 페이지 자체: 최신 식단이 우선. 오프라인이면 마지막에 받은 것 */
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put("./index.html", copy); });
        return res;
      }).catch(function () {
        return caches.match("./index.html");
      })
    );
    return;
  }

  /* 아이콘·글꼴 등 잘 안 바뀌는 것: 캐시 우선 */
  e.respondWith(
    caches.match(req).then(function (hit) {
      return hit || fetch(req).then(function (res) {
        if (res.ok || res.type === "opaque") {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      });
    })
  );
});
