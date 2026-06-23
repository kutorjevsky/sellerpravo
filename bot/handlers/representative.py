from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot.config import TASK_CREATORS
from bot.keyboards import (
    courts_keyboard, yes_no_keyboard, skip_keyboard,
    date_keyboard, confirm_task_keyboard, menu_representative,
    menu_secretary,
)
from bot.states import NewTask
from bot.utils import format_task_card, format_date, tomorrow_str

router = Router()


async def _require_role(user, allowed_roles, message: Message) -> bool:
    if not user or user["role"] not in allowed_roles:
        await message.answer("У вас нет доступа к этой функции.")
        return False
    return True


async def _notify_secretaries(bot: Bot, task: dict, suggested_name: str = None) -> None:
    secretaries = await db.get_users_by_role("secretary")
    suggestion = f"\n💡 Предлагаю: <b>{suggested_name}</b>" if suggested_name else ""
    text = (
        f"🆕 <b>Новое задание #{task['id']}</b>\n\n"
        f"{format_task_card(task)}"
        f"{suggestion}\n\n"
        f"Используйте <b>📋 На завтра</b>, чтобы назначить исполнителя."
    )
    for sec in secretaries:
        try:
            await bot.send_message(sec["telegram_id"], text)
        except Exception:
            pass


# ── Create task ───────────────────────────────────────────────────────────────

async def _start_new_task(message: Message, state: FSMContext, user: dict):
    await state.clear()
    await state.update_data(representative_id=user["id"])
    await message.answer(
        "📝 <b>Новое задание</b>\n\nШаг 1/8: Куда ехать?\n"
        "Выберите из списка или введите вручную:",
        reply_markup=courts_keyboard(),
    )
    await state.set_state(NewTask.court)


@router.message(F.text == "📝 Новое задание")
async def btn_new_task(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not await _require_role(user, TASK_CREATORS, message):
        return
    await _start_new_task(message, state, user)


@router.message(Command("new_task"))
async def cmd_new_task(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not await _require_role(user, TASK_CREATORS, message):
        return
    await _start_new_task(message, state, user)


@router.callback_query(NewTask.court, F.data.startswith("court:"))
async def step_court_cb(callback: CallbackQuery, state: FSMContext):
    court = callback.data[6:]  # strip "court:"
    if court == "Другое...":
        await callback.message.edit_text("Введите название места вручную:")
        await state.set_state(NewTask.court_custom)
        await callback.answer()
        return
    await state.update_data(court=court)
    await callback.message.edit_text(
        f"✅ Место: <b>{court}</b>\n\n"
        "Шаг 2/8: Название дела (напишите):"
    )
    await state.set_state(NewTask.case_name)
    await callback.answer()


@router.message(NewTask.court)
async def step_court_text(message: Message, state: FSMContext):
    await state.update_data(court=message.text.strip())
    await message.answer(
        f"✅ Место: <b>{message.text.strip()}</b>\n\nШаг 2/8: Название дела:"
    )
    await state.set_state(NewTask.case_name)


@router.message(NewTask.court_custom)
async def step_court_custom(message: Message, state: FSMContext):
    await state.update_data(court=message.text.strip())
    await message.answer(
        f"✅ Место: <b>{message.text.strip()}</b>\n\nШаг 2/8: Название дела:"
    )
    await state.set_state(NewTask.case_name)


@router.message(NewTask.case_name)
async def step_case_name(message: Message, state: FSMContext):
    await state.update_data(case_name=message.text.strip())
    await message.answer(
        "Шаг 3/8: Номер дела (если есть, иначе пропустите):",
        reply_markup=skip_keyboard("skip_case_number"),
    )
    await state.set_state(NewTask.case_number)


@router.callback_query(NewTask.case_number, F.data == "skip_case_number")
async def step_skip_case_number(callback: CallbackQuery, state: FSMContext):
    await state.update_data(case_number=None)
    await callback.message.edit_text("Шаг 4/8: Имя клиента:")
    await state.set_state(NewTask.client)
    await callback.answer()


@router.message(NewTask.case_number)
async def step_case_number(message: Message, state: FSMContext):
    await state.update_data(case_number=message.text.strip())
    await message.answer("Шаг 4/8: Имя клиента:")
    await state.set_state(NewTask.client)


@router.message(NewTask.client)
async def step_client(message: Message, state: FSMContext):
    await state.update_data(client=message.text.strip())
    await message.answer("Шаг 5/8: Что нужно сделать? (описание задачи)")
    await state.set_state(NewTask.description)


@router.message(NewTask.description)
async def step_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await message.answer(
        "Шаг 6/8: Примечания / контекст (что было в прошлый раз и т.д.):\n"
        "Или пропустите, если не нужно.",
        reply_markup=skip_keyboard("skip_notes"),
    )
    await state.set_state(NewTask.notes)


@router.callback_query(NewTask.notes, F.data == "skip_notes")
async def step_skip_notes(callback: CallbackQuery, state: FSMContext):
    await state.update_data(notes=None)
    await callback.message.edit_text(
        "Шаг 7/8: Есть ли доверенность на исполнителя?",
        reply_markup=yes_no_keyboard("poa"),
    )
    await state.set_state(NewTask.has_poa)
    await callback.answer()


@router.message(NewTask.notes)
async def step_notes(message: Message, state: FSMContext):
    await state.update_data(notes=message.text.strip())
    await message.answer(
        "Шаг 7/8: Есть ли доверенность на исполнителя?",
        reply_markup=yes_no_keyboard("poa"),
    )
    await state.set_state(NewTask.has_poa)


@router.callback_query(NewTask.has_poa, F.data.startswith("poa:"))
async def step_poa(callback: CallbackQuery, state: FSMContext):
    has_poa = callback.data == "poa:yes"
    await state.update_data(has_poa=has_poa)
    await callback.message.edit_text(
        "Шаг 8/8: На какую дату задание?",
        reply_markup=date_keyboard(),
    )
    await state.set_state(NewTask.date)
    await callback.answer()


@router.callback_query(NewTask.date, F.data.startswith("date:"))
async def step_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data[5:]
    await state.update_data(scheduled_date=date_str)
    data = await state.get_data()

    # Build preview
    preview = _build_preview(data)
    await callback.message.edit_text(
        f"<b>Проверьте задание:</b>\n\n{preview}",
        reply_markup=confirm_task_keyboard(),
    )
    await state.set_state(NewTask.confirm)
    await callback.answer()


def _build_preview(data: dict) -> str:
    poa = "✅ есть" if data.get("has_poa") else "❌ нет"
    lines = [
        f"🏛 <b>Место:</b> {data.get('court')}",
        f"📁 <b>Дело:</b> {data.get('case_name')}"
        + (f" ({data['case_number']})" if data.get("case_number") else ""),
        f"👤 <b>Клиент:</b> {data.get('client')}",
        f"📝 <b>Задача:</b> {data.get('description')}",
        f"📅 <b>Дата:</b> {format_date(data.get('scheduled_date', ''))}",
        f"📜 <b>Доверенность:</b> {poa}",
    ]
    if data.get("notes"):
        lines.append(f"💬 <b>Примечания:</b> {data['notes']}")
    return "\n".join(lines)


@router.callback_query(NewTask.confirm, F.data == "task:confirm")
async def confirm_task(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    task_id = await db.create_task(data)
    task = await db.get_task(task_id)

    from bot.utils import suggest_executor
    suggestion = await suggest_executor(data["scheduled_date"], data["court"])
    suggested_name = suggestion["name"] if suggestion else None

    await callback.message.edit_text(
        f"✅ <b>Задание #{task_id} создано!</b>\n\n"
        f"{_build_preview(data)}\n\n"
        f"Секретарь получил уведомление и назначит исполнителя."
    )
    await callback.answer("Задание создано!")

    await _notify_secretaries(bot, task, suggested_name)


@router.callback_query(NewTask.confirm, F.data == "task:cancel")
async def cancel_task(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🗑 Задание отменено.")
    await callback.answer()


# ── My tasks ──────────────────────────────────────────────────────────────────

@router.message(F.text == "📋 Мои задания")
@router.message(Command("my_tasks"))
async def btn_my_tasks(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or user["role"] not in TASK_CREATORS:
        await message.answer("У вас нет доступа.")
        return

    tasks = await db.get_tasks_by_representative(user["id"], limit=15)
    if not tasks:
        await message.answer("У вас пока нет заданий.")
        return

    chunks = []
    for t in tasks:
        status_map = {
            "pending": "⏳", "assigned": "📌",
            "done": "✅", "failed": "❌", "in_progress": "🔄",
        }
        icon = status_map.get(t["status"], "•")
        date_str = format_date(t["scheduled_date"])
        executor = t.get("executor_name") or "не назначен"
        line = (
            f"{icon} <b>#{t['id']}</b> | {t['court']} | {date_str}\n"
            f"   {t['case_name']} → {executor}"
        )
        if t.get("result"):
            line += f"\n   Результат: {t['result']}"
        chunks.append(line)

    await message.answer(
        "📋 <b>Ваши последние задания:</b>\n\n" + "\n\n".join(chunks)
    )


# ── Archive ───────────────────────────────────────────────────────────────────

@router.message(F.text == "📚 Архив")
async def btn_archive(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Зарегистрируйтесь: /start")
        return
    await _show_archive(message, offset=0)


async def _show_archive(message: Message, offset: int = 0):
    from bot.keyboards import archive_nav_keyboard
    PAGE = 10
    tasks = await db.get_archived_tasks(limit=PAGE + 1, offset=offset)
    has_more = len(tasks) > PAGE
    tasks = tasks[:PAGE]

    if not tasks:
        await message.answer("Архив пуст.")
        return

    lines = [f"📚 <b>Архив заданий</b> (записи {offset + 1}–{offset + len(tasks)})\n"]
    for t in tasks:
        icon = "✅" if t["status"] == "done" else "❌"
        date_str = format_date(t["scheduled_date"])
        lines.append(
            f"{icon} <b>#{t['id']}</b> {t['court']} | {date_str}\n"
            f"   {t['case_name']} | Клиент: {t['client']}\n"
            f"   Исп-ль: {t.get('executor_name') or '—'}"
            + (f"\n   Результат: {t['result']}" if t.get("result") else "")
        )

    nav = archive_nav_keyboard(offset, has_more)
    await message.answer("\n\n".join(lines), reply_markup=nav)
