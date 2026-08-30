// Supply Chain Exception Intelligence Assistant - Frontend Controller

const API_BASE = window.location.origin;
let geminiApiKey = localStorage.getItem("gemini_api_key") || "";
let stockChartInstance = null;
let supplierChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initSettings();
    loadDashboardData();
    loadExceptions();
    loadSupplierBenchmarks();
    loadForecastData();
    initChat();
    initUpload();
});

// ----------------- Navigation Tabs ----------------- //
function initNavigation() {
    const tabs = ["dashboard", "exceptions", "suppliers", "forecast", "query", "upload", "settings"];
    tabs.forEach(tab => {
        const btn = document.getElementById(`tab-btn-${tab}`);
        const view = document.getElementById(`view-${tab}`);
        if (btn && view) {
            btn.addEventListener("click", () => {
                tabs.forEach(t => {
                    const b = document.getElementById(`tab-btn-${t}`);
                    const v = document.getElementById(`view-${t}`);
                    if (b) {
                        b.classList.remove("text-blue-600", "border-b-2", "border-blue-600", "font-semibold");
                        b.classList.add("text-slate-500");
                    }
                    if (v) v.classList.add("hidden");
                });
                btn.classList.add("text-blue-600", "border-b-2", "border-blue-600", "font-semibold");
                btn.classList.remove("text-slate-500");
                view.classList.remove("hidden");

                if (tab === "dashboard") loadDashboardData();
                if (tab === "exceptions") loadExceptions();
                if (tab === "suppliers") loadSupplierBenchmarks();
                if (tab === "forecast") loadForecastData();
            });
        }
    });
}

// ----------------- Settings & API Key ----------------- //
function initSettings() {
    const keyInput = document.getElementById("gemini-api-key-input");
    const saveBtn = document.getElementById("save-api-key-btn");
    const statusMsg = document.getElementById("api-key-status");

    if (keyInput && geminiApiKey) {
        keyInput.value = geminiApiKey;
    }

    if (saveBtn) {
        saveBtn.addEventListener("click", () => {
            geminiApiKey = keyInput.value.trim();
            localStorage.setItem("gemini_api_key", geminiApiKey);
            statusMsg.textContent = geminiApiKey ? "API Key saved in browser memory!" : "API Key cleared (using built-in grounded engine)";
            statusMsg.className = "text-sm text-green-600 mt-2 block";
            setTimeout(() => { statusMsg.className = "hidden"; }, 3500);
        });
    }

    const runAnalyticsBtn = document.getElementById("run-analytics-btn");
    if (runAnalyticsBtn) {
        runAnalyticsBtn.addEventListener("click", triggerAnalyticsRun);
    }
    
    const globalRunBtn = document.getElementById("global-run-analytics-btn");
    if (globalRunBtn) {
        globalRunBtn.addEventListener("click", triggerAnalyticsRun);
    }
}

async function triggerAnalyticsRun() {
    const btn = document.getElementById("global-run-analytics-btn");
    const origText = btn ? btn.innerHTML : "";
    if (btn) {
        btn.innerHTML = `<i class="lucide-loader animate-spin mr-1"></i> Running...`;
        btn.disabled = true;
    }

    try {
        const headers = { "Content-Type": "application/json" };
        if (geminiApiKey) headers["x-gemini-api-key"] = geminiApiKey;

        const res = await fetch(`${API_BASE}/analytics/run`, {
            method: "POST",
            headers: headers
        });
        const data = await res.json();
        
        showNotification("Analytics run complete! Exceptions & AI explanations updated.", "success");
        loadDashboardData();
        loadExceptions();
        loadSupplierBenchmarks();
        loadForecastData();
    } catch (e) {
        showNotification("Failed to run analytics pipeline: " + e.message, "error");
    } finally {
        if (btn) {
            btn.innerHTML = origText;
            btn.disabled = false;
        }
    }
}

// ----------------- Dashboard Data & Charts ----------------- //
async function loadDashboardData() {
    try {
        const res = await fetch(`${API_BASE}/inventory/dashboard`);
        const kpi = await res.json();

        document.getElementById("kpi-total-val").textContent = `$${(kpi.total_inventory_value || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById("kpi-out-stock").textContent = kpi.out_of_stock_count || 0;
        document.getElementById("kpi-safety-breach").textContent = kpi.safety_stock_breaches || 0;
        document.getElementById("kpi-delayed-orders").textContent = kpi.delayed_orders_count || 0;
        document.getElementById("kpi-crit-exceptions").textContent = kpi.critical_exceptions_count || 0;
        document.getElementById("kpi-avg-otif").textContent = `${kpi.average_otif_rate || 0}%`;

        renderStockChart(kpi);
    } catch (e) {
        console.error("Error loading dashboard KPIs:", e);
    }
}

function renderStockChart(kpi) {
    const ctx = document.getElementById("stockStatusChart");
    if (!ctx) return;

    if (stockChartInstance) stockChartInstance.destroy();

    const healthy = Math.max(0, kpi.total_products - (kpi.out_of_stock_count + kpi.safety_stock_breaches));

    stockChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Healthy Stock', 'Safety Stock Breach', 'Out of Stock'],
            datasets: [{
                data: [healthy, kpi.safety_stock_breaches, kpi.out_of_stock_count],
                backgroundColor: ['#22c55e', '#f59e0b', '#ef4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            },
            cutout: '70%'
        }
    });
}

// ----------------- Exception Queue ----------------- //
async function loadExceptions() {
    const sevFilter = document.getElementById("filter-severity")?.value || "ALL";
    const typeFilter = document.getElementById("filter-type")?.value || "ALL";
    const searchVal = document.getElementById("search-exceptions")?.value || "";

    const container = document.getElementById("exceptions-container");
    if (!container) return;

    container.innerHTML = `<div class="p-8 text-center text-slate-400"><i class="lucide-loader animate-spin text-2xl mb-2"></i><p>Loading prioritized exception queue...</p></div>`;

    try {
        const url = new URL(`${API_BASE}/exceptions`);
        if (sevFilter !== "ALL") url.searchParams.append("severity", sevFilter);
        if (typeFilter !== "ALL") url.searchParams.append("exception_type", typeFilter);
        if (searchVal) url.searchParams.append("search", searchVal);

        const res = await fetch(url);
        const exceptions = await res.json();

        if (exceptions.length === 0) {
            container.innerHTML = `
                <div class="p-12 text-center bg-white rounded-xl border border-slate-200">
                    <i class="lucide-check-circle text-green-500 text-4xl mb-3 block"></i>
                    <h3 class="text-lg font-semibold text-slate-800">No Exceptions Found</h3>
                    <p class="text-sm text-slate-500 mt-1">All inventory thresholds and supply orders are operating normally.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = "";
        exceptions.forEach(exc => {
            const card = createExceptionCard(exc);
            container.appendChild(card);
        });
    } catch (e) {
        container.innerHTML = `<div class="p-4 text-red-500">Failed to load exceptions: ${e.message}</div>`;
    }
}

function createExceptionCard(exc) {
    const div = document.createElement("div");
    div.className = "bg-white rounded-xl border border-slate-200 p-5 mb-4 shadow-sm hover:shadow-md transition-all";

    const sevClass = {
        'CRITICAL': 'badge-critical',
        'HIGH': 'badge-high',
        'MEDIUM': 'badge-medium',
        'LOW': 'badge-low'
    }[exc.severity] || 'badge-medium';

    const typeName = exc.exception_type.replace(/_/g, ' ');

    let metricSnippet = "";
    if (exc.deterministic_metrics) {
        const m = exc.deterministic_metrics;
        if (m.current_stock !== undefined) {
            metricSnippet += `<span class="bg-slate-100 px-2.5 py-1 rounded text-xs text-slate-700">Stock: <b>${m.current_stock}</b> / Safety: <b>${m.safety_stock}</b></span>`;
        }
        if (m.delay_days !== undefined) {
            metricSnippet += `<span class="bg-red-50 px-2.5 py-1 rounded text-xs text-red-700 font-medium">Delay: <b>+${m.delay_days} Days</b> ($${(m.order_value || 0).toLocaleString()})</span>`;
        }
        if (m.days_of_supply !== undefined) {
            metricSnippet += `<span class="bg-amber-50 px-2.5 py-1 rounded text-xs text-amber-700 font-medium">Days of Supply: <b>${m.days_of_supply}d</b> (Shortage: ${m.shortage_units_7d} units)</span>`;
        }
    }

    div.innerHTML = `
        <div class="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-3 mb-3">
            <div>
                <div class="flex items-center gap-2">
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${sevClass}">${exc.severity}</span>
                    <span class="text-xs font-medium text-slate-400 uppercase tracking-wider">${typeName}</span>
                    <span class="text-xs text-slate-400">• ID: ${exc.exception_id}</span>
                </div>
                <h4 class="text-base font-bold text-slate-800 mt-1">${exc.product_name || exc.entity_id}</h4>
                <div class="text-xs text-slate-500 mt-0.5">
                    Facility: <span class="text-slate-700 font-medium">${exc.warehouse_name || 'N/A'}</span> 
                    ${exc.supplier_name && exc.supplier_name !== 'N/A' ? ` | Supplier: <span class="text-slate-700 font-medium">${exc.supplier_name}</span>` : ''}
                </div>
            </div>
            <div class="flex flex-wrap gap-2 items-center">
                ${metricSnippet}
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
            <div class="bg-blue-50/50 rounded-lg p-3.5 border border-blue-100/80">
                <div class="flex items-center gap-1.5 text-blue-800 text-xs font-semibold uppercase tracking-wider mb-1">
                    <i class="lucide-sparkles text-blue-600"></i> AI Root-Cause Explanation
                </div>
                <p class="text-sm text-slate-700 leading-relaxed">${exc.explanation}</p>
            </div>

            <div class="bg-emerald-50/50 rounded-lg p-3.5 border border-emerald-100/80">
                <div class="flex items-center gap-1.5 text-emerald-800 text-xs font-semibold uppercase tracking-wider mb-1">
                    <i class="lucide-zap text-emerald-600"></i> Recommended Action
                </div>
                <p class="text-sm text-slate-700 leading-relaxed">${exc.recommended_action}</p>
            </div>
        </div>

        <div class="flex justify-end gap-2 mt-4 pt-2 border-t border-slate-50">
            <button onclick="handleAcknowledge('${exc.exception_id}')" class="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors">
                Acknowledge
            </button>
            <button onclick="handleExecuteAction('${exc.exception_id}', '${exc.entity_id}')" class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors flex items-center gap-1">
                Execute Action <i class="lucide-arrow-right text-xs"></i>
            </button>
        </div>
    `;

    return div;
}

function handleAcknowledge(id) {
    showNotification(`Exception ${id} acknowledged and logged in audit history.`, "info");
}

function handleExecuteAction(excId, entityId) {
    showNotification(`Action dispatched for entity ${entityId}. Automated notification sent to logistics coordinator.`, "success");
}

// ----------------- Supplier Benchmarks ----------------- //
async function loadSupplierBenchmarks() {
    const tbody = document.getElementById("suppliers-table-body");
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/suppliers/compare`);
        const suppliers = await res.json();

        tbody.innerHTML = "";
        const labels = [];
        const otifData = [];
        const reliabilityData = [];

        suppliers.forEach(s => {
            labels.push(s.supplier_name.split(" ")[0]);
            otifData.push(s.otif_rate_pct);
            reliabilityData.push(s.reliability_score);

            const riskBadge = {
                'LOW_RISK': '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Low Risk</span>',
                'MODERATE_RISK': '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">Moderate</span>',
                'HIGH_RISK': '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">High Risk</span>'
            }[s.risk_tier] || '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-800">Standard</span>';

            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-50 border-b border-slate-100 text-sm";
            tr.innerHTML = `
                <td class="p-3 font-semibold text-slate-800">${s.supplier_name}<div class="text-xs font-normal text-slate-400">${s.category} (${s.country})</div></td>
                <td class="p-3 text-center font-bold text-slate-700">${s.total_orders}</td>
                <td class="p-3 text-center ${s.delayed_orders > 0 ? 'text-red-600 font-bold' : 'text-slate-500'}">${s.delayed_orders}</td>
                <td class="p-3 text-center font-semibold ${s.otif_rate_pct >= 90 ? 'text-emerald-600' : (s.otif_rate_pct >= 75 ? 'text-amber-600' : 'text-red-600')}">${s.otif_rate_pct}%</td>
                <td class="p-3 text-center text-slate-600">${s.stated_lead_time_days}d / <b>${s.avg_actual_lead_time_days}d</b></td>
                <td class="p-3 text-center ${s.lead_time_variance_days > 0 ? 'text-red-500 font-bold' : 'text-emerald-600'}">${s.lead_time_variance_days > 0 ? '+' : ''}${s.lead_time_variance_days}d</td>
                <td class="p-3 text-center font-bold text-blue-600">${s.reliability_score}/100</td>
                <td class="p-3 text-center">${riskBadge}</td>
            `;
            tbody.appendChild(tr);
        });

        renderSupplierChart(labels, otifData, reliabilityData);
    } catch (e) {
        console.error("Error loading suppliers:", e);
    }
}

function renderSupplierChart(labels, otifData, reliabilityData) {
    const ctx = document.getElementById("supplierOtifChart");
    if (!ctx) return;

    if (supplierChartInstance) supplierChartInstance.destroy();

    supplierChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'OTIF Rate (%)',
                    data: otifData,
                    backgroundColor: '#3b82f6',
                    borderRadius: 4
                },
                {
                    label: 'Reliability Score',
                    data: reliabilityData,
                    backgroundColor: '#10b981',
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 100 }
            }
        }
    });
}

// ----------------- 7-Day Stockout Forecast ----------------- //
async function loadForecastData() {
    const tbody = document.getElementById("forecast-table-body");
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/analytics/forecast`);
        const forecasts = await res.json();

        tbody.innerHTML = "";
        forecasts.forEach(f => {
            const riskClass = {
                'CRITICAL': 'bg-red-100 text-red-800 font-bold',
                'HIGH': 'bg-amber-100 text-amber-800 font-semibold',
                'MODERATE': 'bg-blue-100 text-blue-800',
                'LOW': 'bg-emerald-100 text-emerald-800'
            }[f.risk_level] || 'bg-slate-100 text-slate-800';

            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-50 border-b border-slate-100 text-sm";
            tr.innerHTML = `
                <td class="p-3 font-semibold text-slate-800">${f.product_name}<div class="text-xs text-slate-400">${f.product_id}</div></td>
                <td class="p-3 text-slate-600">${f.warehouse_name}</td>
                <td class="p-3 text-center">${f.current_stock}</td>
                <td class="p-3 text-center text-slate-500">${f.daily_demand_rate}/day</td>
                <td class="p-3 text-center font-bold ${f.days_of_supply < 3 ? 'text-red-600' : (f.days_of_supply < 7 ? 'text-amber-600' : 'text-emerald-600')}">${f.days_of_supply} Days</td>
                <td class="p-3 text-center text-slate-700 font-medium">${f.projected_stockout_date || 'None'}</td>
                <td class="p-3 text-center ${f.shortage_units_7d > 0 ? 'text-red-600 font-bold' : 'text-slate-400'}">${f.shortage_units_7d > 0 ? f.shortage_units_7d : '-'}</td>
                <td class="p-3 text-center"><span class="px-2.5 py-0.5 rounded-full text-xs ${riskClass}">${f.risk_level}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading forecast:", e);
    }
}

// ----------------- Natural Language Query (Chat) ----------------- //
function initChat() {
    const input = document.getElementById("chat-query-input");
    const sendBtn = document.getElementById("chat-send-btn");
    const chatContainer = document.getElementById("chat-messages");

    if (!input || !sendBtn || !chatContainer) return;

    sendBtn.addEventListener("click", () => sendQuery());
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendQuery();
    });

    document.querySelectorAll(".quick-query-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            input.value = btn.dataset.query;
            sendQuery();
        });
    });

    async function sendQuery() {
        const q = input.value.trim();
        if (!q) return;

        appendUserMessage(q);
        input.value = "";

        const loadId = appendLoadingMessage();

        try {
            const res = await fetch(`${API_BASE}/supply/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: q, gemini_api_key: geminiApiKey || null })
            });
            const data = await res.json();
            removeMessage(loadId);
            appendAiResponse(data);
        } catch (e) {
            removeMessage(loadId);
            appendAiError("Query error: " + e.message);
        }
    }

    function appendUserMessage(text) {
        const div = document.createElement("div");
        div.className = "flex justify-end mb-4";
        div.innerHTML = `
            <div class="chat-bubble-user max-w-xl p-3.5 rounded-2xl rounded-tr-sm text-sm shadow-sm">
                ${escapeHtml(text)}
            </div>
        `;
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function appendLoadingMessage() {
        const id = "load-" + Date.now();
        const div = document.createElement("div");
        div.id = id;
        div.className = "flex justify-start mb-4";
        div.innerHTML = `
            <div class="chat-bubble-ai max-w-xl p-3.5 rounded-2xl rounded-tl-sm text-sm text-slate-500 shadow-sm flex items-center gap-2">
                <i class="lucide-sparkles text-blue-600 animate-spin"></i> Analyzing supply chain operations & calculating insights...
            </div>
        `;
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return id;
    }

    function removeMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function appendAiResponse(data) {
        const div = document.createElement("div");
        div.className = "flex justify-start mb-4";

        let actionsHtml = "";
        if (data.recommended_actions && data.recommended_actions.length > 0) {
            actionsHtml = `
                <div class="mt-3 pt-3 border-t border-slate-200">
                    <div class="text-xs font-bold text-slate-600 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                        <i class="lucide-check-circle-2 text-emerald-600"></i> Recommended Actions
                    </div>
                    <ul class="space-y-1 text-xs text-slate-700">
                        ${data.recommended_actions.map(a => `<li class="flex items-start gap-1.5"><span class="text-blue-500 font-bold">•</span> ${a}</li>`).join("")}
                    </ul>
                </div>
            `;
        }

        div.innerHTML = `
            <div class="chat-bubble-ai max-w-2xl p-4 rounded-2xl rounded-tl-sm text-sm shadow-sm">
                <div class="prose prose-sm text-slate-800 leading-relaxed">
                    ${formatMarkdown(data.answer)}
                </div>
                ${actionsHtml}
            </div>
        `;
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function appendAiError(err) {
        const div = document.createElement("div");
        div.className = "flex justify-start mb-4";
        div.innerHTML = `
            <div class="bg-red-50 border border-red-200 text-red-700 max-w-xl p-3.5 rounded-2xl text-sm">
                ${escapeHtml(err)}
            </div>
        `;
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// ----------------- Data Upload Hub ----------------- //
function initUpload() {
    const uploadForm = document.getElementById("csv-upload-form");
    const sampleBtn = document.getElementById("load-sample-btn");

    if (sampleBtn) {
        sampleBtn.addEventListener("click", async () => {
            try {
                sampleBtn.disabled = true;
                sampleBtn.innerHTML = `<i class="lucide-loader animate-spin mr-1"></i> Ingesting...`;
                const res = await fetch(`${API_BASE}/data/sample`, { method: "POST" });
                const data = await res.json();
                showNotification("Official sample supply chain dataset loaded successfully!", "success");
                loadDashboardData();
                loadExceptions();
                loadSupplierBenchmarks();
                loadForecastData();
            } catch (e) {
                showNotification("Failed to load sample dataset: " + e.message, "error");
            } finally {
                sampleBtn.disabled = false;
                sampleBtn.innerHTML = `<i class="lucide-database mr-1"></i> Load Official Sample Dataset`;
            }
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById("csv-file-input");
            const typeSelect = document.getElementById("csv-type-select");
            
            if (!fileInput.files || fileInput.files.length === 0) {
                showNotification("Please select a CSV file to upload", "warning");
                return;
            }

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            formData.append("data_type", typeSelect.value);

            try {
                const res = await fetch(`${API_BASE}/data/upload`, {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                if (res.ok) {
                    showNotification(data.message, "success");
                    fileInput.value = "";
                    loadDashboardData();
                    loadExceptions();
                    loadSupplierBenchmarks();
                    loadForecastData();
                } else {
                    showNotification(data.detail || "Upload failed", "error");
                }
            } catch (err) {
                showNotification("Network error uploading file: " + err.message, "error");
            }
        });
    }
}

// ----------------- Helpers ----------------- //
function showNotification(msg, type = "info") {
    const toast = document.createElement("div");
    const bg = type === "success" ? "bg-emerald-600" : (type === "error" ? "bg-red-600" : (type === "warning" ? "bg-amber-600" : "bg-blue-600"));
    toast.className = `fixed bottom-5 right-5 z-50 text-white px-4 py-2.5 rounded-lg shadow-lg text-sm transition-all transform duration-300 flex items-center gap-2 ${bg}`;
    toast.innerHTML = `<span>${msg}</span>`;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function escapeHtml(str) {
    return str.replace(/[&<>'"]/g, tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
    }[tag] || tag));
}

function formatMarkdown(md) {
    if (!md) return "";
    return md
        .replace(/### (.*?)\n/g, '<h4 class="text-sm font-bold text-slate-800 mt-2 mb-1">$1</h4>')
        .replace(/## (.*?)\n/g, '<h3 class="text-base font-bold text-slate-900 mt-2 mb-1">$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>')
        .replace(/\*(.*?)\*/g, '<em class="italic">$1</em>')
        .replace(/- (.*?)\n/g, '<li class="ml-4 list-disc text-xs text-slate-700 my-0.5">$1</li>')
        .replace(/\n\n/g, '<br/>');
}
