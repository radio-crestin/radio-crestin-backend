// Fills "Reach: …" on the announcement page after it loads, so counting the devices
// never holds up the page itself.
(function () {
  'use strict';

  function load() {
    document.querySelectorAll('[data-push-reach]').forEach(function (element) {
      fetch(element.getAttribute('data-push-reach'), { credentials: 'same-origin', headers: { Accept: 'application/json' } })
        .then(function (response) { return response.ok ? response.json() : Promise.reject(response.status); })
        .then(function (reach) { element.textContent = reach.text; })
        .catch(function () { element.textContent = '—'; });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
