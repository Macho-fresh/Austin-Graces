/* Appointment form: min date, live slot loading from Django, confirmation modal, submit state.
   Expects form#appointmentForm with data-slots-url (JSON: {"slots":[{"value":"09:00","label":"9:00 AM"}]}). */
(function () {
  "use strict";
  const form = document.getElementById("appointmentForm");
  if (!form) return;
  const date = form.querySelector("#id_date");
  const dentist = form.querySelector("#id_dentist");
  const grid = document.getElementById("slotGrid");
  const submitBtn = document.getElementById("bookBtn");
  const modalEl = document.getElementById("confirmModal");

  // Today onwards (local date)
  const t = new Date();
  date.min = t.getFullYear() + "-" + String(t.getMonth() + 1).padStart(2, "0") + "-" + String(t.getDate()).padStart(2, "0");

  function hint(msg) { grid.innerHTML = ""; const p = document.createElement("p"); p.className = "ag-help"; p.id = "slotHint"; p.textContent = msg; grid.appendChild(p); }

  async function loadSlots() {
    if (!date.value || !dentist.value) { hint("Choose a dentist and date to see available times."); return; }
    hint("Loading available times...");
    try {
      const url = form.dataset.slotsUrl + "?date=" + encodeURIComponent(date.value) + "&dentist=" + encodeURIComponent(dentist.value);
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" } });
      if (!res.ok) throw new Error(res.status);
      const data = await res.json();
      if (!data.slots || !data.slots.length) { hint("No times are available on this date. Please try another day."); return; }
      grid.innerHTML = "";
      data.slots.forEach((s) => {
        const label = document.createElement("label"); label.className = "ag-slot";
        const input = document.createElement("input"); input.type = "radio"; input.name = "time"; input.value = s.value; input.required = true;
        const span = document.createElement("span"); span.textContent = s.label;
        label.append(input, span); grid.appendChild(label);
      });
    } catch (err) {
      hint("We could not load times. Please try again.");
      window.AG && window.AG.toast("Could not load available times.", "error");
    }
  }
  date.addEventListener("change", loadSlots);
  dentist.addEventListener("change", loadSlots);
  if (date.value && dentist.value && !grid.querySelector("input")) loadSlots();

  // Confirmation modal
  let modal = null;
  form.addEventListener("submit", (e) => {
    if (form.dataset.confirmed === "true") return;
    e.preventDefault();
    if (!window.AGValidate(form)) return;
    const text = (id) => { const el = form.querySelector(id); return el.tagName === "SELECT" ? el.options[el.selectedIndex].text : el.value; };
    const time = form.querySelector('input[name="time"]:checked');
    const rows = [["Name", text("#id_full_name")], ["Service", text("#id_service")], ["Dentist", text("#id_dentist")], ["Date", date.value], ["Time", time ? time.nextElementSibling.textContent : ""]];
    const dl = document.getElementById("confirmSummary"); dl.innerHTML = "";
    rows.forEach(([k, v]) => { const dt = document.createElement("dt"); dt.textContent = k; const dd = document.createElement("dd"); dd.textContent = v; dl.append(dt, dd); });
    modal = modal || new bootstrap.Modal(modalEl);
    modal.show();
  });
  document.getElementById("confirmSubmit").addEventListener("click", function () {
    this.classList.add("is-loading"); submitBtn.classList.add("is-loading");
    form.dataset.confirmed = "true";
    form.submit();
  });
})();
