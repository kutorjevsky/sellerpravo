from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot.keyboards import (
    assign_task_keyboard, executors_keyboard, archive_nav_keyboard,
    menu_secretary,
)
from bot.utils import format_task_card, format_date, today_str, tomorrow_str, tasks_summary, suggest_executor

router = Router()


async def _require_secretary(user, message: Message) -> bool:
    if not user or user["role"] != "secretary":
        await message.answer("Эта функция доступна только секретарю.")
        return False
    return True


async def _show_day(message: Message, date_str: str):
    tasks = await db.get_tasks_for_date(date_str)
    if not tasks:
        await message.answer(f"📋 Заданий на {format_date(date_str)} нет.")
        return

    summary = tasks_summary(tasks)
    header = (
        f"📋 <b>Задания на {format_date(date_str)}</b>\n"
        f"{summary}\n"
        f"{'─' * 30}"
    )
    await message.answer(header)

    for task in tasks:
        suggestion = await suggest_executor(task["scheduled_date"], task["court"])
        suggested_id = suggestion["id"] if suggestion else None
        suggested_name = suggestion["name"] if suggestion else None

        card = format_task_card(task)
        kb = None

        if task["status"] == "pending":
            kb = assign_task_keyboard(task["id"], suggested_id, suggested_name)
        elif task["status"] in ("assigned", "in_progress"):
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="🔄 Переназначить",
                    callback_data=f"choose_exec:{task['id']}",
                )
            ]])

        await message.answer(card, reply_markup=kb)


@router.message(F.text == "📋 На сегодня")
async def btn_today(message: Message):
    user = await db.get_user(message.from_user.id)
    if not await _require_secretary(user, message):
        return
    await _show_day(message, today_str())


@router.message(F.text == "📋 На завтра")
async def btn_tomorrow(message: Message):
    user = await db.get_user(message.from_user.id)
    if not await _require_secretary(user, message):
        return
    await _show_day(message, tomorrow_str())


@router.message(Command("today"))
async def cmd_today(message: Message):
    user = await db.get_user(message.from_user.id)
    if not await _require_secretary(user, message):
        return
    await _show_day(message, today_str())


# ── Assignment via inline buttons ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("assign:"))
async def cb_assign(callback: CallbackQuery, bot: Bot):
    _, task_id_str, executor_id_str = callback.data.split(":")
    task_id = int(task_id_str)
    executor_id = int(executor_id_str)

    task = await db.get_task(task_id)
    if not task:
        await callback.answer("Задание не найдено.")
        return

    executor = await db.get_user_by_id(executor_id)
    if not executor:
        await callback.answer("Исполнитель не найден.")
        return

    await db.assign_task(task_id, executor_id)

    await callback.message.edit_text(
        f"✅ Задание <b>#{task_id}</b> назначено: <b>{executor['name']}</b>\n\n"
        f"{format_task_card(task)}"
    )
    await callback.answer(f"Назначено: {executor['name']}")

    # Notify executor
    try:
        await bot.send_message(
            executor["telegram_id"],
            f"📌 <b>Вам назначено задание #{task_id}</b>\n\n"
            f"{format_task_card(task)}\n\n"
            f"Нажмите <b>📋 Мои задания на сегодня</b> для деталей.",
        )
    except Exception:
        pass

    # Notify representative
    if task.get("representative_tg"):
        try:
            await bot.send_message(
                task["representative_tg"],
                f"📌 Задание <b>#{task_id}</b> назначено исполнителю <b>{executor['name']}</b>.",
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("choose_exec:"))
async def cb_choose_executor(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    executors = await db.get_all_executors()
    if not executors:
        await callback.answer("Нет зарегистрированных исполнителей.", show_alert=True)
        return
    await callback.message.edit_reply_markup(
        reply_markup=executors_keyboard(task_id, executors)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_task:"))
async def cb_back_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    task = await db.get_task(task_id)
    if not task:
        await callback.answer("Задание не найдено.")
        return

    suggestion = await suggest_executor(task["scheduled_date"], task["court"])
    suggested_id = suggestion["id"] if suggestion else None
    suggested_name = suggestion["name"] if suggestion else None

    await callback.message.edit_reply_markup(
        reply_markup=assign_task_keyboard(task_id, suggested_id, suggested_name)
    )
    await callback.answer()


# ── Archive for secretary ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("archive:"))
async def cb_archive_page(callback: CallbackQuery):
    offset = int(callback.data.split(":")[1])
    PAGE = 10
    tasks = await db.get_archived_tasks(limit=PAGE + 1, offset=offset)
    has_more = len(tasks) > PAGE
    tasks = tasks[:PAGE]

    if not tasks:
        await callback.answer("Больше записей нет.", show_alert=True)
        return

    lines = [f"📚 <b>Архив</b> (записи {offset + 1}–{offset + len(tasks)})\n"]
    for t in tasks:
        icon = "✅" if t["status"] == "done" else "❌"
        lines.append(
            f"{icon} <b>#{t['id']}</b> {t['court']} | {format_date(t['scheduled_date'])}\n"
            f"   {t['case_name']} | {t.get('client')}\n"
            f"   Исп: {t.get('executor_name') or '—'}"
            + (f"\n   Результат: {t['result']}" if t.get("result") else "")
        )

    nav = archive_nav_keyboard(offset, has_more)
    await callback.message.edit_text(
        "\n\n".join(lines),
        reply_markup=nav,
    )
    await callback.answer()
