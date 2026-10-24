/**
 * FinanceFlow - Personal Expense Tracker
 * Responsive Mobile, Tablet & Desktop Frontend Script
 */

let dailyChartInstance = null;
let categoryChartInstance = null;
let historyChartInstance = null;
let paymentChartInstance = null;

// ==================== THEME MANAGEMENT ====================

function initTheme() {
    const savedTheme = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (savedTheme === "dark" || (!savedTheme && prefersDark)) {
        document.documentElement.classList.add("dark");
    } else {
        document.documentElement.classList.remove("dark");
    }
}

function toggleDarkMode() {
    const isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("theme", isDark ? "dark" : "light");
    // Update charts if instantiated
    updateAllChartsTheme();
}

function isDarkMode() {
    return document.documentElement.classList.contains("dark");
}

function getCurrencySymbol() {
    return window.CURRENCY_SYMBOL || "$";
}

async function changeCurrency(code) {
    try {
        const res = await fetch("/api/settings/currency", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: code })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            setTimeout(() => window.location.reload(), 300);
        } else {
            showToast(data.error || "Failed to update currency", "error");
        }
    } catch (err) {
        showToast("Network error updating currency", "error");
    }
}

function getChartColors() {
    const dark = isDarkMode();
    return {
        text: dark ? "#94A3B8" : "#64748B",
        grid: dark ? "rgba(51, 65, 85, 0.4)" : "rgba(226, 232, 240, 0.7)",
        tooltipBg: dark ? "#1E293B" : "#FFFFFF",
        tooltipText: dark ? "#F8FAFC" : "#0F172A",
        tooltipBorder: dark ? "#334155" : "#E2E8F0"
    };
}

function updateAllChartsTheme() {
    const theme = getChartColors();
    [dailyChartInstance, categoryChartInstance, historyChartInstance, paymentChartInstance].forEach(chart => {
        if (!chart) return;
        if (chart.options.scales?.x) {
            chart.options.scales.x.ticks.color = theme.text;
            chart.options.scales.x.grid.color = theme.grid;
        }
        if (chart.options.scales?.y) {
            chart.options.scales.y.ticks.color = theme.text;
            chart.options.scales.y.grid.color = theme.grid;
        }
        if (chart.options.plugins?.legend) {
            chart.options.plugins.legend.labels.color = theme.text;
        }
        chart.update();
    });
}

// ==================== TOAST NOTIFICATION HELPER ====================

function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast-enter pointer-events-auto flex items-center space-x-3 px-4 py-3 rounded-2xl shadow-xl border text-sm font-semibold transition-all ${
        type === "success" 
            ? "bg-white dark:bg-slate-900 border-teal-500/40 text-teal-800 dark:text-teal-300"
            : type === "error"
            ? "bg-white dark:bg-slate-900 border-rose-500/40 text-rose-700 dark:text-rose-300"
            : "bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200"
    }`;

    const icon = type === "success" ? "fa-circle-check text-teal-500" : type === "error" ? "fa-circle-exclamation text-rose-500" : "fa-circle-info text-blue-500";
    toast.innerHTML = `
        <i class="fa-solid ${icon} text-base flex-shrink-0"></i>
        <span class="flex-1">${message}</span>
        <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1">
            <i class="fa-solid fa-xmark text-xs"></i>
        </button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        setTimeout(() => toast.remove(), 300);
    }, 3800);
}

// ==================== CHART INITIALIZERS ====================

async function initDashboardCharts(month) {
    try {
        const response = await fetch(`/api/chart-data?month=${month}`);
        const data = await response.json();
        renderDailyTrendChart(data.daily);
        renderCategoryDonutChart(data.categories);
    } catch (err) {
        console.error("Failed to load dashboard chart data:", err);
    }
}

async function initReportsCharts(month) {
    try {
        const response = await fetch(`/api/chart-data?month=${month}`);
        const data = await response.json();
        renderDailyTrendChart(data.daily);
        renderCategoryDonutChart(data.categories);
        renderHistoryBarChart(data.history);
        renderPaymentMethodsChart(data.payment_methods);
    } catch (err) {
        console.error("Failed to load reports chart data:", err);
    }
}

function renderDailyTrendChart(dailyData) {
    const ctx = document.getElementById("dailyTrendChart");
    if (!ctx) return;
    if (dailyChartInstance) dailyChartInstance.destroy();

    const theme = getChartColors();
    const sym = getCurrencySymbol();
    dailyChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: dailyData.labels,
            datasets: [{
                label: `Daily Spend (${sym})`,
                data: dailyData.values,
                backgroundColor: "rgba(13, 148, 136, 0.75)",
                hoverBackgroundColor: "rgba(13, 148, 136, 1)",
                borderRadius: 6,
                borderSkipped: false,
                barPercentage: 0.7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: theme.tooltipBg,
                    titleColor: theme.tooltipText,
                    bodyColor: theme.tooltipText,
                    borderColor: theme.tooltipBorder,
                    borderWidth: 1,
                    padding: 10,
                    boxPadding: 4,
                    callbacks: {
                        label: (ctx) => `Spent: ${sym}${ctx.raw.toFixed(2)}`
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: theme.text, font: { size: 10 } }
                },
                y: {
                    grid: { color: theme.grid },
                    ticks: {
                        color: theme.text,
                        font: { size: 10 },
                        callback: (v) => `${sym}${v}`
                    }
                }
            }
        }
    });
}

function renderCategoryDonutChart(catData) {
    const ctx = document.getElementById("categoryDonutChart");
    if (!ctx) return;
    if (categoryChartInstance) categoryChartInstance.destroy();

    const theme = getChartColors();
    const sym = getCurrencySymbol();
    if (!catData.labels || catData.labels.length === 0) {
        // Fallback for empty state
        catData = {
            labels: ["No expenses"],
            values: [1],
            colors: ["#94A3B8"]
        };
    }

    categoryChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: catData.labels,
            datasets: [{
                data: catData.values,
                backgroundColor: catData.colors,
                borderWidth: 2,
                borderColor: isDarkMode() ? "#0F172A" : "#FFFFFF",
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "70%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: theme.text,
                        font: { size: 11, family: "Segoe UI, sans-serif" },
                        boxWidth: 12,
                        padding: 12
                    }
                },
                tooltip: {
                    backgroundColor: theme.tooltipBg,
                    titleColor: theme.tooltipText,
                    bodyColor: theme.tooltipText,
                    borderColor: theme.tooltipBorder,
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: (ctx) => ` ${sym}${ctx.raw.toFixed(2)}`
                    }
                }
            }
        }
    });
}

function renderHistoryBarChart(historyData) {
    const ctx = document.getElementById("historyBarChart");
    if (!ctx) return;
    if (historyChartInstance) historyChartInstance.destroy();

    const theme = getChartColors();
    const sym = getCurrencySymbol();
    historyChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: historyData.labels,
            datasets: [{
                label: `Monthly Total (${sym})`,
                data: historyData.values,
                backgroundColor: "rgba(59, 130, 246, 0.75)",
                hoverBackgroundColor: "rgba(59, 130, 246, 1)",
                borderRadius: 8,
                barPercentage: 0.55
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: theme.tooltipBg,
                    titleColor: theme.tooltipText,
                    bodyColor: theme.tooltipText,
                    borderColor: theme.tooltipBorder,
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: (ctx) => `Total: ${sym}${ctx.raw.toFixed(2)}`
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: theme.text, font: { size: 11 } }
                },
                y: {
                    grid: { color: theme.grid },
                    ticks: {
                        color: theme.text,
                        font: { size: 10 },
                        callback: (v) => `${sym}${v}`
                    }
                }
            }
        }
    });
}

function renderPaymentMethodsChart(paymentData) {
    const ctx = document.getElementById("paymentMethodsChart");
    if (!ctx) return;
    if (paymentChartInstance) paymentChartInstance.destroy();

    const theme = getChartColors();
    const sym = getCurrencySymbol();
    const colors = ["#14B8A6", "#3B82F6", "#8B5CF6", "#F59E0B", "#EC4899", "#10B981"];

    paymentChartInstance = new Chart(ctx, {
        type: "pie",
        data: {
            labels: paymentData.labels,
            datasets: [{
                data: paymentData.values,
                backgroundColor: colors.slice(0, paymentData.labels.length),
                borderWidth: 2,
                borderColor: isDarkMode() ? "#0F172A" : "#FFFFFF"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: theme.text,
                        font: { size: 11 },
                        boxWidth: 12,
                        padding: 12
                    }
                },
                tooltip: {
                    backgroundColor: theme.tooltipBg,
                    titleColor: theme.tooltipText,
                    bodyColor: theme.tooltipText,
                    borderColor: theme.tooltipBorder,
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: (ctx) => ` ${sym}${ctx.raw.toFixed(2)}`
                    }
                }
            }
        }
    });
}

// ==================== EXPENSE MODAL & CRUD ====================

function openAddExpenseModal() {
    const form = document.getElementById("expenseForm");
    if (form) form.reset();
    document.getElementById("expenseId").value = "";
    if (document.getElementById("expenseAccount")) {
        document.getElementById("expenseAccount").value = "";
    }
    document.getElementById("modalTitle").textContent = "Log New Expense";
    document.getElementById("saveExpenseBtnText").textContent = "Save Expense";
    document.getElementById("expenseDate").value = new Date().toISOString().split("T")[0];

    const modal = document.getElementById("expenseModal");
    modal.classList.remove("hidden");
    document.getElementById("expenseAmount").focus();
}

function closeExpenseModal() {
    document.getElementById("expenseModal").classList.add("hidden");
}

function quickSetAmount(val) {
    const amtInput = document.getElementById("expenseAmount");
    const current = parseFloat(amtInput.value || 0);
    amtInput.value = (current + val).toFixed(2);
}

async function editExpense(id) {
    try {
        const res = await fetch(`/api/expense/${id}`);
        const data = await res.json();
        if (!data.success) {
            showToast(data.error || "Expense not found", "error");
            return;
        }

        const exp = data.expense;
        document.getElementById("expenseId").value = exp.id;
        document.getElementById("expenseAmount").value = exp.amount;
        document.getElementById("expenseDescription").value = exp.description;
        document.getElementById("expenseCategory").value = exp.category_id;
        document.getElementById("expenseDate").value = exp.date;
        document.getElementById("expenseNotes").value = exp.notes || "";
        if (document.getElementById("expenseAccount")) {
            document.getElementById("expenseAccount").value = exp.account_id || "";
        }

        // Select payment method radio
        const radios = document.getElementsByName("payment_method");
        for (let r of radios) {
            if (r.value === exp.payment_method) {
                r.checked = true;
                break;
            }
        }

        document.getElementById("modalTitle").textContent = "Edit Expense";
        document.getElementById("saveExpenseBtnText").textContent = "Update Expense";

        document.getElementById("expenseModal").classList.remove("hidden");
    } catch (err) {
        showToast("Error loading expense details", "error");
    }
}

async function handleExpenseSubmit(e) {
    e.preventDefault();
    const saveBtn = document.getElementById("saveExpenseBtn");
    saveBtn.disabled = true;

    const id = document.getElementById("expenseId").value;
    const isEdit = Boolean(id);

    const payload = {
        amount: document.getElementById("expenseAmount").value,
        description: document.getElementById("expenseDescription").value,
        category_id: document.getElementById("expenseCategory").value,
        account_id: document.getElementById("expenseAccount")?.value || null,
        date: document.getElementById("expenseDate").value,
        payment_method: document.querySelector('input[name="payment_method"]:checked')?.value || "Cash",
        notes: document.getElementById("expenseNotes").value
    };

    try {
        const url = isEdit ? `/api/expense/${id}` : "/api/expense";
        const method = isEdit ? "PUT" : "POST";

        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            showToast(data.message || (isEdit ? "Expense updated!" : "Expense logged!"));
            closeExpenseModal();
            setTimeout(() => window.location.reload(), 400);
        } else {
            showToast(data.error || "Failed to save expense", "error");
        }
    } catch (err) {
        showToast("Network error. Please try again.", "error");
    } finally {
        saveBtn.disabled = false;
    }
}

async function deleteExpense(id) {
    if (!confirm("Are you sure you want to delete this expense record?")) return;

    try {
        const res = await fetch(`/api/expense/${id}/delete`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Expense record deleted");
            setTimeout(() => window.location.reload(), 300);
        } else {
            showToast(data.error || "Failed to delete expense", "error");
        }
    } catch (err) {
        showToast("Network error deleting expense", "error");
    }
}

// ==================== EXCEL IMPORT MODAL ====================

function openImportModal() {
    document.getElementById("importModal").classList.remove("hidden");
    document.getElementById("selectedFileName").textContent = "Click or drag & drop .xlsx file here";
    document.getElementById("uploadExcelBtn").disabled = true;
    document.getElementById("excelFileInput").value = "";
}

function closeImportModal() {
    document.getElementById("importModal").classList.add("hidden");
}

function handleFileSelect(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        document.getElementById("selectedFileName").textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        document.getElementById("uploadExcelBtn").disabled = false;
    }
}

async function submitExcelImport() {
    const fileInput = document.getElementById("excelFileInput");
    if (!fileInput.files || !fileInput.files[0]) return;

    const btn = document.getElementById("uploadExcelBtn");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Importing...`;

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
        const res = await fetch("/import/excel", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            closeImportModal();
            setTimeout(() => window.location.reload(), 700);
        } else {
            showToast(data.error || "Import failed", "error");
        }
    } catch (err) {
        showToast("Error uploading Excel file", "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-upload"></i> <span>Import Spreadsheet</span>`;
    }
}

// Setup drag and drop on dropZone
document.addEventListener("DOMContentLoaded", function() {
    initTheme();

    const dropZone = document.getElementById("dropZone");
    if (dropZone) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add("border-teal-500", "bg-teal-50/50");
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove("border-teal-500", "bg-teal-50/50");
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files[0]) {
                document.getElementById('excelFileInput').files = files;
                handleFileSelect({ files: files });
            }
        });
    }

    initCategoryPickers();
});

// ==================== CATEGORIES & BUDGET MANAGEMENT ====================

const ICONS = ["utensils", "shopping-cart", "car", "bolt", "film", "bag-shopping", "heart-pulse", "plane", "book", "sparkles", "box-archive", "dumbbell"];
const COLORS = ["#EF4444", "#F59E0B", "#10B981", "#06B6D4", "#3B82F6", "#6366F1", "#8B5CF6", "#EC4899", "#F97316", "#14B8A6", "#6B7280"];

function initCategoryPickers() {
    const iconContainer = document.getElementById("iconPicker");
    const colorContainer = document.getElementById("colorPicker");
    if (!iconContainer || !colorContainer) return;

    // Render Icons
    iconContainer.innerHTML = ICONS.map(icon => `
        <button type="button" onclick="selectIcon('${icon}')" class="icon-option p-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-teal-500 dark:hover:border-teal-400 flex items-center justify-center text-slate-700 dark:text-slate-300 ${icon === 'tag' ? 'active ring-2 ring-teal-500' : ''}" data-icon="${icon}">
            <i class="fa-solid fa-${icon} text-sm"></i>
        </button>
    `).join("");

    // Render Colors
    colorContainer.innerHTML = COLORS.map(color => `
        <button type="button" onclick="selectColor('${color}')" class="color-option w-7 h-7 rounded-full shadow-sm hover:scale-110 transition-transform ${color === '#3B82F6' ? 'active ring-2 ring-offset-2 ring-slate-800 dark:ring-offset-slate-900 ring-teal-500' : ''}" style="background-color: ${color};" data-color="${color}">
        </button>
    `).join("");
}

function selectIcon(icon) {
    document.getElementById("catIcon").value = icon;
    document.querySelectorAll(".icon-option").forEach(el => {
        el.classList.toggle("ring-2", el.dataset.icon === icon);
        el.classList.toggle("ring-teal-500", el.dataset.icon === icon);
    });
}

function selectColor(color) {
    document.getElementById("catColor").value = color;
    document.querySelectorAll(".color-option").forEach(el => {
        el.classList.toggle("ring-2", el.dataset.color === color);
        el.classList.toggle("ring-offset-2", el.dataset.color === color);
        el.classList.toggle("ring-teal-500", el.dataset.color === color);
    });
}

function openAddCategoryModal() {
    const form = document.getElementById("categoryForm");
    if (form) form.reset();
    document.getElementById("categoryId").value = "";
    document.getElementById("catModalTitle").textContent = "Add New Category";
    document.getElementById("saveCatBtnText").textContent = "Save Category";
    selectIcon("tag");
    selectColor("#3B82F6");
    document.getElementById("categoryModal").classList.remove("hidden");
}

function closeCategoryModal() {
    document.getElementById("categoryModal").classList.add("hidden");
}

function editCategory(cat) {
    document.getElementById("categoryId").value = cat.id;
    document.getElementById("catName").value = cat.name;
    document.getElementById("catBudget").value = cat.monthly_budget;
    selectIcon(cat.icon);
    selectColor(cat.color);
    document.getElementById("catModalTitle").textContent = "Edit Category";
    document.getElementById("saveCatBtnText").textContent = "Update Category";
    document.getElementById("categoryModal").classList.remove("hidden");
}

async function handleCategorySubmit(e) {
    e.preventDefault();
    const btn = document.getElementById("saveCatBtn");
    btn.disabled = true;

    const id = document.getElementById("categoryId").value;
    const isEdit = Boolean(id);

    const payload = {
        name: document.getElementById("catName").value,
        monthly_budget: document.getElementById("catBudget").value,
        icon: document.getElementById("catIcon").value,
        color: document.getElementById("catColor").value
    };

    try {
        const url = isEdit ? `/api/category/${id}` : "/api/category";
        const method = isEdit ? "PUT" : "POST";

        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            showToast(data.message || "Category saved!");
            closeCategoryModal();
            setTimeout(() => window.location.reload(), 400);
        } else {
            showToast(data.error || "Failed to save category", "error");
        }
    } catch (err) {
        showToast("Network error. Please try again.", "error");
    } finally {
        btn.disabled = false;
    }
}

async function deleteCategory(id, name) {
    if (!confirm(`Are you sure you want to delete category "${name}"?`)) return;

    try {
        const res = await fetch(`/api/category/${id}/delete`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Category removed");
            setTimeout(() => window.location.reload(), 300);
        } else {
            showToast(data.error || "Failed to delete category", "error");
        }
    } catch (err) {
        showToast("Network error deleting category", "error");
    }
}

// ==================== BANK ACCOUNT MODAL & CRUD ====================

function openAddAccountModal() {
    const form = document.getElementById("accountForm");
    if (form) form.reset();
    document.getElementById("bankAccountId").value = "";
    document.getElementById("accountModalTitle").textContent = "Add Bank Account";
    document.getElementById("saveAccountBtnText").textContent = "Save Bank Account";
    const modal = document.getElementById("accountModal");
    if (modal) {
        modal.classList.remove("hidden");
        document.getElementById("accountName").focus();
    }
}

function closeAccountModal() {
    const modal = document.getElementById("accountModal");
    if (modal) modal.classList.add("hidden");
}

function editAccount(acc) {
    document.getElementById("bankAccountId").value = acc.id;
    document.getElementById("accountName").value = acc.name;
    document.getElementById("accountType").value = acc.account_type || "Checking";
    document.getElementById("accountNumber").value = acc.account_number || "";
    document.getElementById("accountInitialBalance").value = acc.initial_balance;

    // Set color radio
    const colorRadios = document.getElementsByName("color");
    for (let r of colorRadios) {
        if (r.value === acc.color) {
            r.checked = true;
            break;
        }
    }

    // Set icon radio
    const iconRadios = document.getElementsByName("icon");
    for (let r of iconRadios) {
        if (r.value === acc.icon) {
            r.checked = true;
            break;
        }
    }

    document.getElementById("accountModalTitle").textContent = "Edit Bank Account";
    document.getElementById("saveAccountBtnText").textContent = "Update Account";
    const modal = document.getElementById("accountModal");
    if (modal) modal.classList.remove("hidden");
}

async function handleAccountSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById("saveAccountBtn");
    btn.disabled = true;

    const id = document.getElementById("bankAccountId").value;
    const isEdit = Boolean(id);

    const payload = {
        name: document.getElementById("accountName").value,
        account_type: document.getElementById("accountType").value,
        account_number: document.getElementById("accountNumber").value,
        initial_balance: document.getElementById("accountInitialBalance").value,
        color: document.querySelector('input[name="color"]:checked')?.value || "#0D9488",
        icon: document.querySelector('input[name="icon"]:checked')?.value || "building-columns"
    };

    try {
        const url = isEdit ? `/api/account/${id}` : "/api/account";
        const method = isEdit ? "PUT" : "POST";

        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            showToast(data.message || "Bank account saved successfully!");
            closeAccountModal();
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to save bank account", "error");
        }
    } catch (err) {
        showToast("Network error. Please try again.", "error");
    } finally {
        btn.disabled = false;
    }
}

async function deleteAccount(id, name) {
    if (!confirm(`Are you sure you want to delete account "${name}"?\nAny expenses linked to this account will remain saved, but will become unlinked.`)) return;

    try {
        const res = await fetch(`/api/account/${id}/delete`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Bank account removed successfully");
            setTimeout(() => window.location.reload(), 300);
        } else {
            showToast(data.error || "Failed to delete account", "error");
        }
    } catch (err) {
        showToast("Network error deleting bank account", "error");
    }
}

// ==================== MONTHLY BUDGET MODAL & MANAGEMENT ====================

let cachedBudgetCategories = [];

async function openEditMonthlyBudgetModal(focusCatId = null) {
    const modal = document.getElementById("monthlyBudgetModal");
    if (!modal) return;

    try {
        const res = await fetch("/api/budget");
        const data = await res.json();
        if (!data.success) {
            showToast("Failed to load budget data", "error");
            return;
        }

        cachedBudgetCategories = data.categories || [];
        const sym = getCurrencySymbol();
        const total = data.total_budget || 0;

        document.getElementById("modalTargetBudgetInput").value = total.toFixed(2);
        
        const listContainer = document.getElementById("modalCategoryBudgetList");
        listContainer.innerHTML = "";

        cachedBudgetCategories.forEach(cat => {
            const row = document.createElement("div");
            row.id = `cat-budget-row-${cat.id}`;
            row.className = "py-2.5 flex items-center justify-between gap-3 group transition-colors rounded-xl px-2 hover:bg-slate-50 dark:hover:bg-slate-800/40";
            
            row.innerHTML = `
                <div class="flex items-center space-x-2.5 min-w-0 flex-1">
                    <div class="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs flex-shrink-0 shadow-sm" style="background-color: ${cat.color}">
                        <i class="fa-solid fa-${cat.icon}"></i>
                    </div>
                    <div class="min-w-0">
                        <p class="text-xs font-bold text-slate-800 dark:text-slate-100 truncate">${cat.name}</p>
                        <span class="text-[10px] text-slate-400">Spent: ${sym}${Number(cat.current_month_spent || 0).toFixed(2)}</span>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <span id="pct-badge-${cat.id}" class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 w-14 text-center">
                        0%
                    </span>
                    <div class="relative w-28 sm:w-32">
                        <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400 pointer-events-none">${sym}</span>
                        <input type="number" step="5" min="0" data-cat-id="${cat.id}" value="${Number(cat.monthly_budget || 0).toFixed(2)}" class="modal-cat-budget-input w-full pl-6 pr-2 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-bold text-right text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500 outline-none transition-all" oninput="onCategoryBudgetInputChange()">
                    </div>
                </div>
            `;
            listContainer.appendChild(row);
        });

        recalculateModalTotalBudget();
        modal.classList.remove("hidden");

        if (focusCatId) {
            const targetRow = document.getElementById(`cat-budget-row-${focusCatId}`);
            if (targetRow) {
                targetRow.classList.add("bg-teal-50/80", "dark:bg-teal-950/50");
                const input = targetRow.querySelector(".modal-cat-budget-input");
                if (input) {
                    input.focus();
                    input.select();
                }
            }
        } else {
            document.getElementById("modalTargetBudgetInput").focus();
        }
    } catch (err) {
        showToast("Error opening budget editor", "error");
    }
}

function closeMonthlyBudgetModal() {
    const modal = document.getElementById("monthlyBudgetModal");
    if (modal) modal.classList.add("hidden");
}

function onCategoryBudgetInputChange() {
    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    let total = 0;
    inputs.forEach(inp => {
        total += parseFloat(inp.value || 0);
    });

    const sym = getCurrencySymbol();
    document.getElementById("modalLiveTotalSum").textContent = `${sym}${total.toFixed(2)}`;
    document.getElementById("modalFooterTotal").textContent = `${sym}${total.toFixed(2)}`;
    document.getElementById("modalTargetBudgetInput").value = total.toFixed(2);

    // Update percentage badges
    inputs.forEach(inp => {
        const catId = inp.dataset.catId;
        const val = parseFloat(inp.value || 0);
        const pct = total > 0 ? (val / total * 100).toFixed(1) : 0;
        const badge = document.getElementById(`pct-badge-${catId}`);
        if (badge) badge.textContent = `${pct}%`;
    });
}

function recalculateModalTotalBudget() {
    onCategoryBudgetInputChange();
}

function distributeBudgetProportionally() {
    const targetVal = parseFloat(document.getElementById("modalTargetBudgetInput").value || 0);
    if (targetVal < 0) return;

    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    let currentTotal = 0;
    inputs.forEach(inp => currentTotal += parseFloat(inp.value || 0));

    if (currentTotal > 0) {
        inputs.forEach(inp => {
            const val = parseFloat(inp.value || 0);
            const ratio = val / currentTotal;
            inp.value = (targetVal * ratio).toFixed(2);
        });
    } else {
        distributeBudgetEvenly();
        return;
    }
    recalculateModalTotalBudget();
}

function distributeBudgetEvenly() {
    const targetVal = parseFloat(document.getElementById("modalTargetBudgetInput").value || 0);
    if (targetVal < 0) return;

    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    if (!inputs.length) return;

    const share = (targetVal / inputs.length).toFixed(2);
    inputs.forEach(inp => inp.value = share);
    recalculateModalTotalBudget();
}

async function handleSaveMonthlyBudget() {
    const saveBtn = document.getElementById("saveBudgetBtn");
    saveBtn.disabled = true;
    document.getElementById("saveBudgetBtnText").textContent = "Saving...";

    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    const categoryBudgets = {};
    inputs.forEach(inp => {
        categoryBudgets[inp.dataset.catId] = parseFloat(inp.value || 0);
    });

    try {
        const res = await fetch("/api/budget", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ category_budgets: categoryBudgets })
        });

        const data = await res.json();
        if (data.success) {
            showToast("Monthly budget updated successfully!");
            closeMonthlyBudgetModal();
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to update monthly budget", "error");
        }
    } catch (err) {
        showToast("Network error saving budget", "error");
    } finally {
        saveBtn.disabled = false;
        document.getElementById("saveBudgetBtnText").textContent = "Save Monthly Budget";
    }
}

function openQuickCategoryBudgetEdit(catId, catName, currentBudget) {
    openEditMonthlyBudgetModal(catId);
}
