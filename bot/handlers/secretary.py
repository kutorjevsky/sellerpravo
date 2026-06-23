"""Секретарь: распределение заданий, назначение исполнителей, статусы, план."""
from datetime import date, timedelta

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import sheets, config as cfg
from bot.keyboards import (
    open_list_kb, executors_kb, status_choice_kb, plan_date_kb,
)
from bot.utils import (
    short_line, task_card, notify, g, fmt_date, today_iso, tomorrow_iso,
)

router = Router()


async def _is_secretary(message: Message) -> bool:
    user = await sheets.get_user(message.from_user.id)
    if not user or user.get("Роль") != cfg.ROLE_SECRETARY:
        await message.answer("Функция доступна только секретарю.")
        return False
    return True


def _suggest_executor_hint(plan_date_iso: str, executors: list) -> str:
    """Текстовая подсказка по распределению (курьер ежедневно; помощники Пн/Чт)."""
    try:
        wd = date.fromisoformat(plan_date_iso).weekday()
    except (ValueError, TypeError):
        return ""
    couriers = [e["Имя"] for e in executors if e.get("Роль") == cfg.ROLE_COURIER]
    if wd in (0, 3):  # Пн/Чт — приёмные дни судов
        return ("💡 Пн/Чт — приёмные дни судов. Судебные поручения лучше отдать помощнику; "
                "остальное — курьеру " + (f"({couriers[0]})" if couriers else "") + ".")
    return ("💡 Сегодня не приёмный день судов — поручения берёт курьер "
            + (f"({couriers[0]})" if couriers else "") + ".")


async def _show_list(message: Message, title: str, tasks: list):
    if not tasks:
        await message.answer(f"{title}: пусто.")
        return
    # сортировка: по приоритету, затем по сроку
    prio_order = {p: i for i, p in enumerate(cfg.PRIORITIES)}
    tasks.sort(key=lambda t: (prio_order.get(g(t, cfg.H_PRIORITY), 9),
                              g(t, cfg.H_LEGAL_DEADLINE) or "9999"))
    lines = [f"<b>{title}: {len(tasks)}</b>\n"] + [short_line(t) for t in tasks]
    await message.answer("\n".join(lines), reply_markup=open_list_kb(tasks))


@router.message(F.text == "📥 Новые заявки")
async def btn_new_requests(message: Message):
    if not await _is_secretary(message):
        return
    tasks = await sheets.filter_tasks(statuses=(cfg.ST_NEW, cfg.ST_CLARIFY))
    await _show_list(message, "📥 Новые заявки", tasks)


@router.message(F.text == "🗓 На завтра")
async def btn_tomorrow(message: Message):
    if not await _is_secretary(message):
        return
    tasks = await sheets.filter_tasks(plan_date=tomorrow_iso())
    await _show_list(message, f"🗓 На завтра ({fmt_date(tomorrow_iso())})", tasks)


@router.message(F.text == "📋 В работе")
async def btn_in_work(message: Message):
    if not await _is_secretary(message):
        return
    tasks = await sheets.filter_tasks(
        statuses=(cfg.ST_READY, cfg.ST_ASSIGNED, cfg.ST_DONE_WAIT, cfg.ST_REVISIT)
    )
    await _show_list(message, "📋 В работе", tasks)


# ── Назначение исполнителя ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("assign:"))
async def cb_assign(callback: CallbackQuery):
    task_id = callback.data.split(":", 1)[1]
    task = await sheets.get_task(task_id)
    executors = await sheets.all_executors()
    if not executors:
        await callback.answer("Нет зарегистрированных исполнителей.", show_alert=True)
        return
    hint = _suggest_executor_hint(g(task, cfg.H_PLAN_DATE) or tomorrow_iso(), executors)
    await callback.message.answer(
        f"👤 Кому назначить {task_id}?\n{hint}",
        reply_markup=executors_kb(task_id, executors),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("exec:"))
async def cb_exec(callback: CallbackQuery, bot: Bot):
    _, task_id, exec_tg = callback.data.split(":", 2)
    task = await sheets.get_task(task_id)
    executors = await sheets.all_executors()
    executor = next((e for e in executors if str(e.get("Telegram ID")) == str(exec_tg)), None)
    if not task or not executor:
        await callback.answer("Не найдено", show_alert=True)
        return

    etype = cfg.ROLE_COURIER if executor.get("Роль") == cfg.ROLE_COURIER else \
        (cfg.ROLE_ASSISTANT if executor.get("Роль") == cfg.ROLE_ASSISTANT else "Представитель")
    await sheets.update_task(task_id, {
        cfg.H_EXECUTOR: executor["Имя"],
        cfg.H_EXECUTOR_TG: str(exec_tg),
        cfg.H_EXECUTOR_TYPE: etype,
        cfg.H_STATUS: cfg.ST_ASSIGNED,
    })
    secretary = await sheets.get_user(callback.from_user.id)
    await sheets.log(secretary["Имя"] if secretary else "", "назначено", task_id, executor["Имя"])

    await callback.message.edit_text(
        f"✅ {task_id} назначено: <b>{executor['Имя']}</b> ({etype})"
    )
    await callback.answer("Назначено")

    # уведомления
    await notify(bot, [exec_tg],
                 f"📌 <b>Вам назначено поручение {task_id}</b>\n\n{task_card(task)}\n\n"
                 f"Откройте «📋 Мои поручения».")
    await notify(bot, [g(task, cfg.H_INITIATOR_TG)],
                 f"📌 Поручение {task_id} назначено исполнителю {executor['Имя']}.")


# ── План-дата ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("setplan:"))
async def cb_setplan(callback: CallbackQuery):
    task_id = callback.data.split(":", 1)[1]
    await callback.message.answer(
        f"🗓 На какую дату поставить {task_id} в план?",
        reply_markup=plan_date_kb(task_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("plan:"))
async def cb_plan(callback: CallbackQuery, bot: Bot):
    _, task_id, plan_iso = callback.data.split(":", 2)
    task = await sheets.get_task(task_id)
    await sheets.update_task(task_id, {cfg.H_PLAN_DATE: plan_iso})
    sec = await sheets.get_user(callback.from_user.id)
    await sheets.log(sec["Имя"] if sec else "", "план-дата", task_id, plan_iso)
    await callback.message.edit_text(f"🗓 {task_id}: план на {fmt_date(plan_iso)}.")
    await callback.answer("Готово")
    await notify(bot, [g(task, cfg.H_EXECUTOR_TG)],
                 f"🗓 Поручение {task_id} запланировано на {fmt_date(plan_iso)}.")


# ── Смена статуса ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("status:"))
async def cb_status(callback: CallbackQuery):
    task_id = callback.data.split(":", 1)[1]
    await callback.message.answer(
        f"🔁 Новый статус для {task_id}:", reply_markup=status_choice_kb(task_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("setst:"))
async def cb_setst(callback: CallbackQuery, bot: Bot):
    _, task_id, status = callback.data.split(":", 2)
    task = await sheets.get_task(task_id)
    await sheets.update_task(task_id, {cfg.H_STATUS: status})
    sec = await sheets.get_user(callback.from_user.id)
    await sheets.log(sec["Имя"] if sec else "", "смена статуса", task_id, status)
    await callback.message.edit_text(
        f"{cfg.STATUS_EMOJI.get(status,'')} {task_id}: статус → <b>{status}</b>"
    )
    await callback.answer("Статус изменён")
    recipients = [g(task, cfg.H_INITIATOR_TG), g(task, cfg.H_EXECUTOR_TG)]
    await notify(bot, recipients, f"🔁 Статус {task_id} изменён: {status}")
