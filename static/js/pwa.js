// Mzansi Link: registers the service worker and powers every
// "Install on this phone" card (templates/partials/install_app.html).
(function () {
  'use strict';

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
    });
  }

  var isStandalone =
    (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) ||
    window.navigator.standalone === true;
  var ua = navigator.userAgent || '';
  var isIOS = /iphone|ipad|ipod/i.test(ua) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1); // iPadOS

  var cards = document.querySelectorAll('[data-install-card]');
  if (!cards.length || isStandalone) return; // already running as an app: nothing to offer

  var deferredPrompt = null;

  function eachCard(fn) { Array.prototype.forEach.call(cards, fn); }
  function showCards() { eachCard(function (c) { c.hidden = false; }); }
  function hideCards() { eachCard(function (c) { c.hidden = true; }); }

  // Android / desktop Chrome and Edge: the browser hands us a real install prompt.
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    showCards();
  });
  window.addEventListener('appinstalled', function () { deferredPrompt = null; hideCards(); });

  // iPhone/iPad Safari and browsers with no install prompt (e.g. Firefox):
  // there's no API, so the button shows the manual steps instead.
  if (isIOS || !('onbeforeinstallprompt' in window)) showCards();

  eachCard(function (card) {
    var btn = card.querySelector('[data-install-btn]');
    var help = card.querySelector('[data-install-help]');
    btn.addEventListener('click', function () {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function () { deferredPrompt = null; hideCards(); });
        return;
      }
      help.textContent = isIOS
        ? 'On iPhone: tap the Share button (the square with an arrow) at the bottom of Safari, then choose "Add to Home Screen".'
        : 'Open your browser menu (the three dots) and choose "Install app" or "Add to Home screen".';
      help.hidden = !help.hidden;
    });
  });
})();
