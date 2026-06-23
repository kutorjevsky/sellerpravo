"""Все клавиатуры бота."""
from datetime import date, timedelta
from typing import Dict, List

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from bot import config as cfg
from bot.utils import MONTHS_RU, DAYS_RU


def remove_kb():
    return ReplyKeyboardRemove()


# ── Главные меню по ролям ─────────────────────────────────────────────────────

def menu_representative() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="➕ Новое поручение"))
    b.row(KeyboardButton(text="📋 Мои поручения"), KeyboardButton(text="🔍 Поиск"))
    return b.as_markup(resize_keyboard=True)


def menu_secretary() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="📥 Новые заявки"), KeyboardButton(text="🗓 На завтра"))
    b.row(KeyboardButton(text="📋 В работе"), KeyboardButton(text="🔍 Поиск"))
    b.row(KeyboardButton(text="➕ Новое поручение"))
    return b.as_markup(resize_keyboard=True)


def menu_executor() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="📋 Мои поручения"))
    b.row(KeyboardButton(text="🔍 Поиск"))
    return b.as_markup(resize_keyboard=True)


# ── Регистрация ───────────────────────────────────────────────────────────────

def role_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for r in cfg.ROLES:
        b.button(text=f"{cfg.ROLE_EMOJI[r]} {r}", callback_data=f"reg_role:{r}")
    b.adjust(2)
    return b.as_markup()


# ── Создание поручения ────────────────────────────────────────────────────────

def organ_type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in cfg.ORGAN_TYPES:
        b.button(text=t, callback_data=f"otype:{t}")
    b.adjust(2)
    return b.as_markup()


def task_type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in cfg.TASK_TYPES:
        b.button(text=t, callback_data=f"ttype:{t}")
    b.adjust(2)
    return b.as_markup()


def priority_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in cfg.PRIORITIES:
        b.button(text=f"{cfg.PRIORITY_EMOJI[p]} {p}", callback_data=f"prio:{p}")
    b.adjust(2)
    return b.as_markup()


def organ_suggest_kb(agencies: List[Dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for a in agencies[:8]:
        name = a.get("Орган", "")
        if name:
            b.button(text=name[:40], callback_data=f"organ:{name[:55]}")
    b.button(text="✏️ Ввести вручную", callback_data="organ:__manual__")
    b.adjust(1)
    return b.as_markup()


def yes_no_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да", callback_data=f"{prefix}:Да"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"{prefix}:Нет"),
    ]])


def skip_kb(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Пропустить ⏩", callback_data=action),
    ]])


def deadline_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    today = date.today()
    for i in range(1, 8):
        d = today + timedelta(days=i)
        b.button(
            text=f"{d.day} {MONTHS_RU[d.month]} ({DAYS_RU[d.weekday()]})",
            callback_data=f"ddl:{d.isoformat()}",
        )
    b.button(text="✏️ Свой вариант", callback_data="ddl:__manual__")
    b.button(text="Без срока", callback_data="ddl:__none__")
    b.adjust(2)
    return b.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Создать", callback_data="newtask:ok"),
        InlineKeyboardButton(text="🗑 Отмена", callback_data="newtask:cancel"),
    ]])


def plan_date_kb(task_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    today = date.today()
    for i in range(0, 7):
        d = today + timedelta(days=i)
        label = "сегодня" if i == 0 else ("завтра" if i == 1 else
                f"{d.day} {MONTHS_RU[d.month]} ({DAYS_RU[d.weekday()]})")
        b.button(text=label, callback_data=f"plan:{task_id}:{d.isoformat()}")
    b.adjust(2)
    return b.as_markup()


# ── Карточка поручения: действия по ролям ─────────────────────────────────────

def card_kb(task: Dict, role: str, is_creator: bool, is_assignee: bool) -> InlineKeyboardMarkup:
    tid = task.get(cfg.H_ID)
    st = task.get(cfg.H_STATUS)
    b = InlineKeyboardBuilder()

    # Секретарь
    if role == cfg.ROLE_SECRETARY:
        if st in (cfg.ST_NEW, cfg.ST_CLARIFY, cfg.ST_READY, cfg.ST_ASSIGNED, cfg.ST_REVISIT):
            b.button(text="👤 Назначить исполнителя", callback_data=f"assign:{tid}")
            b.button(text="🗓 План-дата", callback_data=f"setplan:{tid}")
        b.button(text="🔁 Сменить статус", callback_data=f"status:{tid}")

    # Исполнитель
    if is_assignee and st in (cfg.ST_ASSIGNED, cfg.ST_REVISIT):
        b.button(text="✅ Исполнено", callback_data=f"result:{tid}")
        b.button(text="🔁 Нужен повторный визит", callback_data=f"revisit:{tid}")
        b.button(text="🚫 Не исполнено", callback_data=f"fail:{tid}")

    # Инициатор (представитель)
    if is_creator or role == cfg.ROLE_SECRETARY:
        if st == cfg.ST_DONE_WAIT:
            b.button(text="🤝 Принять результат", callback_data=f"accept:{tid}")
        if st in (cfg.ST_NEW, cfg.ST_CLARIFY, cfg.ST_READY):
            b.button(text="✏️ Редактировать", callback_data=f"edit:{tid}")
        if st not in (cfg.ST_CANCELLED, cfg.ST_ACCEPTED):
            b.button(text="❌ Отменить поручение", callback_data=f"cancel:{tid}")

    # Комментарий — всем
    b.button(text="💬 Комментарий", callback_data=f"comment:{tid}")
    b.adjust(1)
    return b.as_markup()


def open_list_kb(tasks: List[Dict]) -> InlineKeyboardMarkup:
    """Кнопки «открыть» для списка поручений."""
    b = InlineKeyboardBuilder()
    for t in tasks:
        tid = t.get(cfg.H_ID)
        b.button(text=f"🔹 {tid}", callback_data=f"open:{tid}")
    b.adjust(3)
    return b.as_markup()


def executors_kb(task_id: str, executors: List[Dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for e in executors:
        name = e.get("Имя", "")
        role = e.get("Роль", "")
        b.button(text=f"{name} ({role})", callback_data=f"exec:{task_id}:{e.get('Telegram ID')}")
    b.button(text="◀️ Назад", callback_data=f"open:{task_id}")
    b.adjust(1)
    return b.as_markup()


def status_choice_kb(task_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in cfg.STATUSES:
        b.button(text=f"{cfg.STATUS_EMOJI.get(s,'')} {s}", callback_data=f"setst:{task_id}:{s}")
    b.button(text="◀️ Назад", callback_data=f"open:{task_id}")
    b.adjust(1)
    return b.as_markup()


def edit_field_kb(task_id: str) -> InlineKeyboardMarkup:
    fields = [
        (cfg.H_CLIENT, "Клиент"),
        (cfg.H_ORGAN, "Орган"),
        (cfg.H_ADDRESS, "Адрес"),
        (cfg.H_CASE, "Номер дела"),
        (cfg.H_ACTION, "Задача"),
        (cfg.H_SUCCESS, "Критерий успеха"),
        (cfg.H_LEGAL_DEADLINE, "Срок"),
    ]
    b = InlineKeyboardBuilder()
    for header, label in fields:
        b.button(text=label, callback_data=f"editf:{task_id}:{header}")
    b.button(text="◀️ Назад", callback_data=f"open:{task_id}")
    b.adjust(2)
    return b.as_markup()


def skip_proof_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Без вложения ⏩", callback_data="proof:skip"),
    ]])
