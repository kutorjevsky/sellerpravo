from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Dict

from bot.config import COMMON_COURTS, ROLES, ROLE_EMOJI


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ── Registration ─────────────────────────────────────────────────────────────

def role_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in ROLES.items():
        builder.button(text=f"{ROLE_EMOJI[key]} {label}", callback_data=f"role:{key}")
    builder.adjust(2)
    return builder.as_markup()


# ── Main menus ────────────────────────────────────────────────────────────────

def menu_representative() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📝 Новое задание"))
    builder.row(KeyboardButton(text="📋 Мои задания"), KeyboardButton(text="📚 Архив"))
    return builder.as_markup(resize_keyboard=True)


def menu_secretary() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📋 На сегодня"), KeyboardButton(text="📋 На завтра"))
    builder.row(KeyboardButton(text="📚 Архив"), KeyboardButton(text="📝 Новое задание"))
    return builder.as_markup(resize_keyboard=True)


def menu_executor() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📋 Мои задания на сегодня"))
    builder.row(KeyboardButton(text="📅 Зарегистрировать выезд"), KeyboardButton(text="📚 Архив"))
    return builder.as_markup(resize_keyboard=True)


# ── Task creation ─────────────────────────────────────────────────────────────

def courts_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for court in COMMON_COURTS:
        builder.button(text=court, callback_data=f"court:{court[:40]}")
    builder.adjust(1)
    return builder.as_markup()


def yes_no_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да", callback_data=f"{prefix}:yes"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"{prefix}:no"),
    ]])


def skip_keyboard(action: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Пропустить ⏩", callback_data=action),
    ]])


def date_keyboard() -> InlineKeyboardMarkup:
    from datetime import date, timedelta
    from bot.utils import MONTHS_RU, DAYS_RU
    builder = InlineKeyboardBuilder()
    today = date.today()
    for i in range(1, 8):
        d = today + timedelta(days=i)
        label = f"{d.day} {MONTHS_RU[d.month]} ({DAYS_RU[d.weekday()]})"
        builder.button(text=label, callback_data=f"date:{d.isoformat()}")
    builder.adjust(2)
    return builder.as_markup()


def confirm_task_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Создать задание", callback_data="task:confirm"),
        InlineKeyboardButton(text="🗑 Отменить", callback_data="task:cancel"),
    ]])


# ── Secretary: assignment ─────────────────────────────────────────────────────

def assign_task_keyboard(task_id: int, suggested_executor_id: int = None,
                          suggested_name: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if suggested_name and suggested_executor_id:
        builder.button(
            text=f"✅ Назначить: {suggested_name}",
            callback_data=f"assign:{task_id}:{suggested_executor_id}",
        )
    builder.button(
        text="👥 Выбрать исполнителя",
        callback_data=f"choose_exec:{task_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


def executors_keyboard(task_id: int, executors: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ex in executors:
        role_label = "Курьер" if ex["role"] == "courier" else "Помощник"
        builder.button(
            text=f"{ex['name']} ({role_label})",
            callback_data=f"assign:{task_id}:{ex['id']}",
        )
    builder.button(text="◀️ Назад", callback_data=f"back_task:{task_id}")
    builder.adjust(1)
    return builder.as_markup()


# ── Executor: task actions ────────────────────────────────────────────────────

def task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done:{task_id}"),
        InlineKeyboardButton(text="❌ Не выполнено", callback_data=f"fail:{task_id}"),
    ]])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀️ Отменить", callback_data="cancel_result"),
    ]])


# ── Assistant schedule ────────────────────────────────────────────────────────

def schedule_date_keyboard() -> InlineKeyboardMarkup:
    from datetime import date, timedelta
    from bot.utils import MONTHS_RU, DAYS_RU
    builder = InlineKeyboardBuilder()
    today = date.today()
    # Show Mon/Thu of next two weeks
    for i in range(14):
        d = today + timedelta(days=i + 1)
        if d.weekday() in (0, 3):
            label = f"{d.day} {MONTHS_RU[d.month]} ({DAYS_RU[d.weekday()]})"
            builder.button(text=label, callback_data=f"sched_date:{d.isoformat()}")
    builder.adjust(2)
    return builder.as_markup()


def schedule_court_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for court in COMMON_COURTS[:-1]:  # exclude "Другое..."
        builder.button(text=court, callback_data=f"sched_court:{court[:40]}")
    builder.button(text="✏️ Ввести вручную", callback_data="sched_court:__manual__")
    builder.adjust(1)
    return builder.as_markup()


# ── Archive pagination ────────────────────────────────────────────────────────

def archive_nav_keyboard(offset: int, has_more: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if offset > 0:
        builder.button(text="◀️ Назад", callback_data=f"archive:{max(0, offset - 10)}")
    if has_more:
        builder.button(text="Вперёд ▶️", callback_data=f"archive:{offset + 10}")
    return builder.as_markup() if (offset > 0 or has_more) else None
