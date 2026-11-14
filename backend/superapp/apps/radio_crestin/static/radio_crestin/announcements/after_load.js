// Fills the announcement page's slow blocks (push reach, results, breakdown) after the page
// loads, so counting devices and events never holds up the page itself. Each element names a
// JSON URL and the key to show; blocks sharing a URL share one request. With
// data-after-load-html the value is HTML built by the admin (format_html), else plain text.
(function () {
  'use strict';

  function fill(element, value) {
    if (element.hasAttribute('data-after-load-html')) element.innerHTML = value;
    else element.textContent = value;
  }

  function load() {
    var byUrl = {};
    document.querySelectorAll('[data-after-load]').forEach(function (element) {
      var url = element.getAttribute('data-after-load');
      (byUrl[url] = byUrl[url] || []).push(element);
    });
    Object.keys(byUrl).forEach(function (url) {
      fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
        .then(function (response) { return response.ok ? response.json() : Promise.reject(response.status); })
        .then(function (data) {
          byUrl[url].forEach(function (element) { fill(element, data[element.getAttribute('data-after-load-key')] || '—'); });
        })
        .catch(function () { byUrl[url].forEach(function (element) { element.textContent = '—'; }); });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
