
const API_BASE_URL = "http://127.0.0.1:8001/api";

const token = sessionStorage.getItem("access_token");

const trainingForm = document.getElementById("trainingForm");
const csvFileInput = document.getElementById("csvFile");
const targetColumnInput = document.getElementById("targetColumn");
const trainButton = document.getElementById("trainButton");
const trainButtonText = document.getElementById("trainButtonText");
const trainMessage = document.getElementById("trainMessage");

const uploadTitle = document.getElementById("uploadTitle");
const uploadDescription = document.getElementById("uploadDescription");
const fileInfo = document.getElementById("fileInfo");

const previewSection = document.getElementById("previewSection");
const previewDescription = document.getElementById("previewDescription");
const previewTable = document.getElementById("previewTable");

const resultSection = document.getElementById("resultSection");
const resultSubtitle = document.getElementById("resultSubtitle");
const resultStatus = document.getElementById("resultStatus");
const resultDetails = document.getElementById("resultDetails");
const metricsGrid = document.getElementById("metricsGrid");
const featuresList = document.getElementById("featuresList");

const modelsMessage = document.getElementById("modelsMessage");
const modelsList = document.getElementById("modelsList");
const refreshModelsButton = document.getElementById("refreshModels");

const authLink = document.getElementById("authLink");
const logoutButton = document.getElementById("logoutButton");

let selectedFile = null;
let csvHeaders = [];

// --------------------------------------------------
// Авторизация
// --------------------------------------------------

if (token) {
    authLink.textContent = "Вы вошли";
    authLink.href = "#";
    logoutButton.hidden = false;
} else {
    authLink.textContent = "Войти";
    authLink.href = "login.html";
    logoutButton.hidden = true;

    showMessage(
        "Для обучения необходимо войти в аккаунт. " +
        "После входа вернись на эту страницу.",
        "info"
    );
}

logoutButton.addEventListener("click", () => {
    sessionStorage.removeItem("access_token");
    window.location.href = "login.html";
});

// --------------------------------------------------
// Общие функции
// --------------------------------------------------

function showMessage(message, type = "error") {
    trainMessage.textContent = message;
    trainMessage.className = "message";

    if (type === "success") {
        trainMessage.classList.add("success");
    } else if (type === "info") {
        trainMessage.classList.add("info");
    }

    trainMessage.hidden = false;
}

function hideMessage() {
    trainMessage.hidden = true;
    trainMessage.textContent = "";
}

function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} Б`;
    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} КБ`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(2)} МБ`;
}

function formatValue(value) {
    if (value === null || value === undefined) {
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

function addTextElement(parent, tag, text, className = "") {
    const element = document.createElement(tag);
    element.textContent = text;

    if (className) {
        element.className = className;
    }

    parent.appendChild(element);
    return element;
}

function getErrorMessage(data, fallback) {
    if (typeof data?.detail === "string") {
        return data.detail;
    }

    if (Array.isArray(data?.detail)) {
        return data.detail
            .map(item => item.msg || JSON.stringify(item))
            .join("; ");
    }

    if (typeof data?.message === "string") {
        return data.message;
    }

    return fallback;
}

async function apiRequest(url, options = {}) {
    const currentToken = sessionStorage.getItem("access_token");

    const headers = {
        Accept: "application/json",
        ...(options.headers || {})
    };

    if (currentToken) {
        headers.Authorization = `Bearer ${currentToken}`;
    }

    let response;

    try {
        response = await fetch(url, {
            ...options,
            headers
        });
    } catch (error) {
        throw new Error(
            "Не удалось подключиться к backend. " +
            "Проверь, запущен ли сервер на порту 8001 и настройки CORS."
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
        throw new Error(
            "Сессия истекла или токен недействителен. Войди в аккаунт заново."
        );
    }

    if (!response.ok) {
        throw new Error(
            getErrorMessage(
                data,
                `Ошибка сервера: HTTP ${response.status}`
            )
        );
    }

    return data;
}

// --------------------------------------------------
// Чтение CSV для предпросмотра
// --------------------------------------------------

function parseCSVLine(line, delimiter) {
    const cells = [];
    let value = "";
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
            if (inQuotes && line[i + 1] === '"') {
                value += '"';
                i++;
            } else {
                inQuotes = !inQuotes;
            }
        } else if (char === delimiter && !inQuotes) {
            cells.push(value.trim());
            value = "";
        } else {
            value += char;
        }
    }

    cells.push(value.trim());
    return cells;
}

function detectDelimiter(line) {
    const candidates = [",", ";", "\t"];
    let bestDelimiter = ",";
    let bestCount = 1;

    for (const delimiter of candidates) {
        const count = parseCSVLine(line, delimiter).length;

        if (count > bestCount) {
            bestCount = count;
            bestDelimiter = delimiter;
        }
    }

    return bestDelimiter;
}

function clearPreview() {
    previewSection.hidden = true;
    previewTable.replaceChildren();
    previewDescription.textContent = "";
    csvHeaders = [];

    const datalist = document.getElementById("targetColumns");
    if (datalist) {
        datalist.replaceChildren();
    }
}

function renderPreview(lines, delimiter) {
    previewTable.replaceChildren();

    const rows = lines.map(line => parseCSVLine(line, delimiter));
    const headers = rows[0] || [];

    if (!headers.length || !headers.some(header => header.trim())) {
        throw new Error(
            "Не удалось прочитать заголовки CSV. " +
            "Проверь первую строку файла."
        );
    }

    csvHeaders = headers.map(header => header.replace(/^\uFEFF/, "").trim());

    // Добавляем подсказки с названиями столбцов.
    let datalist = document.getElementById("targetColumns");

    if (!datalist) {
        datalist = document.createElement("datalist");
        datalist.id = "targetColumns";
        targetColumnInput.setAttribute("list", "targetColumns");
        targetColumnInput.insertAdjacentElement("afterend", datalist);
    }

    datalist.replaceChildren();

    csvHeaders.forEach(header => {
        const option = document.createElement("option");
        option.value = header;
        datalist.appendChild(option);
    });

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");

    headers.forEach(header => {
        addTextElement(headerRow, "th", header || "(без названия)");
    });

    thead.appendChild(headerRow);
    previewTable.appendChild(thead);

    const tbody = document.createElement("tbody");

    rows.slice(1, 5).forEach(row => {
        const tr = document.createElement("tr");

        headers.forEach((_, index) => {
            addTextElement(tr, "td", row[index] ?? "");
        });

        tbody.appendChild(tr);
    });

    previewTable.appendChild(tbody);

    const previewRowCount = Math.min(Math.max(rows.length - 1, 0), 4);

    previewDescription.textContent =
        `Столбцов: ${headers.length}. ` +
        `Строк в предпросмотре: ${previewRowCount}. ` +
        "Показаны первые строки файла.";

    previewSection.hidden = false;
}

csvFileInput.addEventListener("change", async () => {
    hideMessage();
    resultSection.hidden = true;
    clearPreview();

    selectedFile = csvFileInput.files?.[0] || null;

    if (!selectedFile) {
        uploadTitle.textContent = "Выбери CSV-файл";
        uploadDescription.textContent =
            "Нажми, чтобы выбрать файл на компьютере";
        fileInfo.hidden = true;
        return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".csv")) {
        selectedFile = null;
        csvFileInput.value = "";
        fileInfo.hidden = true;
        showMessage("Нужен файл с расширением .csv.");
        return;
    }

    const maxSize = 20 * 1024 * 1024;

    if (selectedFile.size > maxSize) {
        selectedFile = null;
        csvFileInput.value = "";
        fileInfo.hidden = true;
        showMessage("Размер CSV-файла не должен превышать 20 МБ.");
        return;
    }

    if (selectedFile.size === 0) {
        selectedFile = null;
        csvFileInput.value = "";
        fileInfo.hidden = true;
        showMessage("Выбранный файл пуст.");
        return;
    }

    uploadTitle.textContent = selectedFile.name;
    uploadDescription.textContent = "Файл выбран";

    fileInfo.hidden = false;
    fileInfo.textContent =
        `${selectedFile.name} · ${formatBytes(selectedFile.size)}`;

    try {
        const text = await selectedFile.text();
        const lines = text
            .replace(/^\uFEFF/, "")
            .split(/\r?\n/)
            .filter(line => line.trim().length > 0);

        if (lines.length < 2) {
            throw new Error(
                "В CSV должны быть заголовки и хотя бы одна строка данных."
            );
        }

        const delimiter = detectDelimiter(lines[0]);
        renderPreview(lines, delimiter);
    } catch (error) {
        clearPreview();
        showMessage(error.message || "Не удалось прочитать CSV.");
    }
});

// --------------------------------------------------
// Отображение результата обучения
// --------------------------------------------------

function renderTrainingResult(result) {
    resultSection.hidden = false;
    resultSubtitle.textContent =
        result.model_id ? `Модель: ${result.model_id}` : "Результат обучения";

    resultStatus.className = "result-status";

    if (result.model_accepted) {
        resultStatus.classList.add("accepted");
    } else {
        resultStatus.classList.add("rejected");
    }

    resultStatus.textContent =
        result.message ||
        (result.model_accepted
            ? "Модель прошла критерии качества."
            : "Модель не прошла критерии качества.");

    resultDetails.replaceChildren();
    metricsGrid.replaceChildren();
    featuresList.replaceChildren();

    const details = [
        ["ID модели", result.model_id],
        ["Целевой столбец", result.target_column],
        ["Модель принята", result.model_accepted ? "Да" : "Нет"],
        ["Порог качества", result.threshold],
        ["ID в базе данных", result.database_model_id]
    ];

    details.forEach(([label, value]) => {
        if (value === null || value === undefined) return;

        const item = document.createElement("div");
        item.className = "detail-item";

        addTextElement(item, "span", label);
        addTextElement(item, "strong", formatValue(value));

        resultDetails.appendChild(item);
    });

    const metrics = result.metrics || {};
    const metricEntries = Object.entries(metrics);

    if (metricEntries.length === 0) {
        addTextElement(
            metricsGrid,
            "p",
            "Backend не вернул метрики для отображения."
        );
    } else {
        metricEntries.forEach(([name, value]) => {
            const item = document.createElement("div");
            item.className = "metric-item";

            addTextElement(item, "span", name);
            addTextElement(item, "strong", formatValue(value));

            metricsGrid.appendChild(item);
        });
    }

    const features = Object.entries(result.feature_importance || {})
        .sort((a, b) => Number(b[1]) - Number(a[1]));

    if (features.length === 0) {
        addTextElement(
            featuresList,
            "p",
            "Данные о важности признаков не предоставлены."
        );
    } else {
        features.forEach(([name, importance]) => {
            const item = document.createElement("div");
            item.className = "feature-item";

            addTextElement(item, "span", name);
            addTextElement(item, "span", formatValue(importance));

            featuresList.appendChild(item);
        });
    }

    resultSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

// --------------------------------------------------
// Запуск обучения: POST /api/models/train
// --------------------------------------------------

trainingForm.addEventListener("submit", async event => {
    event.preventDefault();
    hideMessage();

    if (!sessionStorage.getItem("access_token")) {
        showMessage(
            "Сначала войди в аккаунт, затем вернись к обучению.",
            "info"
        );
        return;
    }

    if (!selectedFile) {
        showMessage("Сначала выбери CSV-файл.");
        return;
    }

    const targetColumn = targetColumnInput.value.trim();

    if (!targetColumn) {
        showMessage("Укажи название целевого столбца.");
        targetColumnInput.focus();
        return;
    }

    if (csvHeaders.length && !csvHeaders.includes(targetColumn)) {
        showMessage(
            "Целевой столбец не найден среди заголовков CSV. " +
            "Выбери название из подсказок или проверь написание."
        );
        targetColumnInput.focus();
        return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("target_column", targetColumn);

    trainButton.disabled = true;
    trainButtonText.textContent = "Обучение...";
    resultSection.hidden = true;

    showMessage(
        "Запрос отправлен. Ожидаем ответ ML-сервиса. " +
        "Это может занять несколько минут.",
        "info"
    );

    try {
        const result = await apiRequest(
            `${API_BASE_URL}/models/train`,
            {
                method: "POST",
                body: formData
            }
        );

        showMessage(
            result.message || "Обработка завершена.",
            result.model_accepted ? "success" : "info"
        );

        renderTrainingResult(result);
        await loadModels();
    } catch (error) {
        showMessage(error.message || "Не удалось обучить модель.");
    } finally {
        trainButton.disabled = false;
        trainButtonText.textContent = "Обучить модель";
    }
});

// --------------------------------------------------
// Список моделей: GET /api/models
// --------------------------------------------------

async function loadModels() {
    if (!sessionStorage.getItem("access_token")) {
        modelsMessage.textContent =
            "Войди в аккаунт, чтобы увидеть свои модели.";
        modelsList.replaceChildren();
        return;
    }

    modelsMessage.textContent = "Загружаем список моделей...";
    modelsList.replaceChildren();
    refreshModelsButton.disabled = true;

    try {
        const data = await apiRequest(`${API_BASE_URL}/models`);
        const items = Array.isArray(data.items) ? data.items : [];

        if (items.length === 0) {
            modelsMessage.textContent =
                "У тебя пока нет зарегистрированных моделей.";
            return;
        }

        modelsMessage.textContent = `Всего моделей: ${data.total ?? items.length}`;

        items.forEach(model => {
            const item = document.createElement("article");
            item.className = "model-item";

            addTextElement(
                item,
                "h3",
                model.version || `Модель #${model.id}`
            );

            if (model.target_column) {
                addTextElement(
                    item,
                    "p",
                    `Целевой столбец: ${model.target_column}`
                );
            }

            addTextElement(item, "p", `ID: ${model.id}`);
            addTextElement(item, "p", `Статус: ${model.status || "—"}`);

            if (model.created_at) {
                const date = new Date(model.created_at);

                addTextElement(
                    item,
                    "p",
                    `Создана: ${
                        Number.isNaN(date.getTime())
                            ? model.created_at
                            : date.toLocaleString("ru-RU")
                    }`
                );
            }

            const badge = addTextElement(
                item,
                "span",
                model.status || "неизвестно",
                "model-status"
            );

            if (model.status === "ready") {
                badge.title = "Модель зарегистрирована как готовая";
            }

            const metricEntries = Object.entries(model.metrics || {});

            if (metricEntries.length) {
                const firstMetrics = metricEntries
                    .slice(0, 3)
                    .map(([key, value]) => `${key}: ${formatValue(value)}`)
                    .join(" · ");

                addTextElement(item, "p", firstMetrics);
            }

            modelsList.appendChild(item);
        });
    } catch (error) {
        modelsMessage.textContent =
            error.message || "Не удалось загрузить список моделей.";
    } finally {
        refreshModelsButton.disabled = false;
    }
}

refreshModelsButton.addEventListener("click", loadModels);

// Первичная загрузка списка моделей.
loadModels();
