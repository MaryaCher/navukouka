
/*
 * Адрес backend API.
 * Для локальной разработки FastAPI запускается на порту 8000.
 * При развёртывании замени адрес на URL своего backend.
 */
const API_BASE_URL = "http://127.0.0.1:8001/api";

const registerForm = document.getElementById("registerForm");
const loginForm = document.getElementById("loginForm");
const authMessage = document.getElementById("authMessage");

function showMessage(message, isSuccess = false) {
    if (!authMessage) return;

    authMessage.textContent = message;
    authMessage.classList.add("is-visible");
    authMessage.classList.toggle("is-success", isSuccess);
}

function clearMessage() {
    if (!authMessage) return;

    authMessage.textContent = "";
    authMessage.classList.remove("is-visible", "is-success");
}

async function apiRequest(endpoint, payload) {
    let response;

    try {
        response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(payload)
        });
    } catch (error) {
        throw new Error(
            "Не удалось связаться с сервером. Проверь, запущен ли backend, и настройки CORS."
        );
    }

    let result;

    try {
        result = await response.json();
    } catch {
        throw new Error(
            `Сервер вернул некорректный ответ (HTTP ${response.status}).`
        );
    }

    if (!response.ok) {
        const detail = result.detail;

        if (typeof detail === "string") {
            throw new Error(detail);
        }

        if (Array.isArray(detail)) {
            throw new Error(
                detail.map(item => item.msg || "Ошибка проверки данных").join("; ")
            );
        }

        throw new Error(`Ошибка сервера (HTTP ${response.status}).`);
    }

    return result;
}

// Регистрация
if (registerForm) {
    registerForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearMessage();

        const username = registerForm.elements.username.value.trim();
        const password = registerForm.elements.password.value;
        const passwordConfirm =
            registerForm.elements.passwordConfirm.value;

        if (username.length < 3 || username.length > 100) {
            showMessage(
                "Имя пользователя должно содержать от 3 до 100 символов."
            );
            return;
        }

        if (password.length < 8 || password.length > 128) {
            showMessage(
                "Пароль должен содержать от 8 до 128 символов."
            );
            return;
        }

        if (password !== passwordConfirm) {
            showMessage("Пароли не совпадают.");
            return;
        }

        const submitButton = registerForm.querySelector(
            'button[type="submit"]'
        );
        submitButton.disabled = true;

        try {
            const result = await apiRequest("/auth/register", {
                username,
                password
            });

            showMessage(
                `Аккаунт «${result.username}» создан. Сейчас перейдём ко входу.`,
                true
            );

            registerForm.reset();

            // После регистрации пользователь отдельно входит в систему.
            window.setTimeout(() => {
                window.location.href = "login.html";
            }, 1200);
        } catch (error) {
            showMessage(error.message);
        } finally {
            submitButton.disabled = false;
        }
    });
}

// Авторизация
if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearMessage();

        const username = loginForm.elements.username.value.trim();
        const password = loginForm.elements.password.value;

        if (username.length < 3 || username.length > 100) {
            showMessage(
                "Имя пользователя должно содержать от 3 до 100 символов."
            );
            return;
        }

        if (!password || password.length > 128) {
            showMessage("Введи пароль длиной не более 128 символов.");
            return;
        }

        const submitButton = loginForm.querySelector(
            'button[type="submit"]'
        );
        submitButton.disabled = true;

        try {
            const result = await apiRequest("/auth/login", {
                username,
                password
            });

            // Токен живёт в текущей вкладке и удаляется при её закрытии.
            sessionStorage.setItem("access_token", result.access_token);

            showMessage("Вход выполнен успешно.", true);

            /*
             * Временно направляем на главную страницу.
             * Позже заменим переход на личный кабинет.
             */
            window.setTimeout(() => {
                window.location.href = "train.html";
            }, 500);
        } catch (error) {
            showMessage(error.message);
        } finally {
            submitButton.disabled = false;
        }
    });
}
