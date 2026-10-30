"use strict";

/* ============================================================
   NAVUKOUKA ANALYTICS
   ============================================================ */

const API_BASE = "http://127.0.0.1:8001/api";

let analyticsData = null;
let currentMode = "all";

let charts = {
    target: null,
    overviewProbability: null,
    feature: null,
    calibration: null,
    missing: null
};

const elements = {};


/* ============================================================
   INIT
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
    cacheElements();
    setupAuth();
    setupModeButtons();
    setupModelSelect();
    setupFeatureSelect();
    loadModels();
});


/* ============================================================
   CACHE
   ============================================================ */

function cacheElements() {
    elements.logoutButton = document.getElementById("logoutButton");
    elements.authLink = document.getElementById("authLink");
    elements.modelSelect = document.getElementById("modelSelect");
    elements.modelStatusText = document.getElementById("modelStatusText");
    elements.analyticsError = document.getElementById("analyticsError");
    elements.analyticsDashboard = document.getElementById("analyticsDashboard");
    elements.analyticsLoading = document.getElementById("analyticsLoading");
    elements.analyticsEmpty = document.getElementById("analyticsEmpty");

    elements.overviewSection = document.getElementById("overviewSection");
    elements.conversionSection = document.getElementById("conversionSection");
    elements.segmentsSection = document.getElementById("segmentsSection");
    elements.calibrationSection = document.getElementById("calibrationSection");
    elements.insightsSection = document.getElementById("insightsSection");

    elements.overviewDescription = document.getElementById("overviewDescription");
    elements.metricRows = document.getElementById("metricRows");
    elements.metricConversion = document.getElementById("metricConversion");
    elements.metricPredictions = document.getElementById("metricPredictions");
    elements.metricTopShare = document.getElementById("metricTopShare");

    elements.overviewPredictionChartCard = document.getElementById("overviewPredictionChartCard");

    elements.featureSelect = document.getElementById("featureSelect");
    elements.featureDescription = document.getElementById("featureDescription");
    elements.featureGroups = document.getElementById("featureGroups");
    elements.featureBestGroup = document.getElementById("featureBestGroup");
    elements.featureBestConversion = document.getElementById("featureBestConversion");
    elements.featureAverageConversion = document.getElementById("featureAverageConversion");
    elements.featureChartTitle = document.getElementById("featureChartTitle");
    elements.featureChartDescription = document.getElementById("featureChartDescription");

    elements.segmentTableBody = document.getElementById("segmentTableBody");
    elements.segmentEmpty = document.getElementById("segmentEmpty");

    elements.featureTableBody = document.getElementById("featureTableBody");
    elements.insightsList = document.getElementById("insightsList");
}


/* ============================================================
   AUTH
   ============================================================ */

function setupAuth() {
    const token = sessionStorage.getItem("access_token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    if (elements.authLink) elements.authLink.style.display = "none";

    if (elements.logoutButton) {
        elements.logoutButton.addEventListener("click", () => {
            sessionStorage.removeItem("access_token");
            window.location.href = "login.html";
        });
    }
}


/* ============================================================
   MODES
   ============================================================ */

function setupModeButtons() {
    const buttons = document.querySelectorAll(".analytics-mode-card");
    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            currentMode = button.dataset.mode || "all";
            buttons.forEach((item) => {
                item.classList.toggle("active", item === button);
                item.setAttribute(
                    "aria-pressed",
                    item === button ? "true" : "false"
                );
            });
            renderMode();
        });
    });
}


/* ============================================================
   MODEL SELECT
   ============================================================ */

function setupModelSelect() {
    if (!elements.modelSelect) return;
    elements.modelSelect.addEventListener("change", async () => {
        const modelId = elements.modelSelect.value;
        if (!modelId) return;
        await loadAnalytics(modelId);
    });
}


/* ============================================================
   FEATURE SELECT
   ============================================================ */

function setupFeatureSelect() {
    if (!elements.featureSelect) return;
    elements.featureSelect.addEventListener("change", () => {
        const name = elements.featureSelect.value;
        if (!name || !analyticsData) return;
        renderFeatureConversion(name);
    });
}


/* ============================================================
   LOAD MODELS
   ============================================================ */

async function loadModels() {
    showLoading(true);
    hideError();

    try {
        const token = sessionStorage.getItem("access_token");
        const response = await fetch(`${API_BASE}/models`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorText = await getResponseError(response);
            throw new Error(errorText || "Не удалось получить список моделей.");
        }

        const data = await response.json();
        const models = Array.isArray(data)
            ? data
            : Array.isArray(data.items)
                ? data.items
                : [];

        populateModels(models);

        if (models.length === 0) {
            showNoModels();
            return;
        }

        hideNoModels();
        const firstModelId = getModelId(models[0]);
        if (!firstModelId) {
            throw new Error("В ответе сервера не найден идентификатор модели.");
        }

        elements.modelSelect.value = String(firstModelId);
        await loadAnalytics(firstModelId);
    } catch (error) {
        console.error("LOAD MODELS ERROR:", error);
        showError(error.message || "Не удалось загрузить модели.");
        showNoModels();
    } finally {
        showLoading(false);
    }
}


/* ============================================================
   POPULATE MODELS
   ============================================================ */

function populateModels(models) {
    elements.modelSelect.innerHTML = "";
    models.forEach((model, index) => {
        const id = getModelId(model);
        if (!id) return;
        const option = document.createElement("option");
        option.value = id;
        option.textContent = formatModelName(model, index);
        elements.modelSelect.appendChild(option);
    });
    elements.modelStatusText.textContent = `Доступно моделей: ${models.length}`;
}

function getModelId(model) {
    if (!model || typeof model !== "object") return null;
    return model.id ?? model.model_id ?? model.model_version_id ?? null;
}

function formatModelName(model, index) {
    const id = getModelId(model);
    const version = model.version ?? model.name ?? model.model_name ?? `Модель ${index + 1}`;
    const status = model.status ? ` · ${translateStatus(model.status)}` : "";
    return `#${id} · ${version}${status}`;
}


/* ============================================================
   LOAD ANALYTICS
   ============================================================ */

async function loadAnalytics(modelId) {
    showLoading(true);
    hideError();
    elements.analyticsDashboard.hidden = true;

    try {
        const token = sessionStorage.getItem("access_token");
        const response = await fetch(
            `${API_BASE}/models/${modelId}/analytics`,
            { headers: { Authorization: `Bearer ${token}` } }
        );

        if (!response.ok) {
            const errorText = await getResponseError(response);
            throw new Error(errorText || "Не удалось загрузить аналитику модели.");
        }

        analyticsData = await response.json();
        renderAnalytics();
    } catch (error) {
        console.error("LOAD ANALYTICS ERROR:", error);
        analyticsData = null;
        showError(error.message || "Не удалось загрузить аналитику.");
    } finally {
        showLoading(false);
    }
}


/* ============================================================
   RENDER ALL
   ============================================================ */

function renderAnalytics() {
    if (!analyticsData) return;
    elements.analyticsDashboard.hidden = false;

    renderOverview();
    renderFeatureSelector();
    renderSegments();
    renderCalibration();
    renderInsights();
    renderTechnical();
    renderMode();
}


/* ============================================================
   MODE
   ============================================================ */

function renderMode() {
    if (!analyticsData) return;

    const historical = currentMode === "all" || currentMode === "historical";
    const predictions = currentMode === "all" || currentMode === "predictions";

    elements.overviewSection.hidden = false;
    elements.conversionSection.hidden = !historical;
    elements.segmentsSection.hidden = !predictions;
    elements.insightsSection.hidden = false;

    // Блок калибровки показываем только если есть данные.
    const calibration = analyticsData.predictions?.calibration || [];
    elements.calibrationSection.hidden =
        !(historical && predictions && calibration.length > 0);

    if (currentMode === "historical") {
        elements.overviewDescription.textContent =
            "Информация только об исходных данных, использованных при обучении модели.";
    } else if (currentMode === "predictions") {
        elements.overviewDescription.textContent =
            "Информация только о сохранённых результатах прогнозирования.";
    } else {
        elements.overviewDescription.textContent =
            "Исторические данные и результаты прогнозов в одном представлении.";
    }

    const targetCard = document
        .getElementById("targetChart")
        ?.closest(".analytics-chart-card");
    if (targetCard) targetCard.hidden = !historical;

    if (elements.overviewPredictionChartCard) {
        elements.overviewPredictionChartCard.hidden = !predictions;
    }

    const cards = document.querySelectorAll("#overviewSection .analytics-metric-card");
    if (cards[0]) cards[0].hidden = !historical;
    if (cards[1]) cards[1].hidden = !historical;
    if (cards[2]) cards[2].hidden = !predictions;
    if (cards[3]) cards[3].hidden = !predictions;

    renderInsightsForMode();
}


/* ============================================================
   OVERVIEW
   ============================================================ */

function renderOverview() {
    const dataset = analyticsData.dataset || {};
    const predictions = analyticsData.predictions || {};

    const rows = Number(dataset.rows || 0);
    const targetDistribution = normalizeTargetDistribution(
        dataset.target_distribution
    );

    const conversion = calculateConversion(targetDistribution);
    const predictionTotal = Number(predictions.total || 0);
    const topShare = calculateTopShare(predictions);

    elements.metricRows.textContent = formatNumber(rows);
    elements.metricConversion.textContent =
        conversion === null ? "—" : formatPercent(conversion);
    elements.metricPredictions.textContent = formatNumber(predictionTotal);
    elements.metricTopShare.textContent =
        topShare === null ? "—" : formatPercent(topShare);

    renderTargetChart(targetDistribution);
    renderOverviewProbabilityChart(predictions);
}


/* ============================================================
   CONVERSION
   ============================================================ */

function calculateConversion(distribution) {
    if (!Array.isArray(distribution) || !distribution.length) return null;

    let positive = 0;
    let total = 0;

    distribution.forEach((item) => {
        const count = Number(item.count || 0);
        total += count;
        if (isPositiveValue(item.value)) positive += count;
    });

    if (total === 0) return null;
    return positive / total;
}


/* ============================================================
   TOP SHARE
   ============================================================ */

function calculateTopShare(predictions) {
    const dist = Array.isArray(predictions.probability_distribution)
        ? predictions.probability_distribution
        : [];

    if (!dist.length) return null;

    const total = dist.reduce((acc, item) => acc + Number(item.count || 0), 0);
    if (total === 0) return null;

    const top = dist
        .filter((item) => Number(item.from || 0) >= 0.8)
        .reduce((acc, item) => acc + Number(item.count || 0), 0);

    return top / total;
}


/* ============================================================
   TARGET CHART
   ============================================================ */

function renderTargetChart(data) {
    destroyChart("target");
    const canvas = document.getElementById("targetChart");
    if (!canvas || !data.length) return;

    const labels = data.map((item) => translateTargetValue(item.value));
    const values = data.map((item) => Number(item.count || 0));

    charts.target = new Chart(canvas, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Количество записей",
                data: values,
                backgroundColor: "#111111",
                borderWidth: 0
            }]
        },
        options: createChartOptions("Количество записей")
    });
}


/* ============================================================
   OVERVIEW PROBABILITY CHART
   ============================================================ */

function renderOverviewProbabilityChart(predictions) {
    destroyChart("overviewProbability");
    const canvas = document.getElementById("overviewProbabilityChart");
    if (!canvas) return;

    const distribution = Array.isArray(predictions.probability_distribution)
        ? predictions.probability_distribution
        : [];

    if (!distribution.length) return;

    const labels = distribution.map(
        (item) =>
            `${Math.round(Number(item.from || 0) * 100)}–${Math.round(Number(item.to || 0) * 100)}%`
    );
    const values = distribution.map((item) => Number(item.count || 0));

    charts.overviewProbability = new Chart(canvas, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Количество прогнозов",
                data: values,
                backgroundColor: "#19D3C5",
                borderWidth: 0
            }]
        },
        options: createChartOptions("Количество прогнозов")
    });
}


/* ============================================================
   FEATURE SELECTOR
   ============================================================ */

function renderFeatureSelector() {
    const dataset = analyticsData.dataset || {};
    const columns = Array.isArray(dataset.columns) ? dataset.columns : [];

    elements.featureSelect.innerHTML = "";

    if (!columns.length) {
        const option = document.createElement("option");
        option.textContent = "Нет доступных характеристик";
        option.value = "";
        elements.featureSelect.appendChild(option);
        return;
    }

    columns.forEach((column) => {
        const name = getColumnName(column);
        if (!name) return;
        const option = document.createElement("option");
        option.value = name;
        option.textContent = prettifyFeatureName(name);
        elements.featureSelect.appendChild(option);
    });

    const first = getFirstFeatureName();
    if (first) {
        elements.featureSelect.value = first;
        renderFeatureConversion(first);
    }
}

function getColumnName(column) {
    if (typeof column === "string") return column;
    if (column && typeof column === "object") {
        return column.name ?? column.column ?? column.label ?? column.field ?? "";
    }
    return "";
}

function getFirstFeatureName() {
    const features = analyticsData.features || {};
    const names = Object.keys(features);
    return names.length ? names[0] : "";
}


/* ============================================================
   FEATURE CONVERSION
   ============================================================ */

function renderFeatureConversion(featureName) {
    const features = analyticsData.features || {};
    const analysis = features[featureName];
    if (!analysis) return;

    let groups = [];

    if (analysis.type === "numeric") {
        const bins = Array.isArray(analysis.bins) ? analysis.bins : [];
        groups = bins.map((bin) => ({
            label: `${formatValue(bin.from)} – ${formatValue(bin.to)}`,
            count: Number(bin.count || 0),
            positive: Number(bin.positive_count || 0),
            conversion:
                bin.conversion != null
                    ? Number(bin.conversion) / 100
                    : 0
        }));
    } else {
        const categories = Array.isArray(analysis.categories)
            ? analysis.categories
            : [];
        groups = categories.map((item) => ({
            label: shortenLabel(String(item.value ?? "—"), 22),
            count: Number(item.count || 0),
            positive: Number(item.positive_count || 0),
            conversion:
                item.conversion != null
                    ? Number(item.conversion) / 100
                    : 0
        }));
    }

    const total = groups.reduce((acc, g) => acc + g.count, 0);
    elements.featureGroups.textContent = formatNumber(groups.length);

    const best = groups
        .slice()
        .sort((a, b) => b.conversion - a.conversion)[0];

    if (best) {
        elements.featureBestGroup.textContent = best.label;
        elements.featureBestConversion.textContent = formatPercent(best.conversion);
    } else {
        elements.featureBestGroup.textContent = "—";
        elements.featureBestConversion.textContent = "—";
    }

    const avgPositive = groups.reduce((acc, g) => acc + g.positive, 0);
    const average = total ? avgPositive / total : null;
    elements.featureAverageConversion.textContent =
        average === null ? "—" : formatPercent(average);

    elements.featureChartTitle.textContent =
        `Доля совершивших действие по «${prettifyFeatureName(featureName)}»`;
    elements.featureChartDescription.textContent =
        "Чем выше столбец, тем чаще группа совершает целевое действие.";

    renderConversionChart(groups);
}

function renderConversionChart(groups) {
    destroyChart("feature");
    const canvas = document.getElementById("featureChart");
    if (!canvas || !groups.length) return;

    const visible = groups
        .slice()
        .sort((a, b) => b.count - a.count)
        .slice(0, 12);

    const labels = visible.map((g) => g.label);
    const values = visible.map((g) =>
        Number((g.conversion * 100).toFixed(1))
    );

    charts.feature = new Chart(canvas, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Конверсия, %",
                data: values,
                backgroundColor: "#19D3C5",
                borderColor: "#111111",
                borderWidth: 1
            }]
        },
        options: createChartOptions("Конверсия, %")
    });
}


/* ============================================================
   SEGMENTS
   ============================================================ */

function renderSegments() {
    const predictions = analyticsData.predictions || {};
    const segments = Array.isArray(predictions.segments)
        ? predictions.segments
        : [];

    elements.segmentTableBody.innerHTML = "";

    if (!segments.length) {
        elements.segmentEmpty.hidden = false;
        return;
    }
    elements.segmentEmpty.hidden = true;

    const total = Number(predictions.total || 0);

    segments.slice(0, 5).forEach((segment) => {
        const size = Number(segment.size || 0);
        const share = total ? size / total : 0;
        const avg = Number(segment.average_probability || 0);

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${escapeHtml(segment.label || "—")}</td>
            <td>${formatNumber(size)}</td>
            <td>${formatPercent(share)}</td>
            <td>${formatPercent(avg)}</td>
        `;
        elements.segmentTableBody.appendChild(row);
    });
}


/* ============================================================
   CALIBRATION
   ============================================================ */

function renderCalibration() {
    const section = document.getElementById("calibrationSection");
    const deciles = Array.isArray(analyticsData?.predictions?.calibration)
        ? analyticsData.predictions.calibration
        : [];

    if (!deciles.length) {
        if (section) section.hidden = true;
        return;
    }

    if (section) section.hidden = false;

    destroyChart("calibration");
    const canvas = document.getElementById("calibrationChart");
    if (!canvas) return;

    const labels = deciles.map((item) => item.label);
    const values = deciles.map((item) =>
        Number(((item.conversion || 0) * 100).toFixed(1))
    );

    charts.calibration = new Chart(canvas, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Фактическая конверсия, %",
                data: values,
                backgroundColor: "#111111",
                borderWidth: 0
            }]
        },
        options: createChartOptions("Конверсия, %")
    });
}


/* ============================================================
   INSIGHTS
   ============================================================ */

function renderInsights() {
    renderInsightsForMode();
}

function renderInsightsForMode() {
    const insights = Array.isArray(analyticsData?.insights)
        ? analyticsData.insights
        : [];

    elements.insightsList.innerHTML = "";

    if (!insights.length) {
        elements.insightsList.innerHTML = `
            <div class="analytics-empty-panel">
                <div class="analytics-empty-number">—</div>
                <div>
                    <h3>Пока нет автоматических выводов</h3>
                    <p>Для выбранной модели недостаточно информации для формирования выводов.</p>
                </div>
            </div>`;
        return;
    }

    let visible = insights.slice();

    if (currentMode === "historical") {
        visible = insights.filter(
            (text) => !text.includes("прогноз") && !text.includes("сохранено")
        );
    } else if (currentMode === "predictions") {
        visible = insights.filter((text) => text.includes("прогноз"));
    }

    if (!visible.length) visible = insights.slice(0, 2);

    visible.forEach((text, index) => {
        const article = document.createElement("article");
        article.className = "analytics-insight";
        article.innerHTML = `
            <span class="analytics-insight-number">${String(index + 1).padStart(2, "0")}</span>
            <p>${escapeHtml(text)}</p>
        `;
        elements.insightsList.appendChild(article);
    });
}


/* ============================================================
   TECHNICAL
   ============================================================ */

function renderTechnical() {
    const dataset = analyticsData.dataset || {};
    const columns = Array.isArray(dataset.columns) ? dataset.columns : [];
    renderMissingChart(columns);
    renderFeatureTable(columns);
}

function renderMissingChart(columns) {
    destroyChart("missing");
    const canvas = document.getElementById("missingChart");
    if (!canvas || !columns.length) return;

    const visible = columns
        .map((column) => ({
            name: getColumnName(column),
            missing: Number(column?.missing || 0)
        }))
        .filter((item) => item.name)
        .sort((a, b) => b.missing - a.missing);

    const labels = visible.map((item) => shortenLabel(item.name, 20));
    const values = visible.map((item) => item.missing);

    charts.missing = new Chart(canvas, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Пропущенных значений",
                data: values,
                backgroundColor: "#8B928A",
                borderWidth: 0
            }]
        },
        options: createChartOptions("Пропущенные значения")
    });
}

function renderFeatureTable(columns) {
    elements.featureTableBody.innerHTML = "";

    if (!columns.length) {
        elements.featureTableBody.innerHTML = `
            <tr><td colspan="5">Нет информации о характеристиках.</td></tr>`;
        return;
    }

    const totalRows = Number(analyticsData.dataset?.rows || 0);

    columns.forEach((column) => {
        const name = getColumnName(column);
        if (!name) return;

        const type = column.type || "unknown";
        const missing = Number(column.missing || 0);
        const filled = Math.max(totalRows - missing, 0);
        const unique = Number(column.unique || 0);

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${escapeHtml(prettifyFeatureName(name))}</td>
            <td><span class="type-badge">${escapeHtml(translateFeatureType(type))}</span></td>
            <td>${formatNumber(filled)}</td>
            <td>${formatNumber(missing)}</td>
            <td>${formatNumber(unique)}</td>
        `;
        elements.featureTableBody.appendChild(row);
    });
}


/* ============================================================
   CHART OPTIONS
   ============================================================ */

function createChartOptions(yAxisTitle = "") {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: "#111111",
                titleColor: "#ffffff",
                bodyColor: "#ffffff",
                padding: 12,
                displayColors: false,
                callbacks: {
                    label(context) {
                        const value = context.parsed.y ?? context.parsed;
                        return formatNumber(value);
                    }
                }
            }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: {
                    color: "#626262",
                    font: { family: "JetBrains Mono", size: 10 },
                    maxRotation: 35,
                    minRotation: 0
                }
            },
            y: {
                beginAtZero: true,
                grid: { color: "#E5E8E2" },
                ticks: {
                    color: "#626262",
                    font: { family: "JetBrains Mono", size: 10 },
                    precision: 0
                },
                title: {
                    display: Boolean(yAxisTitle),
                    text: yAxisTitle,
                    color: "#626262",
                    font: { family: "Space Grotesk", size: 11, weight: "500" }
                }
            }
        }
    };
}

function destroyChart(name) {
    if (charts[name]) {
        charts[name].destroy();
        charts[name] = null;
    }
}


/* ============================================================
   HELPERS
   ============================================================ */

function normalizeTargetDistribution(distribution) {
    if (!Array.isArray(distribution)) return [];
    return distribution.map((item) => ({
        value: item?.value ?? item?.label ?? "Неизвестно",
        count: Number(item?.count || 0)
    }));
}

function isPositiveValue(value) {
    const text = String(value).toLowerCase();
    return (
        text === "1" ||
        text === "true" ||
        text === "positive" ||
        text === "yes" ||
        text === "да"
    );
}

function formatNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    return new Intl.NumberFormat("ru-RU").format(number);
}

function formatPercent(value) {
    let number = Number(value);
    if (!Number.isFinite(number)) return "—";
    if (number <= 1) number *= 100;
    return `${number.toFixed(1)}%`;
}

function formatValue(value) {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    if (Number.isFinite(number)) {
        if (Math.abs(number) >= 1000 || Number.isInteger(number)) {
            return formatNumber(number);
        }
        return number.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
    }
    return String(value);
}

function prettifyFeatureName(name) {
    if (!name) return "";
    return String(name)
        .replace(/_/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .replace(/^./, (char) => char.toUpperCase());
}

function shortenLabel(value, maxLength = 20) {
    const text = String(value);
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength - 1) + "…";
}

function translateFeatureType(type) {
    switch (String(type).toLowerCase()) {
        case "numeric":
            return "числовой";
        case "categorical":
            return "категория";
        default:
            return "другой";
    }
}

function translateTargetValue(value) {
    const text = String(value);
    if (text === "1") return "Совершили действие";
    if (text === "0") return "Не совершили";
    if (text.toLowerCase() === "true") return "Совершили действие";
    if (text.toLowerCase() === "false") return "Не совершили";
    if (text === "(пропуск)") return "Нет значения";
    return text;
}

function translateStatus(status) {
    switch (String(status).toLowerCase()) {
        case "ready":
            return "готова";
        case "training":
            return "обучается";
        case "failed":
            return "ошибка";
        default:
            return status;
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* ============================================================
   ERROR / LOADING / EMPTY
   ============================================================ */

async function getResponseError(response) {
    try {
        const data = await response.json();
        if (typeof data.detail === "string") return data.detail;
        return "";
    } catch {
        return "";
    }
}

function showError(message) {
    if (!elements.analyticsError) return;
    elements.analyticsError.textContent = message;
    elements.analyticsError.hidden = false;
}

function hideError() {
    if (!elements.analyticsError) return;
    elements.analyticsError.hidden = true;
    elements.analyticsError.textContent = "";
}

function showLoading(show) {
    if (!elements.analyticsLoading) return;
    elements.analyticsLoading.hidden = !show;
}

function showNoModels() {
    if (elements.analyticsDashboard) elements.analyticsDashboard.hidden = true;
    if (elements.analyticsEmpty) elements.analyticsEmpty.hidden = false;
    if (elements.modelStatusText) {
        elements.modelStatusText.textContent = "Нет доступных моделей";
    }
    if (elements.modelSelect) {
        elements.modelSelect.innerHTML = `<option value="">Нет доступных моделей</option>`;
    }
}

function hideNoModels() {
    if (elements.analyticsEmpty) elements.analyticsEmpty.hidden = true;
}