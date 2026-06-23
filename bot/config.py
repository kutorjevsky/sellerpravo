import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/tasks.db")

ROLES = {
    "representative": "Представитель",
    "secretary": "Секретарь",
    "courier": "Курьер",
    "assistant": "Помощник",
}

ROLE_EMOJI = {
    "representative": "⚖️",
    "secretary": "📋",
    "courier": "🚗",
    "assistant": "👤",
}

EXECUTORS = ("courier", "assistant")
TASK_CREATORS = ("representative", "secretary")
ADMINS = ("secretary",)

STATUS_LABELS = {
    "pending": "⏳ Ожидает назначения",
    "assigned": "📌 Назначено",
    "in_progress": "🔄 Выполняется",
    "done": "✅ Выполнено",
    "failed": "❌ Не выполнено",
}

COMMON_COURTS = [
    "Арбитражный суд г. Москвы",
    "Девятый ААС",
    "Московский городской суд",
    "Пресненский районный суд",
    "Тверской районный суд",
    "Замоскворецкий районный суд",
    "Хамовнический районный суд",
    "МФЦ",
    "Росреестр",
    "ФНС",
    "Другое...",
]
