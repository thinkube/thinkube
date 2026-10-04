/*
 * Copyright Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

/* Show/hide button for the password field. Runs only on pages that have both. */
document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.getElementById('password-toggle');
  var input = document.getElementById('password');
  if (!toggle || !input) return;

  var showIcon = toggle.querySelector('.eye-icon.show');
  var hideIcon = toggle.querySelector('.eye-icon.hide');

  toggle.addEventListener('click', function () {
    var reveal = input.type === 'password';
    input.type = reveal ? 'text' : 'password';
    showIcon.style.display = reveal ? 'none' : 'block';
    hideIcon.style.display = reveal ? 'block' : 'none';
    toggle.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
    toggle.setAttribute('aria-pressed', reveal ? 'true' : 'false');
  });
});
