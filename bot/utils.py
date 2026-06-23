from datetime import date, timedelta
from typing import Optional, Dict, List

from bot.database import get_assistant_schedule, get_users_by_role


MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

DAYS_RU = {
    0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс",
}

DAYS_FULL_RU = {
    0: "понедельник", 1: "вторник", 2: "среда",
    3: "четверг", 4: "пятница", 5: "суббота", 6: "воскресенье",
}


def format_date(date_str: str) -> str:
    """Format YYYY-MM-DD to '23 июня (Пн)'."""
    d = date.fromisoformat(date_str)
    return f"{d.day} {MONTHS_RU[d.month]} ({DAYS_RU[d.weekday()]})"


def tomorrow_str() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


def today_str() -> str:
    return date.today().isoformat()


def format_task_card(task: Dict, show_result: bool = False) -> str:
    """Format a task as a readable message block."""
    poa = "✅ есть" if task.get("has_poa") else "❌ нет"
    status_map = {
        "pending": "⏳ Ожидает назначения",
        "assigned": "📌 Назначено",
        "in_progress": "🔄 Выполняется",
        "done": "✅ Выполнено",
        "failed": "❌ Не выполнено",
    }
    status = status_map.get(task.get("status", "pending"), task.get("status", ""))
    executor = task.get("executor_name") or "—"

    lines = [
        f"<b>#{task['id']} | {task['court']}</b>",
        f"📁 Дело: {task['case_name']}"
        + (f" ({task['case_number']})" if task.get("case_number") else ""),
        f"👤 Клиент: {task['client']}",
        f"📝 Задача: {task['description']}",
        f"📅 Дата: {format_date(task['scheduled_date'])}",
        f"📜 Доверенность: {poa}",
        f"👨‍💼 Представитель: {task.get('representative_name', '—')}",
        f"🚗 Исполнитель: {executor}",
        f"Статус: {status}",
    ]

    if task.get("notes"):
        lines.insert(5, f"💬 Примечания: {task['notes']}")

    if show_result and task.get("result"):
        lines.append(f"\n<b>Результат:</b> {task['result']}")

    return "\n".join(lines)


async def suggest_executor(scheduled_date: str, court: str) -> Optional[Dict]:
    """
    Suggest best executor for a task.
    Mon/Thu → check if assistant is going to that court → any available assistant.
    Other days → courier.
    """
    d = date.fromisoformat(scheduled_date)
    day = d.weekday()

    if day in (0, 3):  # Monday or Thursday
        # Assistant scheduled for exact court
        exact = await get_assistant_schedule(scheduled_date, court)
        if exact:
            return {"id": exact[0]["assistant_id"], "name": exact[0]["name"],
                    "telegram_id": exact[0]["telegram_id"]}

        # Any assistant scheduled that day
        any_day = await get_assistant_schedule(scheduled_date)
        if any_day:
            return {"id": any_day[0]["assistant_id"], "name": any_day[0]["name"],
                    "telegram_id": any_day[0]["telegram_id"]}

        # Fallback: any assistant registered in system
        assistants = await get_users_by_role("assistant")
        if assistants:
            a = assistants[0]
            return {"id": a["id"], "name": a["name"], "telegram_id": a["telegram_id"]}

    # Default: courier
    couriers = await get_users_by_role("courier")
    if couriers:
        c = couriers[0]
        return {"id": c["id"], "name": c["name"], "telegram_id": c["telegram_id"]}

    return None


def tasks_summary(tasks: List[Dict]) -> str:
    """One-line summary counts by status."""
    counts: Dict[str, int] = {}
    for t in tasks:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    parts = []
    if counts.get("pending"):
        parts.append(f"⏳ {counts['pending']} ожидает")
    if counts.get("assigned"):
        parts.append(f"📌 {counts['assigned']} назначено")
    if counts.get("done"):
        parts.append(f"✅ {counts['done']} выполнено")
    if counts.get("failed"):
        parts.append(f"❌ {counts['failed']} не выполнено")
    return " | ".join(parts) if parts else "нет заданий"
