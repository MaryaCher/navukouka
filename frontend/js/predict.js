const API_BASE_URL = "http://127.0.0.1:8001/api";

const token = sessionStorage.getItem("access_token");

if (!token) {
    window.location.href = "login.html";
} else {
    initializePredictionPage();
}

function initializePredictionPage() {
    const singleModeButton = document.getElementById("singleModeButton");
    const batchModeButton = document.getElementById("batchModeButton");

    const singleSection = document.getElementById("singleSection");
    const batchSection = document.getElementById("batchSection");

    const predictForm = document.getElementById("predictForm");
    const batchForm = document.getElementById("batchForm");

    const predictButton = document.getElementById("predictButton");
    const batchButton = document.getElementById("batchButton");

    const csvFile = document.getElementById("csvFile");
    const fileName = document.getElementById("fileName");
    const fileHint = document.getElementById("fileHint");

    const singleError = document.getElementById("singleError");
    const batchError = document.getElementById("batchError");

    const singleResult = document.getElementById("singleResult");
    const batchResult = document.getElementById("batchResult");

    const MAX_FILE_SIZE = 20 * 1024 * 1024;

    // ------------------------------
    // Общие вспомогательные функции
    // ------------------------------

    function showMessage(element, message) {
        element.textContent = message;
        element.hidden = false;
    }

    function hideMessage(element) {
        element.textContent = "";
        element.hidden = true;
    }

    function formatError(data, fallback) {
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

    async function readResponse(response) {
        const text = await response.text();

        let data = {};

        if (text) {
            try {
                data = JSON.parse(text);
            } catch {
                data = { detail: text };
            }
        }

        if (response.status === 401) {
            sessionStorage.removeItem("access_token");
            window.location.href = "login.html";

            throw new Error("Сессия завершена. Войдите снова.");
        }

        if (!response.ok) {
            throw new Error(
                formatError(data, `Ошибка сервера: ${response.status}`)
            );
        }

        return data;
    }

    async function apiRequest(url, options) {
        const response = await fetch(url, {
            ...options,
            headers: {
                Authorization: `Bearer ${token}`,
                ...(options.headers || {})
            }
        });

        return readResponse(response);
    }

    function formatPercent(value) {
        const number = Number(value);

        if (!Number.isFinite(number)) {
            return "—";
        }

        return `${number.toLocaleString("ru-RU", {
            maximumFractionDigits: 2
        })}%`;
    }

    function getProbabilityPercent(result) {
        if (
            result.probability_percent !== undefined &&
            result.probability_percent !== null
        ) {
            return Number(result.probability_percent);
        }

        if (
            result.probability !== undefined &&
            result.probability !== null
        ) {
            return Number(result.probability) * 100;
        }

        return NaN;
    }

    function formatPrediction(value) {
        if (value === 1 || value === true || value === "1") {
            return "Да (1)";
        }

        if (value === 0 || value === false || value === "0") {
            return "Нет (0)";
        }

        if (value === null || value === undefined || value === "") {
            return "—";
        }

        return String(value);
    }

    function formatThreshold(value) {
        if (value === null || value === undefined) {
            return "—";
        }

        const number = Number(value);

        if (!Number.isFinite(number)) {
            return String(value);
        }

        return formatPercent(number * 100);
    }

    function switchMode(mode) {
        const isSingle = mode === "single";

        singleSection.hidden = !isSingle;
        batchSection.hidden = isSingle;

        singleModeButton.classList.toggle("active", isSingle);
        batchModeButton.classList.toggle("active", !isSingle);

        singleModeButton.setAttribute("aria-pressed", String(isSingle));
        batchModeButton.setAttribute("aria-pressed", String(!isSingle));
    }

    singleModeButton.addEventListener("click", () => {
        switchMode("single");
    });

    batchModeButton.addEventListener("click", () => {
        switchMode("batch");
    });

    // ------------------------------
    // Выход из аккаунта
    // ------------------------------

    document.getElementById("logoutButton").addEventListener("click", () => {
        sessionStorage.removeItem("access_token");
        window.location.href = "login.html";
    });

    // ------------------------------
    // Одиночный прогноз
    // POST /api/predict
    // ------------------------------

    predictForm.addEventListener("submit", async event => {
        event.preventDefault();

        hideMessage(singleError);
        singleResult.hidden = true;

        if (!predictForm.reportValidity()) {
            return;
        }

        const formData = new FormData(predictForm);

        const userData = {
            age: Number(formData.get("age")),
            income: Number(formData.get("income")),
            education: formData.get("education").trim(),
            industry: formData.get("industry").trim(),
            profession: formData.get("profession").trim(),
            marital_status: formData.get("marital_status").trim(),
            gender: formData.get("gender").trim(),
            residence_type: formData.get("residence_type").trim(),
            nationality: formData.get("nationality").trim(),
            children_count: Number(formData.get("children_count"))
        };

        predictButton.disabled = true;
        predictButton.textContent = "Выполняется прогнозирование...";

        try {
            const result = await apiRequest(
                `${API_BASE_URL}/predict`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        user_data: userData
                    })
                }
            );

            const probability = getProbabilityPercent(result);

            document.getElementById("probabilityValue").textContent =
                formatPercent(probability);

            const probabilityBar = document.getElementById("probabilityBar");

            probabilityBar.style.width = Number.isFinite(probability)
                ? `${Math.max(0, Math.min(100, probability))}%`
                : "0%";

            document.getElementById("predictionValue").textContent =
                formatPrediction(result.prediction);

            document.getElementById("thresholdValue").textContent =
                formatThreshold(result.threshold);

            singleResult.hidden = false;

            singleResult.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        } catch (error) {
            showMessage(
                singleError,
                error.message || "Не удалось получить прогноз."
            );
        } finally {
            predictButton.disabled = false;
            predictButton.innerHTML =
                'Получить прогноз <span aria-hidden="true">↗</span>';
        }
    });

    document.getElementById("newPredictionButton")
        .addEventListener("click", () => {
            singleResult.hidden = true;
            hideMessage(singleError);

            predictForm.reset();

            predictForm.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        });

    // ------------------------------
    // Выбор и проверка CSV
    // ------------------------------

    csvFile.addEventListener("change", () => {
        hideMessage(batchError);

        const file = csvFile.files[0];

        if (!file) {
            fileName.textContent = "Выберите CSV-файл";
            fileHint.textContent =
                "Нажмите здесь, чтобы выбрать файл с компьютера";
            return;
        }

        fileName.textContent = file.name;
        fileHint.textContent =
            `${(file.size / (1024 * 1024)).toFixed(2)} МБ`;

        if (!file.name.toLowerCase().endsWith(".csv")) {
            csvFile.value = "";
            fileName.textContent = "Выберите CSV-файл";
            fileHint.textContent =
                "Нажмите здесь, чтобы выбрать файл с компьютера";

            showMessage(batchError, "Загрузите файл с расширением .csv.");
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            csvFile.value = "";
            fileName.textContent = "Выберите CSV-файл";
            fileHint.textContent =
                "Нажмите здесь, чтобы выбрать файл с компьютера";

            showMessage(
                batchError,
                "Размер файла не должен превышать 20 МБ."
            );
            return;
        }

        if (file.size === 0) {
            csvFile.value = "";
            fileName.textContent = "Выберите CSV-файл";
            fileHint.textContent =
                "Нажмите здесь, чтобы выбрать файл с компьютера";

            showMessage(batchError, "Выбран пустой файл.");
        }
    });

    // ------------------------------
    // Пакетный прогноз
    // POST /api/predictions/batch
    // ------------------------------

    batchForm.addEventListener("submit", async event => {
        event.preventDefault();

        hideMessage(batchError);
        batchResult.hidden = true;

        const file = csvFile.files[0];

        if (!file) {
            showMessage(batchError, "Сначала выберите CSV-файл.");
            return;
        }

        if (!file.name.toLowerCase().endsWith(".csv")) {
            showMessage(batchError, "Загрузите файл с расширением .csv.");
            return;
        }

        if (file.size === 0 || file.size > MAX_FILE_SIZE) {
            showMessage(
                batchError,
                "Файл должен быть непустым и не превышать 20 МБ."
            );
            return;
        }

        batchButton.disabled = true;
        batchButton.textContent = "Обрабатываем файл...";

        const body = new FormData();
        body.append("file", file);

        try {
            const result = await apiRequest(
                `${API_BASE_URL}/predictions/batch`,
                {
                    method: "POST",
                    body
                }
            );

            renderBatchResults(result);

            batchResult.hidden = false;

            batchResult.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        } catch (error) {
            showMessage(
                batchError,
                error.message || "Не удалось выполнить пакетный прогноз."
            );
        } finally {
            batchButton.disabled = false;
            batchButton.innerHTML =
                'Запустить пакетный прогноз <span aria-hidden="true">↗</span>';
        }
    });

    // ------------------------------
    // Создание DOM-элементов карточек
    // ------------------------------

    function createCardElement(tag, className, text) {
        const element = document.createElement(tag);

        if (className) {
            element.className = className;
        }

        if (text !== undefined && text !== null) {
            element.textContent = String(text);
        }

        return element;
    }

    function formatFieldValue(value) {
        if (value === null || value === undefined || value === "") {
            return "Не указано";
        }

        if (typeof value === "object") {
            return JSON.stringify(value);
        }

        return String(value);
    }

    // ------------------------------
    // Отображение результатов карточками
    // ------------------------------

    function renderBatchResults(result) {
        // Статистика пакетной обработки
        document.getElementById("batchStatus").textContent =
            result.status ?? "—";

        document.getElementById("batchTotal").textContent =
            result.total_records ?? 0;

        document.getElementById("batchSuccessful").textContent =
            result.successful_records ?? 0;

        document.getElementById("batchFailed").textContent =
            result.failed_records ?? 0;

        document.getElementById("batchId").textContent =
            result.batch_id ?? "—";

        // Контейнер карточек: в HTML это должен быть div, не tbody.
        const resultsContainer =
            document.getElementById("batchResultsBody");

        resultsContainer.replaceChildren();

        const results = Array.isArray(result.results)
            ? result.results
            : [];

        const notice = document.getElementById("batchResultsNotice");

        hideMessage(notice);

        if (results.length === 0) {
            showMessage(
                notice,
                "Сервер не вернул список результатов. Проверьте статус и ответ API."
            );
            return;
        }

        const fieldLabels = {
            age: "Возраст",
            income: "Доход",
            education: "Образование",
            industry: "Отрасль",
            profession: "Профессия",
            marital_status: "Семейное положение",
            gender: "Пол",
            residence_type: "Тип проживания",
            nationality: "Гражданство",
            children_count: "Количество детей"
        };

        results.forEach((item, index) => {
            const card = createCardElement(
                "article",
                "batch-record-card"
            );

            // Данные исходной записи, переданные backend.
            const inputData =
                item.input_data ??
                item.user_data ??
                item.features ??
                item.user ??
                null;

            const hasError = Boolean(
                item.error ||
                item.error_message ||
                item.success === false ||
                item.status === "failed" ||
                item.status === "error"
            );

            const hasPrediction =
                item.prediction !== null &&
                item.prediction !== undefined &&
                item.prediction !== "";

            const isSuccessful = !hasError && hasPrediction;

            // Заголовок карточки
            const header = createCardElement(
                "div",
                "batch-card-header"
            );

            const number = createCardElement(
                "div",
                "batch-card-number"
            );

            number.appendChild(
                createCardElement(
                    "span",
                    "batch-card-index",
                    String(index + 1).padStart(2, "0")
                )
            );

            number.appendChild(
                createCardElement(
                    "span",
                    "",
                    `ЗАПИСЬ № ${index + 1}`
                )
            );

            const status = createCardElement(
                "span",
                `batch-card-status${isSuccessful ? "" : " failed"}`,
                isSuccessful ? "✓ Успешно" : "✕ Ошибка"
            );

            header.append(number, status);
            card.appendChild(header);

            // Основная часть карточки
            const cardBody = createCardElement(
                "div",
                "batch-card-body"
            );

            cardBody.appendChild(
                createCardElement(
                    "h4",
                    "batch-card-section-title",
                    "Данные пользователя"
                )
            );

            const hasInputData =
                inputData &&
                typeof inputData === "object" &&
                !Array.isArray(inputData) &&
                Object.keys(inputData).length > 0;

            if (hasInputData) {
                const fields = createCardElement(
                    "div",
                    "batch-card-fields"
                );

                Object.entries(inputData).forEach(([key, value]) => {
                    const field = createCardElement(
                        "div",
                        "batch-card-field"
                    );

                    const label =
                        fieldLabels[key] ||
                        key.replace(/_/g, " ");

                    field.appendChild(
                        createCardElement(
                            "span",
                            "batch-card-field-label",
                            label
                        )
                    );

                    field.appendChild(
                        createCardElement(
                            "span",
                            "batch-card-field-value",
                            formatFieldValue(value)
                        )
                    );

                    fields.appendChild(field);
                });

                cardBody.appendChild(fields);
            } else {
                cardBody.appendChild(
                    createCardElement(
                        "div",
                        "batch-card-empty",
                        "Исходные данные для этой записи не возвращены сервером."
                    )
                );
            }

            // Блок результата модели
            const resultSection = createCardElement(
                "div",
                "batch-card-result"
            );

            if (isSuccessful) {
                const resultTop = createCardElement(
                    "div",
                    "batch-card-result-top"
                );

                // Прогноз
                const predictionBlock = createCardElement(
                    "div",
                    ""
                );

                predictionBlock.appendChild(
                    createCardElement(
                        "span",
                        "batch-card-prediction-label",
                        "Прогноз модели"
                    )
                );

                predictionBlock.appendChild(
                    createCardElement(
                        "span",
                        "batch-card-prediction",
                        formatPrediction(item.prediction)
                    )
                );

                // Вероятность
                const probabilityBlock = createCardElement(
                    "div",
                    ""
                );

                probabilityBlock.appendChild(
                    createCardElement(
                        "span",
                        "batch-card-probability-label",
                        "Вероятность"
                    )
                );

                const probability = getProbabilityPercent(item);

                const validProbability =
                    Number.isFinite(probability) &&
                    probability >= 0 &&
                    probability <= 100;

                probabilityBlock.appendChild(
                    createCardElement(
                        "div",
                        "batch-card-probability",
                        validProbability
                            ? formatPercent(probability)
                            : "—"
                    )
                );

                resultTop.append(
                    predictionBlock,
                    probabilityBlock
                );

                resultSection.appendChild(resultTop);

                // Полоса вероятности
                const progress = createCardElement(
                    "div",
                    "batch-card-progress"
                );

                progress.setAttribute("role", "progressbar");
                progress.setAttribute(
                    "aria-label",
                    "Вероятность целевого действия"
                );
                progress.setAttribute("aria-valuemin", "0");
                progress.setAttribute("aria-valuemax", "100");
                progress.setAttribute(
                    "aria-valuenow",
                    validProbability ? String(probability) : "0"
                );

                const fill = createCardElement(
                    "div",
                    "batch-card-progress-fill"
                );

                fill.style.width = validProbability
                    ? `${probability}%`
                    : "0%";

                progress.appendChild(fill);
                resultSection.appendChild(progress);
            } else {
                const errorText =
                    item.error ||
                    item.error_message ||
                    "Не удалось получить прогноз для этой записи.";

                resultSection.appendChild(
                    createCardElement(
                        "div",
                        "batch-card-error",
                        errorText
                    )
                );
            }

            cardBody.appendChild(resultSection);
            card.appendChild(cardBody);

            resultsContainer.appendChild(card);
        });
    }

    // ------------------------------
    // Новый пакетный прогноз
    // ------------------------------

    document.getElementById("newBatchButton")
        .addEventListener("click", () => {
            batchResult.hidden = true;
            hideMessage(batchError);

            batchForm.reset();

            fileName.textContent = "Выберите CSV-файл";
            fileHint.textContent =
                "Нажмите здесь, чтобы выбрать файл с компьютера";

            batchForm.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        });
}