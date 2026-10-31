"""
Makes Mzansi Link installable ("Add to Home screen") on phones and
desktops: the web app manifest, the service worker, and an offline page.

The service worker is deliberately tiny. It does NOT cache pages,
photos or API responses — this is a dating app full of private
content, and a cached copy of someone's matches or chats on a shared
phone would be a privacy problem. It only shows a friendly offline page
when the network is down.
"""
import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache

THEME = "#E8386A"
CACHE_NAME = "mzansi-link-offline-v1"


@never_cache
def manifest_view(request):
    data = {
        "id": "/",
        "name": "Mzansi Link",
        "short_name": "Mzansi Link",
        "description": "Meet South African singles. Real people, real connection.",
        "lang": "en-ZA",
        "start_url": "/post-login/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#FFF0F5",
        "theme_color": THEME,
        "icons": [
            {"src": static("img/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("img/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static("img/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")


@never_cache
def service_worker_view(request):
    js = f"""
// Mzansi Link service worker — offline page only (see config/pwa.py).
const CACHE = {json.dumps(CACHE_NAME)};
const OFFLINE_URL = "/offline/";

self.addEventListener("install", (event) => {{
  event.waitUntil(caches.open(CACHE).then((c) => c.add(OFFLINE_URL)));
  self.skipWaiting();
}});

self.addEventListener("activate", (event) => {{
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
}});

self.addEventListener("fetch", (event) => {{
  // Only page loads. Everything else (photos, chat, payments) goes
  // straight to the network, untouched and never stored.
  if (event.request.mode !== "navigate") return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(OFFLINE_URL))
  );
}});
"""
    response = HttpResponse(js, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


def offline_view(request):
    return render(request, "offline.html")
