
const API_BASE_URL = "http://127.0.0.1:8001/api";

const authLink = document.getElementById("authLink");
const logoutButton = document.getElementById("logoutButton");
const refreshButton = document.getElementById("refreshModels");

const modelsDescription = document.getElementById("modelsDescription");
const modelsMessage = document.getElementById("modelsMessage");
const modelsList = document.getElementById("modelsList");
const emptyState = document.getElementById("emptyState");

const totalModelsElement = document.getElementById("totalModels");
const readyModelsElement = document.getElementById("readyModels");
const latestModelDateElement = document.getElementById("latestModelDate");

const READY_STATUSES = new Set([
    "ready",
    "trained",
    "success",
    "successful",
    "accepted",
    "active",
    "completed"
]);

const FAILED_STATUSES = new Set([
    "failed",
    "error",
    "rejected"
]);

// ----------------------------------------
// Авторизация
// ----------------------------------------

function getToken() {
    return sessionStorage.getItem("access_token");
}

function updateAuthUI() {
    if (getToken()) {
        authLink.textContent = "Вы вошли";
        authLink.href = "#";
        logoutButton.hidden = false;
    } else {
        authLink.textContent = "Войти";
        authLink.href = "login.html";
        logoutButton.hidden = true;
    }
}

updateAuthUI();

logoutButton.addEventListener("click", () => {
    sessionStorage.removeItem("access_token");
    window.location.href = "login.html";
});

// ----------------------------------------
// API
// ----------------------------------------

async function apiRequest(url) {
    const token = getToken();

    if (!token) {
        throw new Error("Войди в аккаунт, чтобы просмотреть свои модели.");
    }

    let response;

    try {
        response = await fetch(url, {
            method: "GET",
            headers: {
                Accept: "application/json",
                Authorization: `Bearer ${token}`
            }
        });
    } catch {
        throw new Error(
            "Не удалось подключиться к backend. " +
            "Проверь, запущен ли сервер на порту 8001."
        );
    }

    const responseText = await response.text();
    let data = {};

    if (responseText) {
        try {
            data = JSON.parse(responseText);
        } catch {
            data = { detail: responseText };
        }
    }

    if (response.status === 401) {
        sessionStorage.removeItem("access_token");
        updateAuthUI();

        throw new Error(
            "Сессия завершена. Войди в аккаунт заново."
        );
    }

    if (!response.ok) {
        let message = `Ошибка сервера: HTTP ${response.status}`;

        if (typeof data.detail === "string") {
            message = data.detail;
        } else if (Array.isArray(data.detail)) {
            message = data.detail
                .map(item => item.msg || JSON.stringify(item))
                .join("; ");
        } else if (typeof data.message === "string") {
            message = data.message;
        }

        throw new Error(message);
    }

    return data;
}

// ----------------------------------------
// Форматирование
// ----------------------------------------

function formatValue(value) {
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    if (typeof value === "number") {
        return Number.isFinite(value)
            ? value.toLocaleString("ru-RU", {
                maximumFractionDigits: 5
            })
            : String(value);
    }

    if (typeof value === "object") {
        return JSON.stringify(value);
    }

    return String(value);
}

function formatDate(value, includeTime = true) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString(
        "ru-RU",
        includeTime
            ? {
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit"
            }
            : {
                year: "numeric",
                month: "2-digit",
                day: "2-digit"
            }
    );
}

function normalizeStatus(status) {
    return String(status ?? "")
        .trim()
        .toLowerCase();
}

function getStatusLabel(status) {
    const normalized = normalizeStatus(status);

    const labels = {
        ready: "Готова",
        trained: "Обучена",
        success: "Успешно",
        successful: "Успешно",
        accepted: "Принята",
        active: "Активна",
        completed: "Завершена",
        failed: "Ошибка",
        error: "Ошибка",
        rejected: "Отклонена",
        pending: "Ожидает",
        training: "Обучается",
        processing: "Обрабатывается"
    };

    return labels[normalized] || status || "Не указан";
}

function createElement(tag, className = "", text = "") {
    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== null && text !== undefined) {
        element.textContent = String(text);
    }

    return element;
}

function addInfoField(parent, label, value) {
    const field = createElement("div", "model-info-field");

    field.appendChild(
        createElement("span", "model-info-label", label)
    );

    field.appendChild(
        createElement("span", "model-info-value", formatValue(value))
    );

    parent.appendChild(field);
}

function showMessage(message, type = "") {
    modelsMessage.textContent = message;
    modelsMessage.className = "models-notice";

    if (type) {
        modelsMessage.classList.add(`notice-${type}`);
    }

    modelsMessage.hidden = false;
}

function hideMessage() {
    modelsMessage.textContent = "";
    modelsMessage.className = "models-notice";
    modelsMessage.hidden = true;
}

// ----------------------------------------
// Статистика
// ----------------------------------------

function updateStatistics(models) {
    totalModelsElement.textContent = String(models.length);

    const readyCount = models.filter(model =>
        READY_STATUSES.has(normalizeStatus(model.status))
    ).length;

    readyModelsElement.textContent = String(readyCount);

    const sortedModels = [...models].sort((a, b) => {
        const dateA = new Date(a.created_at).getTime();
        const dateB = new Date(b.created_at).getTime();

        return (
            (Number.isFinite(dateB) ? dateB : 0) -
            (Number.isFinite(dateA) ? dateA : 0)
        );
    });

    latestModelDateElement.textContent = sortedModels.length
        ? formatDate(sortedModels[0].created_at, false)
        : "—";
}

// ----------------------------------------
// Карточка одной модели
// ----------------------------------------

function renderModelCard(model) {
    const card = createElement("article", "model-card");

    const header = createElement("div", "model-card-header");
    const heading = createElement("div", "model-card-heading");

    heading.appendChild(
        createElement(
            "h3",
            "model-card-version",
            model.version || `Модель #${model.id}`
        )
    );

    heading.appendChild(
        createElement("p", "model-card-id", `ID: ${model.id}`)
    );

    const normalizedStatus = normalizeStatus(model.status);

    let statusClass = "";

    if (READY_STATUSES.has(normalizedStatus)) {
        statusClass = "status-ready";
    } else if (FAILED_STATUSES.has(normalizedStatus)) {
        statusClass = "status-failed";
    }

    const status = createElement(
        "span",
        `model-status ${statusClass}`.trim(),
        getStatusLabel(model.status)
    );

    header.append(heading, status);
    card.appendChild(header);

    const body = createElement("div", "model-card-body");

    // Основная информация
    const infoGrid = createElement("div", "model-card-info");

    addInfoField(
        infoGrid,
        "ВЕРСИЯ",
        model.version || "—"
    );

    addInfoField(
        infoGrid,
        "ЦЕЛЕВОЙ СТОЛБЕЦ",
        model.target_column || "—"
    );

    addInfoField(
        infoGrid,
        "СТАТУС",
        getStatusLabel(model.status)
    );

    addInfoField(
        infoGrid,
        "ДАТА СОЗДАНИЯ",
        formatDate(model.created_at)
    );

    body.appendChild(infoGrid);

    // Метрики
    const metricsSection = createElement("section", "model-metrics");

    metricsSection.appendChild(
        createElement("h4", "model-metrics-title", "Метрики качества")
    );

    const metricsGrid = createElement("div", "model-metrics-grid");
    const metrics = model.metrics &&
        typeof model.metrics === "object" &&
        !Array.isArray(model.metrics)
        ? model.metrics
        : {};

    const metricEntries = Object.entries(metrics);

    if (metricEntries.length === 0) {
        metricsGrid.appendChild(
            createElement(
                "p",
                "",
                "Метрики для этой модели не указаны."
            )
        );
    } else {
        metricEntries.forEach(([name, value]) => {
            const metric = createElement("div", "model-metric");

            metric.appendChild(
                createElement("span", "model-metric-name", name)
            );

            metric.appendChild(
                createElement("strong", "model-metric-value", formatValue(value))
            );

            metricsGrid.appendChild(metric);
        });
    }

    metricsSection.appendChild(metricsGrid);
    body.appendChild(metricsSection);

    // Нижняя строка карточки
    const footer = createElement("div", "model-card-footer");

    const footerLeft = createElement("span");
    footerLeft.appendChild(
        createElement("strong", "", "ID модели: ")
    );
    footerLeft.appendChild(
        document.createTextNode(String(model.id ?? "—"))
    );

    const footerRight = createElement(
        "span",
        "",
        `Создана: ${formatDate(model.created_at, false)}`
    );

    footer.append(footerLeft, footerRight);
    body.appendChild(footer);

    card.appendChild(body);

    return card;
}

// ----------------------------------------
// Отображение списка моделей
// ----------------------------------------

function renderModels(data) {
    const models = Array.isArray(data.items) ? data.items : [];

    modelsList.replaceChildren();

    updateStatistics(models);

    modelsDescription.textContent =
        `Найдено моделей: ${data.total ?? models.length}`;

    if (models.length === 0) {
        emptyState.hidden = false;
        modelsList.hidden = true;

        showMessage("Список моделей успешно загружен.", "success");
        return;
    }

    emptyState.hidden = true;
    modelsList.hidden = false;

    const sortedModels = [...models].sort((a, b) => {
        const dateA = new Date(a.created_at).getTime();
        const dateB = new Date(b.created_at).getTime();

        return (
            (Number.isFinite(dateB) ? dateB : 0) -
            (Number.isFinite(dateA) ? dateA : 0)
        );
    });

    sortedModels.forEach(model => {
        modelsList.appendChild(renderModelCard(model));
    });

    showMessage(
        `Список обновлён. Загружено моделей: ${models.length}.`,
        "success"
    );
}

// ----------------------------------------
// Загрузка моделей
// GET /api/models
// ----------------------------------------

async function loadModels() {
    refreshButton.disabled = true;
    modelsList.classList.add("models-loading");

    emptyState.hidden = true;
    modelsList.hidden = false;

    showMessage("Загружаем модели из backend...");

    try {
        if (!getToken()) {
            modelsList.replaceChildren();

            totalModelsElement.textContent = "—";
            readyModelsElement.textContent = "—";
            latestModelDateElement.textContent = "—";
            modelsDescription.textContent = "Требуется авторизация.";

            showMessage(
                "Войди в аккаунт, чтобы просмотреть свои модели.",
                "error"
            );

            return;
        }

        const data = await apiRequest(`${API_BASE_URL}/models`);
        renderModels(data);
    } catch (error) {
        modelsList.replaceChildren();
        modelsList.hidden = true;
        emptyState.hidden = true;

        modelsDescription.textContent = "Не удалось загрузить данные.";

        showMessage(
            error.message || "Не удалось загрузить список моделей.",
            "error"
        );
    } finally {
        refreshButton.disabled = false;
        modelsList.classList.remove("models-loading");
    }
}

refreshButton.addEventListener("click", loadModels);

// Первичная загрузка
loadModels();
