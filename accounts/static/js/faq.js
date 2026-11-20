/* Accordion for any [data-accordion]; search + topic filter when #faqSearch exists. */
(function () {
  "use strict";
  const items = () => Array.from(document.querySelectorAll("[data-faq-item]"));

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".ag-accordion__btn");
    if (!btn) return;
    const open = btn.getAttribute("aria-expanded") === "true";
    btn.setAttribute("aria-expanded", String(!open));
    const panel = document.getElementById(btn.getAttribute("aria-controls"));
    if (panel) panel.hidden = open;
  });

  const search = document.getElementById("faqSearch");
  if (!search) return;
  const chips = Array.from(document.querySelectorAll(".ag-chip"));
  const count = document.getElementById("faqCount");
  const empty = document.getElementById("faqEmpty");
  let category = "";

  function apply() {
    const q = search.value.trim().toLowerCase();
    let shown = 0;
    items().forEach((item) => {
      const qEl = item.querySelector("[data-faq-question]");
      const text = (qEl.textContent + " " + item.querySelector("[data-faq-answer]").textContent).toLowerCase();
      const ok = (!q || text.includes(q)) && (!category || item.dataset.category === category);
      item.hidden = !ok;
      if (ok) shown++;
    });
    if (empty) empty.hidden = shown !== 0;
    if (count) count.textContent = shown + (shown === 1 ? " question" : " questions") + " shown";
  }
  search.addEventListener("input", apply);
  chips.forEach((chip) => chip.addEventListener("click", () => {
    chips.forEach((c) => c.classList.toggle("is-active", c === chip));
    category = chip.dataset.filter;
    apply();
  }));
  apply();
})();
