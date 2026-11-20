/* Austin Graces Dental Clinic - global behaviour (loaded on every page via base.html) */
(function () {
  "use strict";

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  /* ---------- Toasts: window.AG.toast("Saved", "success" | "error" | "warning" | "info") ---------- */
  function toast(message, type = "info", timeout = 5000) {
    const host = $("#agToasts");
    if (!host) return;
    const el = document.createElement("div");
    el.className = "ag-toast ag-toast--" + type;
    const msg = document.createElement("span");
    msg.className = "ag-toast__msg";
    msg.textContent = message;
    const close = document.createElement("button");
    close.type = "button";
    close.className = "ag-toast__close";
    close.setAttribute("aria-label", "Dismiss message");
    close.innerHTML = "&times;";
    const remove = () => el.remove();
    close.addEventListener("click", remove);
    el.append(msg, close);
    host.appendChild(el);
    if (timeout) setTimeout(remove, timeout);
  }
  window.AG = Object.assign(window.AG || {}, { toast, $, $$ });

  // Django messages -> toasts
  $$(".ag-flash li").forEach((li) => toast(li.textContent.trim(), li.dataset.type || "info"));

  /* ---------- Mobile navigation ---------- */
  const burger = $("#agBurger");
  const nav = $("#agNav");
  function setNav(open) {
    if (!burger || !nav) return;
    nav.classList.toggle("is-open", open);
    burger.setAttribute("aria-expanded", String(open));
    burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    document.body.classList.toggle("ag-nav-open", open);
  }
  if (burger && nav) {
    burger.addEventListener("click", () => setNav(burger.getAttribute("aria-expanded") !== "true"));
    nav.addEventListener("click", (e) => { if (e.target.closest("a")) setNav(false); });
    window.matchMedia("(min-width: 992px)").addEventListener("change", (e) => { if (e.matches) setNav(false); });
  }

  /* ---------- Dropdowns: any element with [data-dropdown] ---------- */
  function closeDropdowns(except) {
    $$("[data-dropdown].is-open").forEach((d) => {
      if (d === except) return;
      d.classList.remove("is-open");
      const t = $(".ag-dropdown__toggle", d);
      if (t) t.setAttribute("aria-expanded", "false");
    });
  }
  document.addEventListener("click", (e) => {
    const dd = e.target.closest("[data-dropdown]");
    const toggle = e.target.closest(".ag-dropdown__toggle");
    if (dd && toggle && dd.contains(toggle)) {
      const open = !dd.classList.contains("is-open");
      closeDropdowns(dd);
      dd.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
    } else if (!dd) {
      closeDropdowns();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const openToggle = $("[data-dropdown].is-open .ag-dropdown__toggle");
    closeDropdowns();
    setNav(false);
    if (openToggle) openToggle.focus();
  });

  /* ---------- Header shadow on scroll + back-to-top ---------- */
  const header = $("#agHeader");
  const toTop = $("#agToTop");
  function onScroll() {
    const y = window.scrollY;
    if (header) header.classList.toggle("is-scrolled", y > 8);
    if (toTop) toTop.hidden = y < 600;
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  if (toTop) toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

  /* ---------- Smooth scrolling for same-page anchors (CSS handles motion; this moves focus) ---------- */
  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a || a.getAttribute("href") === "#") return;
    const target = document.getElementById(a.getAttribute("href").slice(1));
    if (!target) return;
    e.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
  });

  /* ---------- Password visibility: <button class="ag-password__toggle" data-toggle-password> next to the input ---------- */
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-toggle-password]");
    if (!btn) return;
    const input = $("input", btn.closest(".ag-password"));
    if (!input) return;
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    const icon = $("i", btn);
    if (icon) icon.className = show ? "bi bi-eye-slash" : "bi bi-eye";
  });

  /* ---------- Image preview for upload fields: <input type="file" data-preview="#idOfImg"> ---------- */
  document.addEventListener("change", (e) => {
    const input = e.target.closest("input[type=file][data-preview]");
    if (!input || !input.files[0]) return;
    const img = $(input.dataset.preview);
    if (!img) return;
    const file = input.files[0];
    if (!file.type.startsWith("image/")) { toast("Please choose an image file.", "error"); input.value = ""; return; }
    const url = URL.createObjectURL(file);
    img.onload = () => URL.revokeObjectURL(url);
    img.src = url;
    img.hidden = false;
  });
})();

/* ---------- Copy link button: <button data-copy-link> ---------- */
document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-copy-link]");
  if (!btn) return;
  try { await navigator.clipboard.writeText(window.location.href); window.AG.toast("Link copied.", "success", 2500); }
  catch (err) { window.AG.toast("Could not copy the link.", "error"); }
});

/* Restore buttons if the browser shows this page again from its back/forward cache */
window.addEventListener("pageshow", (e) => {
  if (!e.persisted) return;
  document.querySelectorAll(".is-loading").forEach((el) => el.classList.remove("is-loading"));
  document.querySelectorAll("form[data-confirmed]").forEach((f) => delete f.dataset.confirmed);
});
