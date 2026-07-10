function formatMoney(value) {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0
  }).format(value || 0);
}

function parseChartData(element) {
  if (!element) return [];
  try {
    return JSON.parse(element.dataset.chart || "[]");
  } catch (_error) {
    return [];
  }
}

function hasChartValues(data, keys) {
  return data.some((item) => keys.some((key) => Number(item[key] || 0) > 0));
}

function setChartEmpty(canvas, empty) {
  const box = canvas && canvas.closest(".chart-box");
  if (box) box.classList.toggle("is-empty", empty);
}

function buildCharts() {
  if (!window.Chart) return;
  Chart.defaults.color = "#9B99A3";
  Chart.defaults.borderColor = "rgba(255,255,255,.08)";

  const dailyElement = document.getElementById("dailyChart");
  const dailyData = parseChartData(dailyElement);
  if (dailyElement) {
    if (!hasChartValues(dailyData, ["sales", "expenses"])) {
      setChartEmpty(dailyElement, true);
    } else {
      new Chart(dailyElement, {
        type: "bar",
        data: {
          labels: dailyData.map((item) => item.label),
          datasets: [
            { label: "Ventas", data: dailyData.map((item) => item.sales), backgroundColor: "rgba(69,217,151,.78)" },
            { label: "Gastos operacionales", data: dailyData.map((item) => item.expenses), backgroundColor: "rgba(255,98,104,.74)" }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${formatMoney(ctx.raw)}` } } },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { callback: (value) => formatMoney(value) }
            }
          }
        }
      });
    }
  }

  const categoryElement = document.getElementById("categoryChart");
  const categoryData = parseChartData(categoryElement);
  if (categoryElement) {
    if (!categoryData.some((item) => Number(item.amount || 0) > 0)) {
      setChartEmpty(categoryElement, true);
    } else {
      new Chart(categoryElement, {
        type: "doughnut",
        data: {
          labels: categoryData.map((item) => item.category),
          datasets: [{
            data: categoryData.map((item) => item.amount),
            backgroundColor: ["#FF6268", "#F3B94F", "#68CFF4", "#45D997", "#8B78FF", "#C6C1D7", "#D986A1"]
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${formatMoney(ctx.raw)}` } } }
        }
      });
    }
  }
}

function bindConfirmations() {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm") || "¿Confirmar esta acción?";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
}

function digitsOnly(value) {
  return value.replace(/\D/g, "");
}

function formatDateInput(value) {
  const digits = digitsOnly(value).slice(0, 8);
  const parts = [];
  if (digits.slice(0, 2)) parts.push(digits.slice(0, 2));
  if (digits.slice(2, 4)) parts.push(digits.slice(2, 4));
  if (digits.slice(4, 8)) parts.push(digits.slice(4, 8));
  return parts.join("-");
}

function formatTimeInput(value) {
  const digits = digitsOnly(value).slice(0, 4);
  if (digits.length <= 2) return digits;
  return `${digits.slice(0, 2)}:${digits.slice(2, 4)}`;
}

function bindDateTimeMasks() {
  document.querySelectorAll('input[placeholder="DD-MM-YYYY"]').forEach((input) => {
    input.addEventListener("input", () => {
      input.value = formatDateInput(input.value);
      input.setCustomValidity("");
    });
    input.addEventListener("blur", () => {
      const valid = /^\d{2}-\d{2}-\d{4}$/.test(input.value);
      input.setCustomValidity(valid ? "" : "Usa DD-MM-YYYY con año de cuatro dígitos.");
    });
  });

  document.querySelectorAll('input[placeholder="HH:mm"]').forEach((input) => {
    input.addEventListener("input", () => {
      input.value = formatTimeInput(input.value);
      input.setCustomValidity("");
    });
    input.addEventListener("blur", () => {
      const valid = /^([01]\d|2[0-3]):[0-5]\d$/.test(input.value);
      input.setCustomValidity(valid ? "" : "Usa HH:mm en formato 24 horas.");
    });
  });
}

function bindDeleteDialog() {
  const dialog = document.getElementById("deleteDialog");
  if (!dialog || typeof dialog.showModal !== "function") return;
  let pendingForm = null;

  document.querySelectorAll("form[data-delete-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.dataset.confirmed === "true") return;
      event.preventDefault();
      pendingForm = form;
      dialog.querySelector("[data-delete-kind]").textContent = form.dataset.deleteKind || "-";
      dialog.querySelector("[data-delete-description]").textContent = form.dataset.deleteDescription || "-";
      dialog.querySelector("[data-delete-date]").textContent = form.dataset.deleteDate || "-";
      dialog.querySelector("[data-delete-amount]").textContent = form.dataset.deleteAmount || "-";
      dialog.showModal();
    });
  });

  dialog.addEventListener("close", () => {
    if (dialog.returnValue === "confirm" && pendingForm) {
      pendingForm.dataset.confirmed = "true";
      pendingForm.submit();
    }
    pendingForm = null;
  });
}

function bindActionMenus() {
  document.addEventListener("click", (event) => {
    document.querySelectorAll(".action-menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindConfirmations();
  bindDateTimeMasks();
  bindDeleteDialog();
  bindActionMenus();
  buildCharts();
});
