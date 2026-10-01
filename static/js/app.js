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
  Chart.defaults.color = "#817E89";
  Chart.defaults.borderColor = "rgba(255,255,255,.08)";
  Chart.defaults.font.family = 'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif';

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
            { label: "Ventas", data: dailyData.map((item) => item.sales), backgroundColor: "rgba(66,216,148,.72)", borderRadius: 4, maxBarThickness: 24 },
            { label: "Gastos operacionales", data: dailyData.map((item) => item.expenses), backgroundColor: "rgba(255,98,104,.68)", borderRadius: 4, maxBarThickness: 24 }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { intersect: false, mode: "index" },
          plugins: {
            legend: { position: "bottom", align: "start", labels: { usePointStyle: true, boxWidth: 8, boxHeight: 8, padding: 18 } },
            tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${formatMoney(ctx.raw)}` } }
          },
          scales: {
            x: { grid: { display: false }, ticks: { autoSkip: true, maxTicksLimit: 10, maxRotation: 0 } },
            y: {
              beginAtZero: true,
              ticks: { maxTicksLimit: 6, callback: (value) => formatMoney(value) }
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
            backgroundColor: ["#FF6268", "#F0B84A", "#66CFF2", "#42D894", "#8D7CFF", "#B4B1BC", "#D986A1"],
            borderColor: "#15161C",
            borderWidth: 3,
            hoverOffset: 3
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "66%",
          plugins: {
            legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8, boxHeight: 8, padding: 14 } },
            tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${formatMoney(ctx.raw)}` } }
          }
        }
      });
    }
  }
}

function bindMobileNavigation() {
  const openButton = document.querySelector("[data-nav-open]");
  const closeButtons = document.querySelectorAll("[data-nav-close]");
  const navigation = document.getElementById("appNavigation");
  if (!openButton || !navigation) return;

  const setOpen = (open) => {
    document.body.classList.toggle("nav-open", open);
    openButton.setAttribute("aria-expanded", String(open));
    if (open) navigation.querySelector("a")?.focus();
  };

  openButton.addEventListener("click", () => setOpen(true));
  closeButtons.forEach((button) => button.addEventListener("click", () => setOpen(false)));
  navigation.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => setOpen(false)));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.body.classList.contains("nav-open")) {
      setOpen(false);
      openButton.focus();
    }
  });
}

function bindCustomPeriodFilter() {
  const toggle = document.querySelector("[data-custom-filter-toggle]");
  const form = document.querySelector("[data-custom-filter]");
  if (!toggle || !form) return;

  toggle.addEventListener("click", () => {
    const willOpen = form.hidden;
    form.hidden = !willOpen;
    toggle.setAttribute("aria-expanded", String(willOpen));
    if (willOpen) form.querySelector("input[type='date']")?.focus();
  });
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

function bindExpenseCategories() {
  const catalogElement = document.getElementById("expenseCategoryCatalog");
  if (!catalogElement) return;

  let catalog;
  try {
    catalog = JSON.parse(catalogElement.textContent || "{}");
  } catch (_error) {
    return;
  }

  document.querySelectorAll("[data-expense-category-select]").forEach((categorySelect) => {
    const form = categorySelect.closest("form");
    const typeSelect = form?.querySelector("[data-expense-type-select]");
    if (!typeSelect) return;

    typeSelect.addEventListener("change", () => {
      const categories = catalog[typeSelect.value] || [];
      const currentCategory = categorySelect.value;
      categorySelect.replaceChildren(...categories.map((category) => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        return option;
      }));
      categorySelect.value = categories.includes(currentCategory) ? currentCategory : (categories[0] || "");
    });
  });
}

function santiagoNowParts() {
  const now = new Date();
  const formatter = new Intl.DateTimeFormat("es-CL", {
    timeZone: "America/Santiago",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = Object.fromEntries(formatter.formatToParts(now).map((part) => [part.type, part.value]));
  const hour = parts.hour === "24" ? "00" : parts.hour;
  return {
    date: `${parts.day}-${parts.month}-${parts.year}`,
    time: `${hour}:${parts.minute}`,
  };
}

function bindFillNow() {
  document.querySelectorAll("[data-fill-now]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.fillTarget;
      if (!target) return;
      const form = button.closest("form");
      if (!form) return;
      const dateInput = form.querySelector(`input[name="${target}_date"]`);
      const timeInput = form.querySelector(`input[name="${target}_time"]`);
      const now = santiagoNowParts();
      if (dateInput) {
        dateInput.value = now.date;
        dateInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      if (timeInput) {
        timeInput.value = now.time;
        timeInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
  });
}

function bindHistoryPeriod() {
  const periodSelect = document.querySelector("[data-history-period]");
  const customFields = document.querySelector("[data-history-custom-period]");
  if (!periodSelect || !customFields) return;

  const updateVisibility = () => {
    customFields.hidden = periodSelect.value !== "custom";
  };
  periodSelect.addEventListener("change", updateVisibility);
  updateVisibility();
}

document.addEventListener("DOMContentLoaded", () => {
  bindMobileNavigation();
  bindCustomPeriodFilter();
  bindConfirmations();
  bindDateTimeMasks();
  bindDeleteDialog();
  bindActionMenus();
  bindExpenseCategories();
  bindHistoryPeriod();
  bindFillNow();
  buildCharts();
});
