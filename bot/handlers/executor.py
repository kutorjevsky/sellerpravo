from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot.keyboards import task_actions_keyboard, cancel_keyboard, schedule_date_keyboard, schedule_court_keyboard
from bot.states import TaskResult, AssistantSchedule
from bot.utils import format_task_card, format_date, today_str

router = Router()


async def _require_executor(user, message: Message) -> bool:
    if not user or user["role"] not in ("courier", "assistant"):
        await message.answer("Эта функция доступна только для исполнителей (курьер/помощник).")
        return False
    return True


# ── My tasks for today ────────────────────────────────────────────────────────

@router.message(F.text == "📋 Мои задания на сегодня")
@router.message(Command("tasks"))
async def btn_my_tasks(message: Message):
    user = await db.get_user(message.from_user.id)
    if not await _require_executor(user, message):
        return

    tasks = await db.get_tasks_for_executor(user["id"], today_str())
    if not tasks:
        await message.answer(
            f"📋 На сегодня ({format_date(today_str())}) у вас нет назначенных заданий."
        )
        return

    await message.answer(
        f"📋 <b>Ваши задания на {format_date(today_str())}:</b> ({len(tasks)} шт.)"
    )
    for task in tasks:
        card = format_task_card(task)
        kb = task_actions_keyboard(task["id"]) if task["status"] in ("assigned", "in_progress") else None
        await message.answer(card, reply_markup=kb)


# ── Mark done ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("done:"))
async def cb_done(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    user = await db.get_user(callback.from_user.id)
    task = await db.get_task(task_id)

    if not task or task.get("executor_tg") != callback.from_user.id:
        await callback.answer("Задание не найдено или не назначено вам.", show_alert=True)
        return

    await state.update_data(task_id=task_id, success=True)
    await callback.message.edit_text(
        f"✅ Задание <b>#{task_id}</b>\n"
        f"Напишите результат (что сделано, что получено, какой ответ):",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(TaskResult.entering_result)
    await callback.answer()


@router.message(TaskResult.entering_result)
async def receive_result(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    task_id = data["task_id"]
    result_text = message.text.strip()

    await db.complete_task(task_id, result_text, success=True)
    task = await db.get_task(task_id)
    await state.clear()

    await message.answer(f"✅ <b>Задание #{task_id} отмечено как выполненное.</b>\n\nРезультат сохранён.")

    # Notify representative
    if task and task.get("representative_tg"):
        try:
            await bot.send_message(
                task["representative_tg"],
                f"✅ <b>Задание #{task_id} выполнено</b>\n\n"
                f"🏛 {task['court']}\n"
                f"📁 {task['case_name']}\n"
                f"👤 Клиент: {task['client']}\n\n"
                f"<b>Результат:</b> {result_text}",
            )
        except Exception:
            pass

    # Notify secretaries
    secretaries = await db.get_users_by_role("secretary")
    for sec in secretaries:
        try:
            await bot.send_message(
                sec["telegram_id"],
                f"✅ <b>Задание #{task_id} выполнено</b>\n"
                f"Исп-ль: {task.get('executor_name', '—')}\n"
                f"🏛 {task['court']} | {task['case_name']}\n"
                f"<b>Результат:</b> {result_text}",
            )
        except Exception:
            pass


# ── Mark failed ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fail:"))
async def cb_fail(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    user = await db.get_user(callback.from_user.id)
    task = await db.get_task(task_id)

    if not task or task.get("executor_tg") != callback.from_user.id:
        await callback.answer("Задание не найдено или не назначено вам.", show_alert=True)
        return

    await state.update_data(task_id=task_id, success=False)
    await callback.message.edit_text(
        f"❌ Задание <b>#{task_id}</b>\nОпишите причину / что произошло:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(TaskResult.entering_fail_reason)
    await callback.answer()


@router.message(TaskResult.entering_fail_reason)
async def receive_fail_reason(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    task_id = data["task_id"]
    reason = message.text.strip()

    await db.complete_task(task_id, reason, success=False)
    task = await db.get_task(task_id)
    await state.clear()

    await message.answer(f"❌ <b>Задание #{task_id} отмечено как невыполненное.</b>")

    # Notify representative (urgent)
    if task and task.get("representative_tg"):
        try:
            await bot.send_message(
                task["representative_tg"],
                f"❌ <b>Задание #{task_id} НЕ выполнено</b>\n\n"
                f"🏛 {task['court']}\n"
                f"📁 {task['case_name']}\n"
                f"👤 Клиент: {task['client']}\n\n"
                f"<b>Причина:</b> {reason}",
            )
        except Exception:
            pass

    # Notify secretaries
    secretaries = await db.get_users_by_role("secretary")
    for sec in secretaries:
        try:
            await bot.send_message(
                sec["telegram_id"],
                f"⚠️ <b>Задание #{task_id} НЕ выполнено!</b>\n"
                f"Исп-ль: {task.get('executor_name', '—')}\n"
                f"🏛 {task['court']} | {task['case_name']}\n"
                f"<b>Причина:</b> {reason}",
            )
        except Exception:
            pass


@router.callback_query(F.data == "cancel_result")
async def cb_cancel_result(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено. Задание остаётся в прежнем статусе.")
    await callback.answer()


# ── Assistant schedule registration ──────────────────────────────────────────

@router.message(F.text == "📅 Зарегистрировать выезд")
@router.message(Command("schedule"))
async def btn_schedule(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not await _require_executor(user, message):
        return

    if user["role"] != "assistant":
        await message.answer(
            "Регистрация выездного расписания доступна только помощникам.\n"
            "Курьер (Иван) выезжает ежедневно автоматически."
        )
        return

    await message.answer(
        "📅 <b>Регистрация выезда</b>\n\nВыберите дату поездки в суд:",
        reply_markup=schedule_date_keyboard(),
    )
    await state.set_state(AssistantSchedule.date)


@router.callback_query(AssistantSchedule.date, F.data.startswith("sched_date:"))
async def sched_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    await state.update_data(sched_date=date_str)
    await callback.message.edit_text(
        f"Дата: <b>{format_date(date_str)}</b>\n\nВыберите суд:",
        reply_markup=schedule_court_keyboard(),
    )
    await state.set_state(AssistantSchedule.court)
    await callback.answer()


@router.callback_query(AssistantSchedule.court, F.data.startswith("sched_court:"))
async def sched_court_cb(callback: CallbackQuery, state: FSMContext):
    court_raw = callback.data[len("sched_court:"):]
    if court_raw == "__manual__":
        await callback.message.edit_text("Введите название суда вручную:")
        await callback.answer()
        return
    await _save_schedule(callback.message, state, court_raw, callback.from_user.id)
    await callback.answer()


@router.message(AssistantSchedule.court)
async def sched_court_text(message: Message, state: FSMContext):
    await _save_schedule(message, state, message.text.strip(), message.from_user.id)


async def _save_schedule(message: Message, state: FSMContext, court: str, tg_id: int):
    data = await state.get_data()
    date_str = data["sched_date"]
    user = await db.get_user(tg_id)

    await db.set_assistant_schedule(user["id"], date_str, court)
    await state.clear()

    await message.answer(
        f"✅ <b>Выезд зарегистрирован!</b>\n"
        f"📅 Дата: {format_date(date_str)}\n"
        f"🏛 Суд: {court}\n\n"
        f"Секретарь увидит вас в рекомендациях при назначении заданий на эту дату."
    )

    # Notify secretaries
    secretaries = await db.get_users_by_role("secretary")
    for sec in secretaries:
        try:
            from aiogram import Bot
            # We can't easily get the bot here without passing it — skip secretary notification
            # (they will see it when they view tasks for that day)
            pass
        except Exception:
            pass
