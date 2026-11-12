// Dismissible cards already show a built-in "Hide" button, so the second
// button's "Close" option is offered only when "Can be closed" is off.
(function () {
  'use strict';

  function setup() {
    var dismissible = document.getElementById('id_dismissible');
    var kind = document.getElementById('id_secondary_kind');
    if (!dismissible || !kind) return;
    var closeOption = kind.querySelector('option[value="close"]');
    if (!closeOption) return;

    function sync() {
      closeOption.hidden = dismissible.checked;
      closeOption.disabled = dismissible.checked;
      if (dismissible.checked && kind.value === 'close') {
        kind.value = 'none';
        kind.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    dismissible.addEventListener('change', sync);
    sync();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
})();
