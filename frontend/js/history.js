
"use strict";

const API_BASE = "http://127.0.0.1:8001/api";

const elements = {
    message: document.getElementById("historyMessage"),
    description: document.getElementById("historyDescription"),
    total: document.getElementById("totalHistory"),
    visible: document.getElementById("visibleHistory"),
    batches: document.getElementById("batchHistory"),
    tableBody: document.getElementById("historyTableBody"),
    search: document.getElementById("historySearch"),
    typeFilter: document.getElementById("typeFilter"),
    predictionFilter: document.getElementById("predictionFilter"),
    pageSize: document.getElementById("pageSize"),
    refresh: document.getElementById("refreshHistory"),
    previous: document.getElementById("previousPage"),
    next: document.getElementById("nextPage"),
    pageDescription: document.getElementById("pageDescription"),
    empty: document.getElementById("historyEmpty"),
    emptyDescription: document.getElementById("emptyDescription"),
    panel: document.querySelector(".history-panel"),
    logout: document.getElementById("logoutButton"),
    authLink: document.getElementById("authLink"),
};

const state = {
    items: [],
    total: 0,
    offset: 0,
    limit: Number(elements.pageSize.value) || 50,
    loading: false,
};

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    })[char]);
}

function getToken() {
    return sessionStorage.getItem("access_token");
}

function setMessage(message = "", type = "") {
    elements.message.textContent = message;
    elements.message.className = "history-message";

    if (type) {
        elements.message.classList.add(`message-${type}`);
    }
}

function formatDate(value) {
    if (!value) {
        return { date: "—", time: "" };
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return { date: String(value), time: "" };
    }

    return {
        date: date.toLocaleDateString("ru-RU", {
            day: "2-digit",
            month: "short",
            year: "numeric",
        }),
        time: date.toLocaleTimeString("ru-RU", {
            hour: "2-digit",
            minute: "2-digit",
        }),
    };
}

function formatProbability(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    // Backend хранит вероятность в диапазоне 0..1.
    const percent = number >= 0 && number <= 1
        ? number * 100
        : number;

    return `${percent.toLocaleString("ru-RU", {
        maximumFractionDigits: 2,
    })}%`;
}

function getRecordType(record) {
    return record.batch_id != null ? "batch" : "single";
}

function getModelLabel(record) {
    if (record.model_version != null) {
        return String(record.model_version);
    }

    if (record.model_version_id != null) {
        return `ID ${record.model_version_id}`;
    }

    return "Не указана";
}

function getSearchText(record) {
    return [
        record.id,
        record.batch_id,
        record.model_version_id,
        record.model_version,
        record.prediction,
        record.probability,
        record.created_at,
        JSON.stringify(record.input_data ?? {}),
    ].join(" ").toLowerCase();
}

function getFilteredRecords() {
    const search = elements.search.value.trim().toLowerCase();
    const type = elements.typeFilter.value;
    const prediction = elements.predictionFilter.value;

    return state.items.filter((record) => {
        if (type !== "all" && getRecordType(record) !== type) {
            return false;
        }

        if (
            prediction !== "all"
            && String(record.prediction) !== prediction
        ) {
            return false;
        }

        if (search && !getSearchText(record).includes(search)) {
            return false;
        }

        return true;
    });
}

function renderDetails(record) {
    const inputData = JSON.stringify(
        record.input_data ?? {},
        null,
        2,
    );

    const prediction = escapeHtml(record.prediction);
    const probability = escapeHtml(formatProbability(record.probability));
    const model = escapeHtml(getModelLabel(record));
    const batchId = record.batch_id == null
        ? "Одиночный прогноз"
        : `Пакет #${escapeHtml(record.batch_id)}`;

    return `
        <tr class="history-details-row" id="details-${record.id}" hidden>
            <td colspan="7">
                <div class="history-details-content">
                    <h3 class="history-details-heading">
                        Подробности записи #${escapeHtml(record.id)}
                    </h3>

                    <div class="history-details-grid">
                        <div class="history-detail-field">
                            <span class="history-detail-label">ID записи</span>
                            <strong class="history-detail-value">
                                #${escapeHtml(record.id)}
                            </strong>
                        </div>

                        <div class="history-detail-field">
                            <span class="history-detail-label">Тип / пакет</span>
                            <strong class="history-detail-value">
                                ${batchId}
                            </strong>
                        </div>

                        <div class="history-detail-field">
                            <span class="history-detail-label">Результат</span>
                            <strong class="history-detail-value">
                                Класс ${prediction}
                            </strong>
                        </div>

                        <div class="history-detail-field">
                            <span class="history-detail-label">Вероятность</span>
                            <strong class="history-detail-value">
                                ${probability}
                            </strong>
                        </div>

                        <div class="history-detail-field">
                            <span class="history-detail-label">ID версии модели</span>
                            <strong class="history-detail-value">
                                ${model}
                            </strong>
                        </div>

                        <div class="history-detail-field">
                            <span class="history-detail-label">Дата создания</span>
                            <strong class="history-detail-value">
                                ${escapeHtml(record.created_at ?? "—")}
                            </strong>
                        </div>
                    </div>

                    <h3 class="history-details-heading">Входные данные</h3>
                    <pre class="history-json">${escapeHtml(inputData)}</pre>
                </div>
            </td>
        </tr>
    `;
}

function renderRow(record) {
    const date = formatDate(record.created_at);
    const type = getRecordType(record);
    const resultClass = String(record.prediction) === "1"
        ? "result-positive"
        : "";

    const typeLabel = type === "batch"
        ? "Пакетный"
        : "Одиночный";

    const model = getModelLabel(record);

    return `
        <tr class="history-main-row" data-record-id="${escapeHtml(record.id)}">
            <td>
                <span class="history-record-id">
                    #${escapeHtml(record.id)}
                </span>
            </td>

            <td>
                <div class="history-date">
                    ${escapeHtml(date.date)}
                    <span>${escapeHtml(date.time)}</span>
                </div>
            </td>

            <td>
                <span class="history-type type-${type}">
                    <span class="history-type-mark"></span>
                    ${typeLabel}
                </span>
            </td>

            <td>
                <span class="history-result ${resultClass}">
                    Класс ${escapeHtml(record.prediction)}
                </span>
            </td>

            <td>
                <span class="history-probability">
                    ${escapeHtml(formatProbability(record.probability))}
                </span>
            </td>

            <td>
                <span class="history-model">
                    ${escapeHtml(model)}
                </span>
            </td>

            <td>
                <button
                    class="history-details-button"
                    type="button"
                    data-toggle-details="${escapeHtml(record.id)}"
                    aria-expanded="false"
                    aria-controls="details-${escapeHtml(record.id)}"
                    aria-label="Показать подробности записи ${escapeHtml(record.id)}"
                >+</button>
            </td>
        </tr>

        ${renderDetails(record)}
    `;
}

function render() {
    const filtered = getFilteredRecords();

    elements.total.textContent = state.total.toLocaleString("ru-RU");
    elements.visible.textContent = filtered.length.toLocaleString("ru-RU");

    elements.batches.textContent = state.items.filter(
        (record) => getRecordType(record) === "batch",
    ).length.toLocaleString("ru-RU");

    elements.description.textContent =
        `Записи ${state.total === 0 ? 0 : state.offset + 1}–` +
        `${Math.min(state.offset + state.items.length, state.total)} из ${state.total}`;

    elements.pageDescription.textContent =
        `Страница ${Math.floor(state.offset / state.limit) + 1}`;

    elements.previous.disabled = state.loading || state.offset === 0;

    elements.next.disabled =
        state.loading || state.offset + state.items.length >= state.total;

    elements.refresh.disabled = state.loading;

    elements.tableBody.innerHTML = "";

    if (state.total === 0) {
        elements.panel.hidden = true;
        elements.empty.hidden = false;
        elements.emptyDescription.textContent =
            "Выполни первый прогноз — и он появится в журнале.";
        return;
    }

    elements.panel.hidden = false;
    elements.empty.hidden = true;

    if (filtered.length === 0) {
        elements.tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="history-table-placeholder">
                    По заданным условиям на этой странице ничего не найдено.
                    Попробуй изменить фильтры или перейти на другую страницу.
                </td>
            </tr>
        `;
        return;
    }

    elements.tableBody.innerHTML = filtered.map(renderRow).join("");
}

async function loadHistory() {
    const token = getToken();

    if (!token) {
        window.location.href = "login.html";
        return;
    }

    state.loading = true;
    elements.refresh.disabled = true;
    elements.previous.disabled = true;
    elements.next.disabled = true;
    setMessage("Загружаем историю прогнозов...");

    try {
        const params = new URLSearchParams({
            limit: String(state.limit),
            offset: String(state.offset),
        });

        const response = await fetch(
            `${API_BASE}/predictions/history?${params.toString()}`,
            {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${token}`,
                    Accept: "application/json",
                },
            },
        );

        if (response.status === 401 || response.status === 403) {
            sessionStorage.removeItem("access_token");
            window.location.href = "login.html";
            return;
        }

        if (!response.ok) {
            let detail = "Не удалось загрузить историю прогнозов.";

            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    detail = errorData.detail;
                }
            } catch {
                // Используем сообщение по умолчанию.
            }

            throw new Error(detail);
        }

        const data = await response.json();

        state.items = Array.isArray(data.items) ? data.items : [];
        state.total = Number(data.total) || 0;

        setMessage("");
        render();
    } catch (error) {
        setMessage(
            error.message || "Ошибка при загрузке истории.",
            "error",
        );

        elements.tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="history-table-placeholder">
                    Не удалось получить записи. Проверь backend и попробуй обновить журнал.
                </td>
            </tr>
        `;
    } finally {
        state.loading = false;
        render();
    }
}

elements.refresh.addEventListener("click", () => {
    loadHistory();
});

elements.previous.addEventListener("click", () => {
    if (state.offset === 0 || state.loading) {
        return;
    }

    state.offset = Math.max(0, state.offset - state.limit);
    loadHistory();
});

elements.next.addEventListener("click", () => {
    if (state.offset + state.items.length >= state.total || state.loading) {
        return;
    }

    state.offset += state.limit;
    loadHistory();
});

elements.pageSize.addEventListener("change", () => {
    state.limit = Number(elements.pageSize.value) || 50;
    state.offset = 0;
    loadHistory();
});

elements.search.addEventListener("input", render);
elements.typeFilter.addEventListener("change", render);
elements.predictionFilter.addEventListener("change", render);

elements.tableBody.addEventListener("click", (event) => {
    const button = event.target.closest("[data-toggle-details]");

    if (!button) {
        return;
    }

    const id = button.dataset.toggleDetails;
    const details = document.getElementById(`details-${id}`);
    const mainRow = button.closest(".history-main-row");

    if (!details) {
        return;
    }

    const willOpen = details.hidden;
    details.hidden = !willOpen;
    button.setAttribute("aria-expanded", String(willOpen));
    button.textContent = willOpen ? "−" : "+";
    mainRow?.classList.toggle("is-expanded", willOpen);
});

if (elements.logout) {
    elements.logout.hidden = !getToken();

    elements.logout.addEventListener("click", () => {
        sessionStorage.removeItem("access_token");
        window.location.href = "login.html";
    });
}

if (elements.authLink) {
    elements.authLink.hidden = Boolean(getToken());
}

loadHistory();
