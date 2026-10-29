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
    setTimeout(() => {
        const amt = document.getElementById("expenseAmount");
        if (amt) { amt.focus(); amt.select(); }
    }, 40);
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

    const formData = new FormData();
    formData.append("amount", document.getElementById("expenseAmount").value);
    formData.append("description", document.getElementById("expenseDescription").value);
    formData.append("category_id", document.getElementById("expenseCategory").value);
    formData.append("date", document.getElementById("expenseDate").value);
    formData.append("payment_method", document.querySelector('input[name="payment_method"]:checked')?.value || "Cash");
    formData.append("notes", document.getElementById("expenseNotes").value || "");
    
    const accId = document.getElementById("expenseAccount")?.value;
    if (accId) formData.append("account_id", accId);

    const receiptFile = document.getElementById("expenseReceipt")?.files[0];
    if (receiptFile) {
        formData.append("receipt", receiptFile);
    }

    try {
        const url = isEdit ? `/api/expense/${id}` : "/api/expense";
        const method = isEdit ? "PUT" : "POST";

        const res = await fetch(url, {
            method: method,
            body: formData
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
    document.getElementById("catBudget").value = (cat.monthly_budget && Number(cat.monthly_budget) > 0) ? cat.monthly_budget : "";
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
        const total = Number(data.total_budget || 0);

        document.getElementById("modalTargetBudgetInput").value = total > 0 ? total.toFixed(2) : "";
        document.getElementById("modalFooterTotal").textContent = `${sym}${total.toFixed(2)}`;
        
        const listContainer = document.getElementById("modalCategoryBudgetList");
        listContainer.innerHTML = "";

        let catSum = 0;
        cachedBudgetCategories.forEach(cat => {
            const bVal = Number(cat.monthly_budget || 0);
            catSum += bVal;
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
                    <span id="pct-badge-${cat.id}" class="text-[10px] font-semibold px-2 py-0.5 rounded-full w-16 text-center transition-all">
                        0%
                    </span>
                    <div class="relative w-28 sm:w-32">
                        <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400 pointer-events-none">${sym}</span>
                        <input type="number" step="5" min="0" data-cat-id="${cat.id}" placeholder="0.00" value="${bVal > 0 ? bVal.toFixed(2) : '0.00'}" class="modal-cat-budget-input w-full pl-6 pr-2 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-bold text-right text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500 outline-none transition-all" oninput="onCategoryBudgetInputChange()">
                    </div>
                </div>
            `;
            listContainer.appendChild(row);
        });

        document.getElementById("modalLiveTotalSum").textContent = `${sym}${catSum.toFixed(2)}`;
        updateModalCategoryBadges();
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

function onTargetBudgetInputChange() {
    const sym = getCurrencySymbol();
    const targetVal = parseFloat(document.getElementById("modalTargetBudgetInput").value || 0);
    document.getElementById("modalFooterTotal").textContent = `${sym}${targetVal.toFixed(2)}`;
    updateModalCategoryBadges();
}

function onCategoryBudgetInputChange() {
    const sym = getCurrencySymbol();
    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    let catSum = 0;
    inputs.forEach(inp => {
        catSum += parseFloat(inp.value || 0);
    });
    document.getElementById("modalLiveTotalSum").textContent = `${sym}${catSum.toFixed(2)}`;

    // If overall target budget input is completely empty or 0, initialize it to catSum
    const targetInp = document.getElementById("modalTargetBudgetInput");
    if (!targetInp.value || parseFloat(targetInp.value) === 0) {
        targetInp.value = catSum.toFixed(2);
        document.getElementById("modalFooterTotal").textContent = `${sym}${catSum.toFixed(2)}`;
    }
    updateModalCategoryBadges();
}

function updateModalCategoryBadges() {
    const targetVal = parseFloat(document.getElementById("modalTargetBudgetInput").value || 0);
    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    inputs.forEach(inp => {
        const catId = inp.dataset.catId;
        const val = parseFloat(inp.value || 0);
        const badge = document.getElementById(`pct-badge-${catId}`);
        if (!badge) return;
        if (val <= 0) {
            badge.textContent = "Uncapped";
            badge.className = "text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 w-16 text-center";
        } else if (targetVal > 0) {
            const pct = Math.round((val / targetVal) * 100);
            badge.textContent = `${pct}%`;
            badge.className = "text-[10px] font-semibold px-2 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/60 text-teal-600 dark:text-teal-400 border border-teal-200/50 dark:border-teal-800/50 w-16 text-center";
        } else {
            badge.textContent = "Limit";
            badge.className = "text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 w-16 text-center";
        }
    });
}

function recalculateModalTotalBudget() {
    onCategoryBudgetInputChange();
}

function uncapAllCategoryBudgets() {
    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    inputs.forEach(inp => inp.value = "0.00");
    const sym = getCurrencySymbol();
    document.getElementById("modalLiveTotalSum").textContent = `${sym}0.00`;
    updateModalCategoryBadges();
}

function matchCategorySum() {
    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    let catSum = 0;
    inputs.forEach(inp => catSum += parseFloat(inp.value || 0));
    document.getElementById("modalTargetBudgetInput").value = catSum.toFixed(2);
    onTargetBudgetInputChange();
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
    const sym = getCurrencySymbol();
    let catSum = 0;
    inputs.forEach(inp => catSum += parseFloat(inp.value || 0));
    document.getElementById("modalLiveTotalSum").textContent = `${sym}${catSum.toFixed(2)}`;
    updateModalCategoryBadges();
}

function distributeBudgetEvenly() {
    const targetVal = parseFloat(document.getElementById("modalTargetBudgetInput").value || 0);
    if (targetVal < 0) return;

    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    if (!inputs.length) return;

    const share = (targetVal / inputs.length).toFixed(2);
    inputs.forEach(inp => inp.value = share);
    const sym = getCurrencySymbol();
    document.getElementById("modalLiveTotalSum").textContent = `${sym}${targetVal.toFixed(2)}`;
    updateModalCategoryBadges();
}

async function handleSaveMonthlyBudget() {
    const saveBtn = document.getElementById("saveBudgetBtn");
    saveBtn.disabled = true;
    document.getElementById("saveBudgetBtnText").textContent = "Saving...";

    const targetVal = parseFloat(document.getElementById("modalTargetBudgetInput").value || 0);
    const inputs = document.querySelectorAll(".modal-cat-budget-input");
    const categoryBudgets = {};
    inputs.forEach(inp => {
        categoryBudgets[inp.dataset.catId] = parseFloat(inp.value || 0);
    });

    try {
        const res = await fetch("/api/budget", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                total_budget: targetVal,
                category_budgets: categoryBudgets
            })
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

// ============================================================
// FinanceFlow v2.0 Additions: PWA, Income, Transfers,
// Subscriptions, Goals, AI Receipt OCR, 2FA Security
// ============================================================

// --- 1. PWA Service Worker Registration ---
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/service-worker.js')
            .then(reg => console.log('FinanceFlow PWA Worker active:', reg.scope))
            .catch(err => console.warn('PWA Worker registration failed:', err));
    });
}

// --- 2. Receipt Attachment, Lightbox & Smart AI OCR ---
let currentReceiptPreviewUrl = null;

function previewReceiptFile(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        document.getElementById("receiptLabelText").textContent = file.name;
        
        if (file.type.startsWith("image/")) {
            const reader = new FileReader();
            reader.onload = function(e) {
                currentReceiptPreviewUrl = e.target.result;
                const thumb = document.getElementById("receiptPreviewThumb");
                const img = document.getElementById("receiptThumbImg");
                img.src = e.target.result;
                thumb.classList.remove("hidden");
            };
            reader.readAsDataURL(file);
        } else {
            currentReceiptPreviewUrl = null;
            document.getElementById("receiptPreviewThumb").classList.add("hidden");
        }
    }
}

function viewAttachedReceipt() {
    if (currentReceiptPreviewUrl) {
        viewReceiptImage(currentReceiptPreviewUrl);
    }
}

function viewReceiptImage(url) {
    const modal = document.getElementById("receiptLightboxModal");
    const img = document.getElementById("lightboxImg");
    img.src = url;
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
}

function closeReceiptLightbox() {
    const modal = document.getElementById("receiptLightboxModal");
    modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
}

function openReceiptScanner() {
    const modal = document.getElementById("ocrScannerModal");
    modal.classList.remove("hidden");
    document.getElementById("ocrProgressBox").classList.add("hidden");
    document.getElementById("ocrResultsBox").classList.add("hidden");
    document.getElementById("ocrUploadZone").classList.remove("hidden");
}

function closeReceiptScanner() {
    document.getElementById("ocrScannerModal").classList.add("hidden");
}

let ocrDetectedData = { amount: 0, date: "", merchant: "" };

async function runReceiptOcr(input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];

    document.getElementById("ocrUploadZone").classList.add("hidden");
    const progressBox = document.getElementById("ocrProgressBox");
    progressBox.classList.remove("hidden");

    const statusText = document.getElementById("ocrStatusText");
    const percentText = document.getElementById("ocrPercentText");
    const progressBar = document.getElementById("ocrProgressBar");

    try {
        statusText.textContent = "Loading AI OCR Engine...";
        percentText.textContent = "10%";
        progressBar.style.width = "10%";

        if (!window.Tesseract) {
            await new Promise((resolve, reject) => {
                const s = document.createElement("script");
                s.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
                s.onload = resolve;
                s.onerror = () => reject(new Error("Failed to load OCR library"));
                document.head.appendChild(s);
            });
        }

        const worker = await Tesseract.createWorker("eng");
        
        statusText.textContent = "Scanning receipt image...";
        percentText.textContent = "40%";
        progressBar.style.width = "40%";

        const ret = await worker.recognize(file);
        const text = ret.data.text;
        await worker.terminate();

        progressBar.style.width = "100%";
        percentText.textContent = "100%";
        statusText.textContent = "Extraction complete!";

        // Extract Amounts: Find all dollar patterns $XX.XX or XX.XX
        const amountRegex = /(?:[$€£₹¥]\s*)?([0-9]{1,5}\.[0-9]{2})\b/g;
        let match;
        let highestAmount = 0;
        while ((match = amountRegex.exec(text)) !== null) {
            const val = parseFloat(match[1]);
            if (val > highestAmount && val < 50000) {
                highestAmount = val;
            }
        }

        // Extract Date: YYYY-MM-DD or MM/DD/YYYY or DD-MM-YYYY
        let detectedDate = "";
        const dateRegex = /\b(202[0-9][-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12][0-9]|3[01]))\b/;
        const dateMatch = text.match(dateRegex);
        if (dateMatch) {
            detectedDate = dateMatch[1].replace(/[/.]/g, "-");
        } else {
            detectedDate = new Date().toISOString().split("T")[0];
        }

        // Extract Merchant: usually first non-trivial line
        const lines = text.split("\n").map(l => l.trim()).filter(l => l.length > 2 && !l.includes("RECEIPT") && !l.includes("INVOICE"));
        const merchant = lines.length > 0 ? lines[0].slice(0, 35) : "Scanned Receipt Purchase";

        ocrDetectedData = {
            amount: highestAmount || 25.0,
            date: detectedDate,
            merchant: merchant
        };

        // Also copy scanned file to expense receipt input
        const expenseFileInput = document.getElementById("expenseReceipt");
        if (expenseFileInput) {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            expenseFileInput.files = dataTransfer.files;
            previewReceiptFile(expenseFileInput);
        }

        // Show Results Card
        document.getElementById("ocrDetectedAmount").textContent = (window.CURRENCY_SYMBOL || "$") + ocrDetectedData.amount.toFixed(2);
        document.getElementById("ocrDetectedDate").textContent = ocrDetectedData.date;
        document.getElementById("ocrDetectedMerchant").textContent = ocrDetectedData.merchant;
        document.getElementById("ocrResultsBox").classList.remove("hidden");

    } catch (err) {
        console.error("OCR Failure:", err);
        statusText.textContent = "OCR scanning encountered an issue. You can still enter details manually.";
        showToast("OCR scanning failed on this image", "error");
    }
}

function applyOcrToExpense() {
    closeReceiptScanner();
    openAddExpenseModal();
    if (ocrDetectedData.amount > 0) {
        document.getElementById("expenseAmount").value = ocrDetectedData.amount.toFixed(2);
    }
    if (ocrDetectedData.date) {
        document.getElementById("expenseDate").value = ocrDetectedData.date;
    }
    if (ocrDetectedData.merchant) {
        document.getElementById("expenseDescription").value = ocrDetectedData.merchant;
    }
    showToast("Receipt details applied to expense form!");
}

// --- 3. Income CRUD (v2.0) ---
function openAddIncomeModal() {
    const modal = document.getElementById("incomeModal");
    if (!modal) return;
    document.getElementById("incomeForm").reset();
    document.getElementById("incomeId").value = "";
    document.getElementById("incomeDate").value = new Date().toISOString().split("T")[0];
    document.getElementById("incomeModalTitle").textContent = "Log Income Stream";
    document.getElementById("saveIncomeBtnText").textContent = "Save Income";
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
}

function closeIncomeModal() {
    const modal = document.getElementById("incomeModal");
    if (modal) modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
}

async function handleIncomeSubmit(e) {
    e.preventDefault();
    const saveBtn = document.getElementById("saveIncomeBtn");
    saveBtn.disabled = true;

    const id = document.getElementById("incomeId").value;
    const isEdit = Boolean(id);

    const payload = {
        amount: parseFloat(document.getElementById("incomeAmount").value),
        source: document.getElementById("incomeSource").value.trim(),
        account_id: document.getElementById("incomeAccount")?.value || null,
        date: document.getElementById("incomeDate").value,
        payment_method: document.getElementById("incomePaymentMethod").value,
        notes: document.getElementById("incomeNotes").value.trim()
    };

    try {
        const url = isEdit ? `/api/income/${id}` : "/api/income";
        const method = isEdit ? "PUT" : "POST";

        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            showToast(data.message || (isEdit ? "Income updated!" : "Income logged!"));
            closeIncomeModal();
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to save income", "error");
        }
    } catch (err) {
        showToast("Network error. Please try again.", "error");
    } finally {
        saveBtn.disabled = false;
    }
}

async function editIncome(id) {
    try {
        const res = await fetch(`/api/income/${id}`);
        const data = await res.json();
        if (!data.success || !data.income) {
            showToast("Failed to load income details", "error");
            return;
        }
        const inc = data.income;
        document.getElementById("incomeId").value = inc.id;
        document.getElementById("incomeAmount").value = inc.amount;
        document.getElementById("incomeSource").value = inc.source;
        document.getElementById("incomeDate").value = inc.date;
        document.getElementById("incomePaymentMethod").value = inc.payment_method;
        if (inc.account_id) document.getElementById("incomeAccount").value = inc.account_id;
        document.getElementById("incomeNotes").value = inc.notes || "";

        document.getElementById("incomeModalTitle").textContent = "Edit Income Stream";
        document.getElementById("saveIncomeBtnText").textContent = "Update Income";
        document.getElementById("incomeModal").classList.remove("hidden");
        document.body.classList.add("overflow-hidden");
    } catch (err) {
        showToast("Error retrieving income", "error");
    }
}

async function deleteIncome(id) {
    if (!confirm("Are you sure you want to delete this income record?")) return;
    try {
        const res = await fetch(`/api/income/${id}/delete`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Income deleted successfully!");
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to delete income", "error");
        }
    } catch (err) {
        showToast("Network error deleting income", "error");
    }
}

// --- 4. Account Transfers (v2.0) ---
function openTransferModal() {
    const modal = document.getElementById("transferModal");
    if (!modal) return;
    document.getElementById("transferForm").reset();
    document.getElementById("transferDate").value = new Date().toISOString().split("T")[0];
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
}

function closeTransferModal() {
    const modal = document.getElementById("transferModal");
    if (modal) modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
}

async function handleTransferSubmit(e) {
    e.preventDefault();
    const fromId = document.getElementById("transferFromAccount").value;
    const toId = document.getElementById("transferToAccount").value;
    if (fromId === toId) {
        showToast("Source and destination accounts must be different", "error");
        return;
    }

    const payload = {
        amount: parseFloat(document.getElementById("transferAmount").value),
        from_account_id: parseInt(fromId),
        to_account_id: parseInt(toId),
        date: document.getElementById("transferDate").value,
        notes: document.getElementById("transferNotes").value.trim()
    };

    try {
        const res = await fetch("/api/transfer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || "Transfer completed successfully!");
            closeTransferModal();
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Transfer failed", "error");
        }
    } catch (err) {
        showToast("Network error executing transfer", "error");
    }
}

async function deleteTransferRecord(id) {
    if (!confirm("Are you sure you want to delete this transfer? Account balances will re-adjust.")) return;
    try {
        const res = await fetch(`/api/transfer/${id}/delete`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Transfer deleted!");
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to delete transfer", "error");
        }
    } catch (err) {
        showToast("Network error", "error");
    }
}

// --- 5. Subscriptions & Bills (v2.0) ---
function openAddSubscriptionModal() {
    const modal = document.getElementById("subscriptionModal");
    if (!modal) return;
    document.getElementById("subscriptionForm").reset();
    document.getElementById("subscriptionId").value = "";
    document.getElementById("subNextDueDate").value = new Date().toISOString().split("T")[0];
    document.getElementById("subscriptionModalTitle").textContent = "Add Subscription";
    document.getElementById("saveSubBtnText").textContent = "Save Subscription";
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
}

function closeSubscriptionModal() {
    const modal = document.getElementById("subscriptionModal");
    if (modal) modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
}

async function handleSubscriptionSubmit(e) {
    e.preventDefault();
    const saveBtn = document.getElementById("saveSubBtn");
    saveBtn.disabled = true;

    const id = document.getElementById("subscriptionId").value;
    const isEdit = Boolean(id);

    const payload = {
        name: document.getElementById("subName").value.trim(),
        amount: parseFloat(document.getElementById("subAmount").value),
        billing_cycle: document.getElementById("subCycle").value,
        next_due_date: document.getElementById("subNextDueDate").value,
        category_id: document.getElementById("subCategory")?.value || null,
        account_id: document.getElementById("subAccount")?.value || null,
        notes: document.getElementById("subNotes").value.trim()
    };

    try {
        const url = isEdit ? `/api/subscription/${id}` : "/api/subscription";
        const method = isEdit ? "PUT" : "POST";

        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            showToast(data.message || "Subscription saved!");
            closeSubscriptionModal();
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to save subscription", "error");
        }
    } catch (err) {
        showToast("Network error saving subscription", "error");
    } finally {
        saveBtn.disabled = false;
    }
}

async function editSubscription(id) {
    try {
        const res = await fetch(`/api/subscription/${id}`);
        const data = await res.json();
        if (!data.success || !data.subscription) return;
        const sub = data.subscription;

        document.getElementById("subscriptionId").value = sub.id;
        document.getElementById("subName").value = sub.name;
        document.getElementById("subAmount").value = sub.amount;
        document.getElementById("subCycle").value = sub.billing_cycle || "Monthly";
        document.getElementById("subNextDueDate").value = sub.next_due_date;
        if (sub.category_id) document.getElementById("subCategory").value = sub.category_id;
        if (sub.account_id) document.getElementById("subAccount").value = sub.account_id;
        document.getElementById("subNotes").value = sub.notes || "";

        document.getElementById("subscriptionModalTitle").textContent = "Edit Subscription";
        document.getElementById("saveSubBtnText").textContent = "Update Subscription";
        document.getElementById("subscriptionModal").classList.remove("hidden");
        document.body.classList.add("overflow-hidden");
    } catch (err) {
        showToast("Error retrieving subscription", "error");
    }
}

async function deleteSubscription(id) {
    if (!confirm("Are you sure you want to delete this subscription?")) return;
    try {
        const res = await fetch(`/api/subscription/${id}/delete`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Subscription deleted!");
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to delete subscription", "error");
        }
    } catch (err) {
        showToast("Network error", "error");
    }
}

async function paySubscriptionNow(id) {
    try {
        const res = await fetch(`/api/subscription/${id}/pay`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Bill recorded as expense & advanced!");
            setTimeout(() => window.location.reload(), 400);
        } else {
            showToast(data.error || "Failed to process payment", "error");
        }
    } catch (err) {
        showToast("Network error", "error");
    }
}

// --- 6. Financial Goals & Savings Pockets (v2.0) ---
function openAddGoalModal() {
    const modal = document.getElementById("goalModal");
    if (!modal) return;
    document.getElementById("goalForm").reset();
    document.getElementById("goalId").value = "";
    document.getElementById("goalColor").value = "#10B981";
    document.getElementById("goalColorLabel").textContent = "#10B981";
    document.getElementById("goalModalTitle").textContent = "Create Financial Goal";
    document.getElementById("saveGoalBtnText").textContent = "Save Goal";
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
}

function closeGoalModal() {
    const modal = document.getElementById("goalModal");
    if (modal) modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
}

async function handleGoalSubmit(e) {
    e.preventDefault();
    const saveBtn = document.getElementById("saveGoalBtn");
    saveBtn.disabled = true;

    const id = document.getElementById("goalId").value;
    const isEdit = Boolean(id);

    const payload = {
        name: document.getElementById("goalName").value.trim(),
        target_amount: parseFloat(document.getElementById("goalTargetAmount").value),
        current_amount: parseFloat(document.getElementById("goalCurrentAmount").value || 0),
        target_date: document.getElementById("goalTargetDate").value || null,
        account_id: document.getElementById("goalAccount")?.value || null,
        color: document.getElementById("goalColor").value,
        icon: document.getElementById("goalIcon").value,
        notes: document.getElementById("goalNotes").value.trim()
    };

    try {
        const url = isEdit ? `/api/goal/${id}` : "/api/goal";
        const method = isEdit ? "PUT" : "POST";

        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            showToast(data.message || "Goal saved!");
            closeGoalModal();
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to save goal", "error");
        }
    } catch (err) {
        showToast("Network error saving goal", "error");
    } finally {
        saveBtn.disabled = false;
    }
}

async function editGoal(id) {
    try {
        const res = await fetch(`/api/goal/${id}`);
        const data = await res.json();
        if (!data.success || !data.goal) return;
        const g = data.goal;

        document.getElementById("goalId").value = g.id;
        document.getElementById("goalName").value = g.name;
        document.getElementById("goalTargetAmount").value = g.target_amount;
        document.getElementById("goalCurrentAmount").value = g.current_amount;
        if (g.target_date) document.getElementById("goalTargetDate").value = g.target_date;
        if (g.account_id) document.getElementById("goalAccount").value = g.account_id;
        document.getElementById("goalColor").value = g.color || "#10B981";
        document.getElementById("goalColorLabel").textContent = g.color || "#10B981";
        document.getElementById("goalIcon").value = g.icon || "bullseye";
        document.getElementById("goalNotes").value = g.notes || "";

        document.getElementById("goalModalTitle").textContent = "Edit Goal";
        document.getElementById("saveGoalBtnText").textContent = "Update Goal";
        document.getElementById("goalModal").classList.remove("hidden");
        document.body.classList.add("overflow-hidden");
    } catch (err) {
        showToast("Error retrieving goal", "error");
    }
}

async function deleteGoal(id) {
    if (!confirm("Are you sure you want to delete this goal?")) return;
    try {
        const res = await fetch(`/api/goal/${id}/delete`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Goal deleted!");
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to delete goal", "error");
        }
    } catch (err) {
        showToast("Network error", "error");
    }
}

function openContributeModal(id, name, remaining) {
    const modal = document.getElementById("contributeModal");
    if (!modal) return;
    document.getElementById("contributeGoalId").value = id;
    document.getElementById("contributeGoalNameHeader").textContent = name;
    document.getElementById("contributeAmount").value = "";
    document.getElementById("contributeAmount").placeholder = `e.g. ${remaining > 0 ? remaining.toFixed(2) : '50.00'}`;
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
}

function closeContributeModal() {
    const modal = document.getElementById("contributeModal");
    if (modal) modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
}

async function handleContributeSubmit(e) {
    e.preventDefault();
    const id = document.getElementById("contributeGoalId").value;
    const amount = parseFloat(document.getElementById("contributeAmount").value);
    if (amount <= 0) {
        showToast("Contribution must be greater than zero", "error");
        return;
    }

    try {
        const res = await fetch(`/api/goal/${id}/contribute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount: amount })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Contribution recorded!");
            closeContributeModal();
            setTimeout(() => window.location.reload(), 350);
        } else {
            showToast(data.error || "Failed to contribute", "error");
        }
    } catch (err) {
        showToast("Network error", "error");
    }
}

// --- 7. Two-Factor Authentication Security (v2.0) ---
let current2faSecret = "";

function openTwoFactorModal() {
    const modal = document.getElementById("twoFactorModal");
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
    checkTwoFactorStatus();
}

function closeTwoFactorModal() {
    const modal = document.getElementById("twoFactorModal");
    modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
}

async function checkTwoFactorStatus() {
    const banner = document.getElementById("twoFactorStatusBanner");
    const setupStep = document.getElementById("twoFactorSetupStep");
    const disableStep = document.getElementById("twoFactorDisableStep");
    const initStep = document.getElementById("twoFactorInitStep");

    setupStep.classList.add("hidden");
    disableStep.classList.add("hidden");
    initStep.classList.add("hidden");

    try {
        const res = await fetch("/api/2fa/status");
        const data = await res.json();
        if (data.enabled) {
            banner.className = "p-3 rounded-xl text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 flex items-center justify-between";
            banner.innerHTML = `<span class="flex items-center space-x-1.5"><i class="fa-solid fa-circle-check text-emerald-500"></i><span>Status: 2FA Active & Protecting Account</span></span>`;
            disableStep.classList.remove("hidden");
        } else {
            banner.className = "p-3 rounded-xl text-xs font-semibold bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 flex items-center justify-between";
            banner.innerHTML = `<span class="flex items-center space-x-1.5"><i class="fa-solid fa-triangle-exclamation text-amber-500"></i><span>Status: 2FA Inactive (Recommended to Enable)</span></span>`;
            initStep.classList.remove("hidden");
        }
    } catch (err) {
        showToast("Failed to check 2FA status", "error");
    }
}

async function startSetup2FA() {
    document.getElementById("twoFactorInitStep").classList.add("hidden");
    const setupStep = document.getElementById("twoFactorSetupStep");
    setupStep.classList.remove("hidden");

    try {
        const res = await fetch("/api/2fa/setup", { method: "POST" });
        const data = await res.json();
        if (!data.success) {
            showToast("Failed to initialize 2FA", "error");
            return;
        }

        current2faSecret = data.secret;
        document.getElementById("twoFactorSecretText").value = data.secret;

        // Render QR Code using qrcode.js (on-demand loaded)
        if (!window.QRCode) {
            await new Promise((resolve) => {
                const s = document.createElement("script");
                s.src = "https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js";
                s.onload = resolve;
                s.onerror = resolve;
                document.head.appendChild(s);
            });
        }

        const canvasContainer = document.getElementById("twoFactorQrCodeCanvas");
        canvasContainer.innerHTML = "";
        if (window.QRCode) {
            new QRCode(canvasContainer, {
                text: data.uri,
                width: 170,
                height: 170,
                colorDark: "#0F172A",
                colorLight: "#FFFFFF",
                correctLevel: QRCode.CorrectLevel.M
            });
        }
    } catch (err) {
        showToast("Error generating 2FA credentials", "error");
    }
}

function copyTwoFactorSecret() {
    const text = document.getElementById("twoFactorSecretText").value;
    navigator.clipboard.writeText(text).then(() => {
        showToast("Secret key copied to clipboard!");
    });
}

async function confirmEnable2FA() {
    const code = document.getElementById("twoFactorVerifyInput").value.trim();
    if (!code || code.length !== 6) {
        showToast("Enter a valid 6-digit verification code", "error");
        return;
    }

    try {
        const res = await fetch("/api/2fa/verify-and-enable", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ secret: current2faSecret, code: code })
        });
        const data = await res.json();
        if (data.success) {
            showToast("2FA successfully enabled!");
            checkTwoFactorStatus();
        } else {
            showToast(data.error || "Verification failed. Check your authenticator app.", "error");
        }
    } catch (err) {
        showToast("Network error verifying 2FA", "error");
    }
}

async function disable2FA() {
    if (!confirm("Are you sure you want to disable Two-Factor Authentication?")) return;
    try {
        const res = await fetch("/api/2fa/disable", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Two-Factor Authentication disabled");
            checkTwoFactorStatus();
        } else {
            showToast(data.error || "Failed to disable 2FA", "error");
        }
    } catch (err) {
        showToast("Network error", "error");
    }
}


// ==================== 8. DEBTS, LOANS & PEER CREDIT ====================

let currentRepaymentMax = 0;

function openAddDebtModal() {
    const modal = document.getElementById("debtModal");
    if (!modal) return;
    document.getElementById("debtForm").reset();
    document.getElementById("debtId").value = "";
    document.getElementById("debtModalTitle").textContent = "Add Credit, Loan or Card";
    document.getElementById("saveDebtBtn").textContent = "Save Record";
    
    // Default to friend_lent
    const firstRadio = document.querySelector('input[name="debt_type"][value="friend_lent"]');
    if (firstRadio) firstRadio.checked = true;

    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
}

async function openEditDebtModal(debtId) {
    const modal = document.getElementById("debtModal");
    if (!modal) return;
    
    try {
        const res = await fetch(`/api/debt/${debtId}`);
        const data = await res.json();
        if (!data.success) {
            showToast(data.error || "Failed to load record", "error");
            return;
        }

        const d = data.debt;
        document.getElementById("debtId").value = d.id;
        document.getElementById("debtModalTitle").textContent = "Edit Credit / Loan Record";
        document.getElementById("saveDebtBtn").textContent = "Update Record";

        // Set radio type
        const radio = document.querySelector(`input[name="debt_type"][value="${d.debt_type}"]`);
        if (radio) radio.checked = true;

        document.getElementById("debtPerson").value = d.person_or_institution;
        document.getElementById("debtTotalAmount").value = d.total_amount;
        document.getElementById("debtPaidAmount").value = d.paid_amount;
        document.getElementById("debtDueDate").value = d.due_date || "";
        document.getElementById("debtInterestRate").value = d.interest_rate || "";
        document.getElementById("debtAccountId").value = d.account_id || "";
        document.getElementById("debtNotes").value = d.notes || "";

        modal.classList.remove("hidden");
        document.body.classList.add("overflow-hidden");
    } catch (err) {
        showToast("Error loading debt details", "error");
    }
}

function closeDebtModal() {
    const modal = document.getElementById("debtModal");
    if (modal) {
        modal.classList.add("hidden");
        document.body.classList.remove("overflow-hidden");
    }
}

async function handleDebtSubmit(event) {
    event.preventDefault();
    const btn = document.getElementById("saveDebtBtn");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Saving...`;

    const debtId = document.getElementById("debtId").value;
    const debtType = document.querySelector('input[name="debt_type"]:checked').value;
    const person = document.getElementById("debtPerson").value.trim();
    const totalAmount = parseFloat(document.getElementById("debtTotalAmount").value) || 0;
    const paidAmount = parseFloat(document.getElementById("debtPaidAmount").value) || 0;
    const dueDate = document.getElementById("debtDueDate").value || null;
    const interestRate = parseFloat(document.getElementById("debtInterestRate").value) || 0;
    const accountId = document.getElementById("debtAccountId").value || null;
    const notes = document.getElementById("debtNotes").value.trim();

    const payload = {
        debt_type: debtType,
        person_or_institution: person,
        total_amount: totalAmount,
        paid_amount: paidAmount,
        interest_rate: interestRate,
        due_date: dueDate,
        account_id: accountId,
        notes: notes
    };

    try {
        const url = debtId ? `/api/debt/${debtId}` : "/api/debt";
        const method = debtId ? "PUT" : "POST";
        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || "Record saved successfully!");
            closeDebtModal();
            setTimeout(() => window.location.reload(), 500);
        } else {
            showToast(data.error || "Failed to save record", "error");
        }
    } catch (err) {
        showToast("Network error saving record", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = debtId ? "Update Record" : "Save Record";
    }
}

async function deleteDebt(debtId, personName) {
    if (!confirm(`Are you sure you want to delete the debt record for "${personName}"? This will also remove its repayment history.`)) return;

    try {
        const res = await fetch(`/api/debt/${debtId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.success) {
            showToast("Record deleted successfully");
            setTimeout(() => window.location.reload(), 500);
        } else {
            showToast(data.error || "Failed to delete record", "error");
        }
    } catch (err) {
        showToast("Network error deleting record", "error");
    }
}

function openDebtPaymentModal(debtId, personName, remainingAmount, direction, accountId) {
    const modal = document.getElementById("debtPaymentModal");
    if (!modal) return;

    document.getElementById("debtPaymentForm").reset();
    document.getElementById("paymentDebtId").value = debtId;
    document.getElementById("paymentDirection").value = direction;
    currentRepaymentMax = parseFloat(remainingAmount) || 0;

    document.getElementById("paymentPersonName").textContent = personName;
    document.getElementById("paymentRemainingAmount").textContent = `${window.CURRENCY_SYMBOL || '$'}${currentRepaymentMax.toFixed(2)}`;

    const sym = window.CURRENCY_SYMBOL || '$';
    if (direction === "receivable") {
        document.getElementById("paymentModalTitle").textContent = "Record Payment Received";
        document.getElementById("paymentDirectionText").textContent = "Money received from friend towards balance";
        document.getElementById("paymentAccountLabel").textContent = "Deposit Into Bank Account";
        document.getElementById("submitPaymentBtn").innerHTML = `<i class="fa-solid fa-arrow-down-to-bracket mr-1.5"></i> Confirm Deposit`;
    } else {
        document.getElementById("paymentModalTitle").textContent = "Record Repayment";
        document.getElementById("paymentDirectionText").textContent = "Repaying money you owe";
        document.getElementById("paymentAccountLabel").textContent = "Pay From Bank Account";
        document.getElementById("submitPaymentBtn").innerHTML = `<i class="fa-solid fa-money-bill-transfer mr-1.5"></i> Confirm Repayment`;
    }

    document.getElementById("paymentAmount").max = currentRepaymentMax;
    document.getElementById("paymentAmount").value = "";
    document.getElementById("paymentDate").value = new Date().toISOString().split("T")[0];
    
    if (accountId) {
        document.getElementById("paymentAccountId").value = accountId;
    }

    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
}

function fillFullPaymentAmount() {
    if (currentRepaymentMax > 0) {
        document.getElementById("paymentAmount").value = currentRepaymentMax.toFixed(2);
    }
}

function closeDebtPaymentModal() {
    const modal = document.getElementById("debtPaymentModal");
    if (modal) {
        modal.classList.add("hidden");
        document.body.classList.remove("overflow-hidden");
    }
}

async function handleDebtPaymentSubmit(event) {
    event.preventDefault();
    const debtId = document.getElementById("paymentDebtId").value;
    const amount = parseFloat(document.getElementById("paymentAmount").value) || 0;
    const paymentDate = document.getElementById("paymentDate").value;
    const accountId = document.getElementById("paymentAccountId").value || null;
    const recordInAccount = document.getElementById("paymentRecordInAccount").checked ? 1 : 0;
    const notes = document.getElementById("paymentNotes").value.trim();

    if (amount <= 0) {
        showToast("Please enter a payment amount greater than zero", "error");
        return;
    }

    const btn = document.getElementById("submitPaymentBtn");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Processing...`;

    try {
        const res = await fetch(`/api/debt/${debtId}/payment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                amount: amount,
                payment_date: paymentDate,
                account_id: accountId,
                record_in_account: recordInAccount,
                notes: notes
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || "Repayment recorded successfully!");
            closeDebtPaymentModal();
            setTimeout(() => window.location.reload(), 500);
        } else {
            showToast(data.error || "Failed to record payment", "error");
        }
    } catch (err) {
        showToast("Network error recording payment", "error");
    } finally {
        btn.disabled = false;
    }
}


// ==================== MOBILE NAVIGATION & QUICK ACTIONS ====================

function toggleMobileDrawer(forceState = null) {
    const drawer = document.getElementById("mobileDrawer");
    const backdrop = document.getElementById("mobileDrawerBackdrop");
    if (!drawer || !backdrop) return;
    const isOpening = forceState !== null ? forceState : drawer.classList.contains("-translate-x-full");
    if (isOpening) {
        backdrop.classList.remove("hidden");
        setTimeout(() => drawer.classList.remove("-translate-x-full"), 10);
    } else {
        drawer.classList.add("-translate-x-full");
        setTimeout(() => backdrop.classList.add("hidden"), 250);
    }
}

function toggleQuickAddSheet(forceState = null) {
    const sheet = document.getElementById("mobileQuickAddSheet");
    const backdrop = document.getElementById("mobileQuickAddBackdrop");
    const fabIcon = document.getElementById("quickAddFabIcon");
    if (!sheet) {
        openAddExpenseModal();
        return;
    }
    const isOpening = forceState !== null ? forceState : sheet.classList.contains("pointer-events-none");
    if (isOpening) {
        if (backdrop) backdrop.classList.remove("hidden");
        sheet.classList.remove("pointer-events-none", "opacity-0", "scale-95");
        sheet.classList.add("opacity-100", "scale-100");
        if (fabIcon) fabIcon.style.transform = "rotate(45deg)";
    } else {
        sheet.classList.remove("opacity-100", "scale-100");
        sheet.classList.add("pointer-events-none", "opacity-0", "scale-95");
        if (backdrop) backdrop.classList.add("hidden");
        if (fabIcon) fabIcon.style.transform = "rotate(0deg)";
    }
}

// Global Keyboard Escape Handler
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        if (typeof closeExpenseModal === "function") closeExpenseModal();
        if (typeof closeIncomeModal === "function") closeIncomeModal();
        if (typeof closeTransferModal === "function") closeTransferModal();
        if (typeof closeCategoryModal === "function") closeCategoryModal();
        if (typeof closeMonthlyBudgetModal === "function") closeMonthlyBudgetModal();
        if (typeof closeImportModal === "function") closeImportModal();
        if (typeof closeTwoFactorModal === "function") closeTwoFactorModal();
        if (typeof closeSubscriptionModal === "function") closeSubscriptionModal();
        if (typeof closeGoalModal === "function") closeGoalModal();
        if (typeof closeGoalContributionModal === "function") closeGoalContributionModal();
        if (typeof closeDebtModal === "function") closeDebtModal();
        if (typeof closeDebtPaymentModal === "function") closeDebtPaymentModal();
        toggleMobileDrawer(false);
        toggleQuickAddSheet(false);
    }
});
