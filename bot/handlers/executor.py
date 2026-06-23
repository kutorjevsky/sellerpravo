"""Исполнитель (курьер/помощник): мои поручения, отчёт о результате."""
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import sheets, config as cfg
from bot.states import Result, FailReason
from bot.keyboards import open_list_kb, skip_proof_kb
from bot.utils import short_line, task_card, notify, g, fmt_date

router = Router()


@router.message(F.text == "📋 Мои поручения")
async def btn_my_tasks(message: Message):
    user = await sheets.get_user(message.from_user.id)
    if not user or user.get("Роль") not in cfg.EXECUTOR_ROLES:
        return  # для представителя обрабатывает representative.py
    tasks = await sheets.filter_tasks(
        executor_tg=str(user["Telegram ID"]),
        statuses=(cfg.ST_ASSIGNED, cfg.ST_REVISIT),
    )
    if not tasks:
        await message.answer("📋 У вас нет активных поручений.")
        return
    # сортировка по план-дате
    tasks.sort(key=lambda t: g(t, cfg.H_PLAN_DATE) or "9999")
    lines = [f"📋 <b>Ваши поручения: {len(tasks)}</b>\n"] + [short_line(t) for t in tasks]
    await message.answer("\n".join(lines), reply_markup=open_list_kb(tasks))


# ── Исполнено: ввод результата ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("result:"))
async def cb_result(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split(":", 1)[1]
    task = await sheets.get_task(task_id)
    if not task or str(task.get(cfg.H_EXECUTOR_TG)) != str(callback.from_user.id):
        await callback.answer("Это поручение не назначено вам.", show_alert=True)
        return
    await state.update_data(result_task=task_id)
    await callback.message.answer(
        f"✅ {task_id}. Опишите результат "
        f"(что сделано, что получено, входящий номер и т.п.):"
    )
    await state.set_state(Result.text)
    await callback.answer()


@router.message(Result.text)
async def result_text(message: Message, state: FSMContext):
    await state.update_data(result_text=message.text.strip())
    await message.answer(
        "📎 Прикрепите ссылку на фото/скан/документ (Google Drive и т.п.) "
        "или нажмите «Без вложения»:",
        reply_markup=skip_proof_kb(),
    )
    await state.set_state(Result.proof)


@router.callback_query(Result.proof, F.data == "proof:skip")
async def result_proof_skip(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await _finish_result(callback.message, state, bot, callback.from_user.id, proof="")
    await callback.answer()


@router.message(Result.proof)
async def result_proof(message: Message, state: FSMContext, bot: Bot):
    await _finish_result(message, state, bot, message.from_user.id, proof=message.text.strip())


async def _finish_result(message: Message, state: FSMContext, bot: Bot, tg_id: int, proof: str):
    data = await state.get_data()
    task_id = data["result_task"]
    result_text = data["result_text"]
    await state.clear()

    from bot.utils import today_iso
    await sheets.update_task(task_id, {
        cfg.H_STATUS: cfg.ST_DONE_WAIT,
        cfg.H_RESULT: result_text,
        cfg.H_PROOF: proof,
        cfg.H_FACT_DATE: today_iso(),
    })
    user = await sheets.get_user(tg_id)
    await sheets.log(user["Имя"] if user else "", "исполнено", task_id, result_text[:80])
    task = await sheets.get_task(task_id)

    await message.answer(
        f"✅ {task_id} отмечено как исполнено. Инициатор и секретарь уведомлены."
    )

    recipients = [g(task, cfg.H_INITIATOR_TG)] + \
                 [str(s) for s in await sheets.secretary_tg_ids()]
    proof_line = f"\n📎 {proof}" if proof else ""
    await notify(
        bot, recipients,
        f"📨 <b>Исполнено: {task_id}</b> (ждёт приёмки)\n"
        f"🏛 {g(task, cfg.H_ORGAN)} · {g(task, cfg.H_CLIENT)}\n"
        f"Исполнитель: {g(task, cfg.H_EXECUTOR)}\n\n"
        f"✅ Результат: {result_text}{proof_line}",
    )


# ── Повторный визит ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("revisit:"))
async def cb_revisit(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split(":", 1)[1]
    task = await sheets.get_task(task_id)
    if not task or str(task.get(cfg.H_EXECUTOR_TG)) != str(callback.from_user.id):
        await callback.answer("Это поручение не назначено вам.", show_alert=True)
        return
    await state.update_data(fail_task=task_id, fail_status=cfg.ST_REVISIT)
    await callback.message.answer(
        f"🔁 {task_id}. Почему нужен повторный визит? Опишите, что произошло:"
    )
    await state.set_state(FailReason.text)
    await callback.answer()


# ── Не исполнено объективно ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fail:"))
async def cb_fail(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split(":", 1)[1]
    task = await sheets.get_task(task_id)
    if not task or str(task.get(cfg.H_EXECUTOR_TG)) != str(callback.from_user.id):
        await callback.answer("Это поручение не назначено вам.", show_alert=True)
        return
    await state.update_data(fail_task=task_id, fail_status=cfg.ST_FAILED)
    await callback.message.answer(
        f"🚫 {task_id}. Опишите причину (орган закрыт, документ не готов и т.п.):"
    )
    await state.set_state(FailReason.text)
    await callback.answer()


@router.message(FailReason.text)
async def fail_reason(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    task_id = data["fail_task"]
    status = data["fail_status"]
    reason = message.text.strip()
    await state.clear()

    user = await sheets.get_user(message.from_user.id)
    author = user["Имя"] if user else ""
    await sheets.update_task(task_id, {cfg.H_STATUS: status})
    await sheets.append_comment(task_id, author, reason)
    await sheets.log(author, status, task_id, reason[:80])
    task = await sheets.get_task(task_id)

    label = "🔁 Нужен повторный визит" if status == cfg.ST_REVISIT else "🚫 Не исполнено"
    await message.answer(f"{label}: {task_id}. Инициатор и секретарь уведомлены.")

    recipients = [g(task, cfg.H_INITIATOR_TG)] + \
                 [str(s) for s in await sheets.secretary_tg_ids()]
    await notify(
        bot, recipients,
        f"{label} — <b>{task_id}</b>\n"
        f"🏛 {g(task, cfg.H_ORGAN)} · {g(task, cfg.H_CLIENT)}\n"
        f"Исполнитель: {g(task, cfg.H_EXECUTOR)}\n\nПричина: {reason}",
    )
