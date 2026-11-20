/* Dashboard chart. Reads <script id="chart-data" type="application/json"> from Django's json_script:
   {"week":{"labels":[],"pending":[],"confirmed":[],"completed":[]},"month":{...same keys...}} */
(function () {
  "use strict";
  const el = document.getElementById("chart-data"), canvas = document.getElementById("apptChart");
  if (!el || !canvas || !window.Chart) return;
  const data = JSON.parse(el.textContent);
  const colors = { pending: "#E7B24A", confirmed: "#19A7A1", completed: "#123B5D" };
  const build = (key) => ({
    labels: data[key].labels,
    datasets: ["pending", "confirmed", "completed"].map((s) => ({ label: s[0].toUpperCase() + s.slice(1), data: data[key][s], backgroundColor: colors[s], borderRadius: 6, stack: "a" }))
  });
  const chart = new Chart(canvas, {
    type: "bar", data: build("week"),
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } }, scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } } }
  });
  document.querySelectorAll("[data-range]").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("[data-range]").forEach((x) => { x.setAttribute("aria-pressed", String(x === b)); x.classList.toggle("ag-btn--navy", x === b); x.classList.toggle("ag-btn--outline", x !== b); });
    chart.data = build(b.dataset.range); chart.update();
  }));
})();
