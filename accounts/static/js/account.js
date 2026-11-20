/* Patient portal: cancel-appointment modal. Buttons carry data-cancel-url and data-cancel-label. */
(function () {
  "use strict";
  const modalEl = document.getElementById("cancelModal");
  if (!modalEl) return;
  const form = document.getElementById("cancelForm");
  const label = document.getElementById("cancelLabel");
  let modal = null;
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-cancel-url]");
    if (!btn) return;
    form.action = btn.dataset.cancelUrl;
    label.textContent = btn.dataset.cancelLabel || "";
    modal = modal || new bootstrap.Modal(modalEl);
    modal.show();
  });
  form.addEventListener("submit", () => {
    const b = form.querySelector('button[type="submit"]'); if (b) b.classList.add("is-loading");
  });
})();
