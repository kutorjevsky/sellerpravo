"""Форматирование карточек, дат, уведомления."""
from datetime import date, timedelta
from typing import Dict, List

from aiogram import Bot

from bot import config as cfg

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}
DAYS_RU = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}


def fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = date.fromisoformat(str(iso)[:10])
        return f"{d.day} {MONTHS_RU[d.month]} ({DAYS_RU[d.weekday()]})"
    except (ValueError, TypeError):
        return str(iso)


def today_iso() -> str:
    return date.today().isoformat()


def tomorrow_iso() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


def g(task: Dict, key: str) -> str:
    v = task.get(key, "")
    return str(v).strip() if v is not None else ""


def status_line(task: Dict) -> str:
    st = g(task, cfg.H_STATUS)
    return f"{cfg.STATUS_EMOJI.get(st, '•')} {st}"


def short_line(task: Dict) -> str:
    """Одна строка для списков."""
    st = g(task, cfg.H_STATUS)
    emoji = cfg.STATUS_EMOJI.get(st, "•")
    prio = cfg.PRIORITY_EMOJI.get(g(task, cfg.H_PRIORITY), "")
    organ = g(task, cfg.H_ORGAN) or g(task, cfg.H_ORGAN_TYPE)
    client = g(task, cfg.H_CLIENT)
    plan = g(task, cfg.H_PLAN_DATE)
    plan_part = f" · {fmt_date(plan)}" if plan else ""
    return f"{emoji}{prio} <b>{g(task, cfg.H_ID)}</b> · {organ} · {client}{plan_part}"


def task_card(task: Dict) -> str:
    """Полная карточка поручения."""
    lines = [
        f"{cfg.STATUS_EMOJI.get(g(task, cfg.H_STATUS), '•')} "
        f"<b>Поручение {g(task, cfg.H_ID)}</b>",
        f"Статус: <b>{g(task, cfg.H_STATUS)}</b>",
        "",
        f"👤 Клиент: {g(task, cfg.H_CLIENT) or '—'}",
    ]
    if g(task, cfg.H_CASE):
        lines.append(f"📁 Дело: {g(task, cfg.H_CASE)}")
    organ = g(task, cfg.H_ORGAN) or g(task, cfg.H_ORGAN_TYPE)
    lines.append(f"🏛 Орган: {organ}")
    if g(task, cfg.H_ADDRESS):
        lines.append(f"📍 Адрес: {g(task, cfg.H_ADDRESS)}")
    if g(task, cfg.H_TASK_TYPE):
        lines.append(f"🔖 Тип: {g(task, cfg.H_TASK_TYPE)}")
    lines.append(f"📝 Задача: {g(task, cfg.H_ACTION) or g(task, cfg.H_FULL) or '—'}")
    if g(task, cfg.H_FULL) and g(task, cfg.H_FULL) != g(task, cfg.H_ACTION):
        lines.append(f"   {g(task, cfg.H_FULL)}")
    if g(task, cfg.H_SUCCESS):
        lines.append(f"🎯 Успех = {g(task, cfg.H_SUCCESS)}")
    if g(task, cfg.H_OFFICIAL):
        lines.append(f"👔 Лицо: {g(task, cfg.H_OFFICIAL)}")

    prio = g(task, cfg.H_PRIORITY)
    if prio:
        lines.append(f"{cfg.PRIORITY_EMOJI.get(prio, '')} Приоритет: {prio}")
    if g(task, cfg.H_LEGAL_DEADLINE):
        lines.append(f"⏳ Срок: {g(task, cfg.H_LEGAL_DEADLINE)}")
    if g(task, cfg.H_POA):
        lines.append(f"📜 Доверенность: {g(task, cfg.H_POA)}")

    lines.append("")
    lines.append(f"👨‍💼 Инициатор: {g(task, cfg.H_INITIATOR) or '—'}")
    lines.append(f"🚗 Исполнитель: {g(task, cfg.H_EXECUTOR) or '— не назначен'}")
    if g(task, cfg.H_PLAN_DATE):
        lines.append(f"🗓 План: {fmt_date(g(task, cfg.H_PLAN_DATE))}")

    if g(task, cfg.H_RESULT):
        lines.append(f"\n✅ Результат: {g(task, cfg.H_RESULT)}")
    if g(task, cfg.H_PROOF):
        lines.append(f"📎 Доказательство: {g(task, cfg.H_PROOF)}")
    if g(task, cfg.H_ACCEPTED_BY):
        lines.append(f"🤝 Принял: {g(task, cfg.H_ACCEPTED_BY)}")
    if g(task, cfg.H_COMMENTS):
        lines.append(f"\n💬 Комментарии:\n{g(task, cfg.H_COMMENTS)}")

    return "\n".join(lines)


async def notify(bot: Bot, tg_ids: List, text: str) -> None:
    for tid in tg_ids:
        if not tid:
            continue
        try:
            await bot.send_message(int(tid), text)
        except Exception:
            pass


def main_menu_role(role: str):
    from bot.keyboards import (
        menu_representative, menu_secretary, menu_executor,
    )
    if role == cfg.ROLE_SECRETARY:
        return menu_secretary()
    if role in cfg.EXECUTOR_ROLES:
        return menu_executor()
    return menu_representative()
