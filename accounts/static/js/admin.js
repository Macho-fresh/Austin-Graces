/* Clinic admin behaviour. Authorization is enforced by Django views, never by this file.
   Hooks (data attributes):
   [data-post-url]        POST immediately (CSRF added), e.g. approve / complete / publish toggle
   [data-confirm-url]     open #confirmModal first (data-confirm-title, data-confirm-text, data-confirm-label)
   [data-form-modal]      open a form modal: data-action-url, data-title, data-f-<field-name>="value" to prefill, data-image-url
   [data-detail-modal]    fill a read-only modal: data-d-<name>="value" -> [data-fill="<name>"], data-history="#hiddenList"
   input[data-live-search="#tableId"]  filters rows client-side
   [data-add-row="#tpl"] / [data-remove-row]  repeatable rows (opening hours)
   [data-day-toggle]      enables/disables the time inputs of a schedule day */
(function () {
  "use strict";
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const csrf = ($('meta[name="csrf-token"]') || {}).content || "";
  const modalFor = (el) => bootstrap.Modal.getOrCreateInstance(el);

  function post(url, data) {
    const f = document.createElement("form");
    f.method = "post"; f.action = url; f.hidden = true;
    const add = (n, v) => { const i = document.createElement("input"); i.type = "hidden"; i.name = n; i.value = v; f.appendChild(i); };
    add("csrfmiddlewaretoken", csrf);
    Object.entries(data || {}).forEach(([k, v]) => add(k, v));
    document.body.appendChild(f); f.submit();
  }

  /* Mobile sidebar */
  const side = $("#adminSide"), overlay = $("#adminOverlay"), menuBtn = $("#adminMenu");
  function setSide(open) {
    if (!side) return;
    side.classList.toggle("is-open", open); overlay.classList.toggle("is-open", open);
    menuBtn.setAttribute("aria-expanded", String(open)); document.body.style.overflow = open ? "hidden" : "";
  }
  if (menuBtn) {
    menuBtn.addEventListener("click", () => setSide(!side.classList.contains("is-open")));
    overlay.addEventListener("click", () => setSide(false));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") setSide(false); });
  }

  document.addEventListener("click", (e) => {
    const direct = e.target.closest("[data-post-url]");
    if (direct) { direct.classList.add("is-loading"); post(direct.dataset.postUrl); return; }

    const conf = e.target.closest("[data-confirm-url]");
    if (conf) {
      const m = $("#confirmModal");
      $("#confirmTitle").textContent = conf.dataset.confirmTitle || "Are you sure?";
      $("#confirmText").textContent = conf.dataset.confirmText || "This cannot be undone.";
      const go = $("#confirmGo"); go.textContent = conf.dataset.confirmLabel || "Confirm";
      go.dataset.url = conf.dataset.confirmUrl; modalFor(m).show(); return;
    }

    const fm = e.target.closest("[data-form-modal]");
    if (fm) {
      const m = $(fm.dataset.formModal), form = $("form", m);
      form.reset();
      $$("img[data-current-image]", m).forEach((img) => { if (fm.dataset.imageUrl) { img.src = fm.dataset.imageUrl; img.hidden = false; } else { img.removeAttribute("src"); img.hidden = true; } });
      form.action = fm.dataset.actionUrl;
      const title = $("[data-modal-title]", m); if (title && fm.dataset.title) title.textContent = fm.dataset.title;
      fm.getAttributeNames().filter((n) => n.startsWith("data-f-")).forEach((n) => {
        const name = n.slice(7).replace(/-/g, "_");
        const field = form.elements[name]; if (!field) return;
        const v = fm.getAttribute(n);
        if (field.type === "checkbox") field.checked = v === "true";
        else if (field.type !== "file") field.value = v;
      });
      modalFor(m).show(); return;
    }

    const dm = e.target.closest("[data-detail-modal]");
    if (dm) {
      const m = $(dm.dataset.detailModal);
      dm.getAttributeNames().filter((n) => n.startsWith("data-d-")).forEach((n) => {
        const t = $('[data-fill="' + n.slice(7) + '"]', m); if (t) t.textContent = dm.getAttribute(n) || "-";
      });
      const h = $("[data-fill-html]", m);
      if (h) { const src = dm.dataset.history && $(dm.dataset.history); h.innerHTML = src ? src.innerHTML : ""; }
      modalFor(m).show(); return;
    }

    const add = e.target.closest("[data-add-row]");
    if (add) { const tpl = $(add.dataset.addRow); $(add.dataset.target).appendChild(tpl.content.cloneNode(true)); return; }
    const rm = e.target.closest("[data-remove-row]");
    if (rm) { rm.closest("[data-row]").remove(); }
  });

  const go = $("#confirmGo");
  if (go) go.addEventListener("click", () => { go.classList.add("is-loading"); post(go.dataset.url); });

  /* Submit state on all admin forms */
  document.addEventListener("submit", (e) => {
    const b = e.target.querySelector('button[type="submit"]:not([data-no-loading])'); if (b) b.classList.add("is-loading");
  });

  /* Live search */
  $$("input[data-live-search]").forEach((input) => {
    const rows = () => $$(input.dataset.liveSearch + " tbody tr[data-search]");
    input.addEventListener("input", () => { const q = input.value.trim().toLowerCase(); rows().forEach((r) => { r.hidden = q && !r.dataset.search.toLowerCase().includes(q); }); });
  });

  /* Schedule day toggles */
  $$("[data-day-toggle]").forEach((cb) => {
    const sync = () => $$("input:not([data-day-toggle])", cb.closest(".ad-day")).forEach((i) => { i.disabled = !cb.checked; });
    cb.addEventListener("change", sync); sync();
  });

  /* Selects with data-autosubmit submit their form on change */
  $$("select[data-autosubmit]").forEach((s) => s.addEventListener("change", () => s.form.submit()));

  /* Reset image previews when a form modal closes */
  $$(".modal").forEach((m) => m.addEventListener("hidden.bs.modal", () => $$("form", m).forEach((f) => f.reset())));
})();
