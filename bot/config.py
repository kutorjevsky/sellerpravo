"""
Конфигурация системы управления поручениями.
Единый источник правды — Google-таблица (реестр). Бот пишет в неё через API.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Подключение ───────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
# Учётные данные сервисного аккаунта Google: либо JSON-строкой в переменной,
# либо путём к файлу. Достаточно одного из двух.
GOOGLE_CREDENTIALS_JSON: str = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# ── Названия листов таблицы ───────────────────────────────────────────────────
SHEET_DASHBOARD = "00_Панель"
SHEET_REGISTRY = "01_Реестр"
SHEET_AGENCIES = "Справочник_Органы"
SHEET_STAFF = "Справочник_Сотрудники"
SHEET_CLIENTS = "Справочник_Клиенты"
SHEET_LOG = "Журнал"

# ── Роли пользователей ────────────────────────────────────────────────────────
ROLE_REPRESENTATIVE = "Представитель"
ROLE_SECRETARY = "Секретарь"
ROLE_COURIER = "Курьер"
ROLE_ASSISTANT = "Помощник"

ROLES = [ROLE_REPRESENTATIVE, ROLE_SECRETARY, ROLE_COURIER, ROLE_ASSISTANT]
ROLE_EMOJI = {
    ROLE_REPRESENTATIVE: "⚖️",
    ROLE_SECRETARY: "📋",
    ROLE_COURIER: "🚗",
    ROLE_ASSISTANT: "👤",
}
EXECUTOR_ROLES = (ROLE_COURIER, ROLE_ASSISTANT)
CREATOR_ROLES = (ROLE_REPRESENTATIVE, ROLE_SECRETARY)

# ── Заголовки колонок реестра (порядок важен!) ────────────────────────────────
H_ID = "ID"
H_CREATED = "Дата создания"
H_STATUS = "Статус"
H_INITIATOR = "Инициатор"
H_CLIENT = "Клиент"
H_CASE = "Номер дела"
H_ORGAN_TYPE = "Тип органа"
H_ORGAN = "Орган"
H_ADDRESS = "Адрес"
H_TASK_TYPE = "Тип поручения"
H_ACTION = "Краткое действие"
H_FULL = "Полное задание"
H_OFFICIAL = "Должностное лицо"
H_SUCCESS = "Критерий успеха"
H_ONFAIL = "При отказе"
H_POA = "Доверенность"
H_PRIORITY = "Приоритет"
H_LEGAL_DEADLINE = "Процессуальный срок"
H_PLAN_DATE = "Плановая дата"
H_MOVABLE = "Можно перенести"
H_URGENCY_REASON = "Причина срочности"
H_EXECUTOR = "Исполнитель"
H_EXECUTOR_TYPE = "Тип исполнителя"
H_ROUTE = "Маршрут/район"
H_FACT_DATE = "Фактическая дата"
H_RESULT = "Результат"
H_PROOF = "Доказательство"
H_COMMENTS = "Комментарии"
H_ACCEPTED_BY = "Принял"
H_UPDATED = "Обновлено"
H_INITIATOR_TG = "TG инициатора"   # служебная колонка для уведомлений
H_EXECUTOR_TG = "TG исполнителя"   # служебная колонка для уведомлений

REGISTRY_HEADERS = [
    H_ID, H_CREATED, H_STATUS, H_INITIATOR, H_CLIENT, H_CASE,
    H_ORGAN_TYPE, H_ORGAN, H_ADDRESS,
    H_TASK_TYPE, H_ACTION, H_FULL, H_OFFICIAL, H_SUCCESS, H_ONFAIL,
    H_POA, H_PRIORITY, H_LEGAL_DEADLINE, H_PLAN_DATE, H_MOVABLE, H_URGENCY_REASON,
    H_EXECUTOR, H_EXECUTOR_TYPE, H_ROUTE,
    H_FACT_DATE, H_RESULT, H_PROOF, H_COMMENTS, H_ACCEPTED_BY, H_UPDATED,
    H_INITIATOR_TG, H_EXECUTOR_TG,
]

STAFF_HEADERS = [
    "Telegram ID", "Имя", "Роль", "Username", "Телефон",
    "Доступность", "Доверенности", "Добавлен",
]

AGENCY_HEADERS = [
    "Тип органа", "Орган", "Адрес", "Кабинет/окно",
    "Режим приёма", "Предзапись", "Особенности", "Ссылка",
]

CLIENT_HEADERS = [
    "Клиент", "Представитель", "Внутр. номер дела", "Номер дела суда", "Примечание",
]

LOG_HEADERS = ["Время", "Кто", "Действие", "ID поручения", "Детали"]

# ── Статусы поручений ─────────────────────────────────────────────────────────
ST_NEW = "Новая заявка"
ST_CLARIFY = "Требуется уточнение"
ST_READY = "Готово к маршрутизации"
ST_ASSIGNED = "Назначено"
ST_DONE_WAIT = "Исполнено, ждёт приёмки"
ST_REVISIT = "Повторный визит"
ST_FAILED = "Не исполнено объективно"
ST_OVERDUE = "Просрочено"
ST_CANCELLED = "Отменено"
ST_ACCEPTED = "Принято"

STATUSES = [
    ST_NEW, ST_CLARIFY, ST_READY, ST_ASSIGNED, ST_DONE_WAIT,
    ST_REVISIT, ST_FAILED, ST_OVERDUE, ST_CANCELLED, ST_ACCEPTED,
]
# Активные = ещё в работе; закрытые = архив
ACTIVE_STATUSES = (ST_NEW, ST_CLARIFY, ST_READY, ST_ASSIGNED, ST_DONE_WAIT, ST_REVISIT)
CLOSED_STATUSES = (ST_FAILED, ST_OVERDUE, ST_CANCELLED, ST_ACCEPTED)

STATUS_EMOJI = {
    ST_NEW: "🆕", ST_CLARIFY: "❓", ST_READY: "📦", ST_ASSIGNED: "📌",
    ST_DONE_WAIT: "📨", ST_REVISIT: "🔁", ST_FAILED: "🚫",
    ST_OVERDUE: "⏰", ST_CANCELLED: "❌", ST_ACCEPTED: "✅",
}

# ── Справочные значения (для кнопок и выпадающих списков) ─────────────────────
ORGAN_TYPES = [
    "Суд общей юрисдикции", "Арбитражный суд", "Мировой суд",
    "МФЦ", "ОСП (приставы)", "ГИБДД/ГАИ", "СФР", "ФНС",
    "Росреестр", "Нотариус", "Банк", "Военкомат", "Почта", "Иное",
]

TASK_TYPES = [
    "Подача", "Получение", "Ознакомление",
    "Получение информации", "Передача", "Почта", "Иное",
]

PRIORITIES = ["Критический", "Высокий", "Обычный", "Низкий"]
PRIORITY_EMOJI = {
    "Критический": "🔴", "Высокий": "🟠", "Обычный": "🟢", "Низкий": "⚪",
}

EXECUTOR_TYPES = ["Курьер", "Помощник", "Представитель"]

YES_NO = ["Да", "Нет"]
