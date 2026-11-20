/* Client-side validation for forms with [data-validate]. Server-side validation remains authoritative.
   Each field wrapper must be .ag-field with a .ag-error child. */
(function () {
  "use strict";
  function check(field) {
    const wrap = field.closest(".ag-field");
    if (!wrap) return true;
    let ok = field.checkValidity();
    if (field.type === "radio") {
      ok = !!field.form.querySelector('input[name="' + field.name + '"]:checked') || !field.required;
    }
    if (field.type === "date" && field.value && field.min) ok = ok && field.value >= field.min;
    wrap.classList.toggle("has-error", !ok);
    field.setAttribute("aria-invalid", String(!ok));
    return ok;
  }
  window.AGValidate = function (form) {
    let firstBad = null;
    form.querySelectorAll("input, select, textarea").forEach((f) => {
      if (f.type === "hidden" || f.name === "csrfmiddlewaretoken") return;
      if (!check(f) && !firstBad) firstBad = f;
    });
    if (firstBad) firstBad.focus();
    return !firstBad;
  };
  document.querySelectorAll("form[data-validate]").forEach((form) => {
    form.addEventListener("blur", (e) => { if (e.target.matches("input, select, textarea")) check(e.target); }, true);
    form.addEventListener("input", (e) => { const w = e.target.closest(".ag-field"); if (w && w.classList.contains("has-error")) check(e.target); });
    form.addEventListener("submit", (e) => {
      if (form.dataset.confirmed === "true" || form.hasAttribute("data-confirm-flow")) return; // appointment.js owns this submit
      if (!window.AGValidate(form)) { e.preventDefault(); return; }
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.classList.add("is-loading");
    });
  });
})();
