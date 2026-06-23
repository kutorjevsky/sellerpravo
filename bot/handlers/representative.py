"""Представитель: создание поручения, свои поручения, правка, отмена, приёмка."""
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import sheets, config as cfg
from bot.states import NewTask, EditTask
from bot.keyboards import (
    organ_type_kb, organ_suggest_kb, task_type_kb, priority_kb,
    yes_no_kb, skip_kb, deadline_kb, confirm_kb, open_list_kb,
    edit_field_kb,
)
from bot.utils import (
    task_card, short_line, fmt_date, notify, g, main_menu_role,
)
from bot.handlers.common import render_and_send

router = Router()


async def _start_new(message: Message, state: FSMContext, user: dict):
    await state.clear()
    await state.update_data(
        initiator=user["Имя"], initiator_tg=str(user["Telegram ID"]),
    )
    await message.answer("➕ <b>Новое поручение</b>\n\nШаг 1. Клиент (ФИО/организация):")
    await state.set_state(NewTask.client)


@router.message(F.text == "➕ Новое поручение")
@router.message(Command("new"))
async def btn_new(message: Message, state: FSMContext):
    user = await sheets.get_user(message.from_user.id)
    if not user or user.get("Роль") not in cfg.CREATOR_ROLES:
        await message.answer("Создавать поручения могут представитель и секретарь.")
        return
    await _start_new(message, state, user)


@router.message(NewTask.client)
async def s_client(message: Message, state: FSMContext):
    await state.update_data(client=message.text.strip())
    await message.answer("Шаг 2. Тип органа:", reply_markup=organ_type_kb())
    await state.set_state(NewTask.organ_type)


@router.callback_query(NewTask.organ_type, F.data.startswith("otype:"))
async def s_organ_type(callback: CallbackQuery, state: FSMContext):
    otype = callback.data.split(":", 1)[1]
    await state.update_data(organ_type=otype)
    agencies = await sheets.agencies_by_type(otype)
    if agencies:
        await callback.message.edit_text(
            f"Тип: <b>{otype}</b>\n\nШаг 3. Выберите орган или введите вручную:",
            reply_markup=organ_suggest_kb(agencies),
        )
    else:
        await callback.message.edit_text(
            f"Тип: <b>{otype}</b>\n\nШаг 3. Название органа (куда ехать):"
        )
    await state.set_state(NewTask.organ)
    await callback.answer()


@router.callback_query(NewTask.organ, F.data.startswith("organ:"))
async def s_organ_cb(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":", 1)[1]
    if val == "__manual__":
        await callback.message.edit_text("Введите название органа вручную:")
        await callback.answer()
        return
    # подтянем адрес из справочника
    await state.update_data(organ=val)
    address = ""
    for a in await sheets.agencies():
        if a.get("Орган") == val:
            address = a.get("Адрес", "")
            break
    await state.update_data(address=address)
    addr_note = f"\nАдрес из справочника: {address}" if address else ""
    await callback.message.edit_text(
        f"Орган: <b>{val}</b>{addr_note}\n\nШаг 4. Номер дела/материала (или пропустите):",
        reply_markup=skip_kb("skip_case"),
    )
    await state.set_state(NewTask.case)
    await callback.answer()


@router.message(NewTask.organ)
async def s_organ_text(message: Message, state: FSMContext):
    await state.update_data(organ=message.text.strip())
    await message.answer("Адрес органа (или пропустите):", reply_markup=skip_kb("skip_addr"))
    await state.set_state(NewTask.address)


@router.callback_query(NewTask.address, F.data == "skip_addr")
async def s_addr_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(address="")
    await callback.message.edit_text("Шаг 4. Номер дела/материала (или пропустите):",
                                     reply_markup=skip_kb("skip_case"))
    await state.set_state(NewTask.case)
    await callback.answer()


@router.message(NewTask.address)
async def s_addr(message: Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await message.answer("Шаг 4. Номер дела/материала (или пропустите):",
                         reply_markup=skip_kb("skip_case"))
    await state.set_state(NewTask.case)


@router.callback_query(NewTask.case, F.data == "skip_case")
async def s_case_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(case="")
    await callback.message.edit_text("Шаг 5. Тип поручения:", reply_markup=task_type_kb())
    await state.set_state(NewTask.task_type)
    await callback.answer()


@router.message(NewTask.case)
async def s_case(message: Message, state: FSMContext):
    await state.update_data(case=message.text.strip())
    await message.answer("Шаг 5. Тип поручения:", reply_markup=task_type_kb())
    await state.set_state(NewTask.task_type)


@router.callback_query(NewTask.task_type, F.data.startswith("ttype:"))
async def s_task_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(task_type=callback.data.split(":", 1)[1])
    await callback.message.edit_text(
        "Шаг 6. Что нужно сделать? (подробно опишите задачу)"
    )
    await state.set_state(NewTask.action)
    await callback.answer()


@router.message(NewTask.action)
async def s_action(message: Message, state: FSMContext):
    await state.update_data(action=message.text.strip())
    await message.answer(
        "Шаг 7. Что считать успешным результатом? "
        "(например: получить отметку, документ, входящий номер) — или пропустите:",
        reply_markup=skip_kb("skip_success"),
    )
    await state.set_state(NewTask.success)


@router.callback_query(NewTask.success, F.data == "skip_success")
async def s_success_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(success="")
    await callback.message.edit_text("Шаг 8. Срок исполнения:", reply_markup=deadline_kb())
    await state.set_state(NewTask.deadline)
    await callback.answer()


@router.message(NewTask.success)
async def s_success(message: Message, state: FSMContext):
    await state.update_data(success=message.text.strip())
    await message.answer("Шаг 8. Срок исполнения:", reply_markup=deadline_kb())
    await state.set_state(NewTask.deadline)


@router.callback_query(NewTask.deadline, F.data.startswith("ddl:"))
async def s_deadline_cb(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":", 1)[1]
    if val == "__manual__":
        await callback.message.edit_text("Введите срок текстом (например: до 27.06 включительно):")
        await callback.answer()
        return
    deadline = "" if val == "__none__" else val
    await state.update_data(deadline=deadline)
    await callback.message.edit_text("Шаг 9. Приоритет:", reply_markup=priority_kb())
    await state.set_state(NewTask.priority)
    await callback.answer()


@router.message(NewTask.deadline)
async def s_deadline_text(message: Message, state: FSMContext):
    await state.update_data(deadline=message.text.strip())
    await message.answer("Шаг 9. Приоритет:", reply_markup=priority_kb())
    await state.set_state(NewTask.priority)


@router.callback_query(NewTask.priority, F.data.startswith("prio:"))
async def s_priority(callback: CallbackQuery, state: FSMContext):
    await state.update_data(priority=callback.data.split(":", 1)[1])
    await callback.message.edit_text(
        "Шаг 10. Есть доверенность на исполнителя?", reply_markup=yes_no_kb("poa"),
    )
    await state.set_state(NewTask.poa)
    await callback.answer()


@router.callback_query(NewTask.poa, F.data.startswith("poa:"))
async def s_poa(callback: CallbackQuery, state: FSMContext):
    await state.update_data(poa=callback.data.split(":", 1)[1])
    await callback.message.edit_text(
        "Шаг 11. Доп. примечания / контекст (или пропустите):",
        reply_markup=skip_kb("skip_notes"),
    )
    await state.set_state(NewTask.notes)
    await callback.answer()


@router.callback_query(NewTask.notes, F.data == "skip_notes")
async def s_notes_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(notes="")
    await _show_confirm(callback.message, state)
    await callback.answer()


@router.message(NewTask.notes)
async def s_notes(message: Message, state: FSMContext):
    await state.update_data(notes=message.text.strip())
    await _show_confirm(message, state)


def _preview(d: dict) -> str:
    lines = [
        "<b>Проверьте поручение:</b>",
        f"👤 Клиент: {d.get('client')}",
        f"🏛 Орган: {d.get('organ')} ({d.get('organ_type')})",
    ]
    if d.get("address"):
        lines.append(f"📍 {d['address']}")
    if d.get("case"):
        lines.append(f"📁 Дело: {d['case']}")
    lines.append(f"🔖 {d.get('task_type')}: {d.get('action')}")
    if d.get("success"):
        lines.append(f"🎯 Успех = {d['success']}")
    if d.get("deadline"):
        lines.append(f"⏳ Срок: {d['deadline']}")
    lines.append(f"{cfg.PRIORITY_EMOJI.get(d.get('priority',''),'')} Приоритет: {d.get('priority')}")
    lines.append(f"📜 Доверенность: {d.get('poa')}")
    if d.get("notes"):
        lines.append(f"💬 {d['notes']}")
    return "\n".join(lines)


async def _show_confirm(message: Message, state: FSMContext):
    d = await state.get_data()
    await message.answer(_preview(d), reply_markup=confirm_kb())
    await state.set_state(NewTask.confirm)


@router.callback_query(NewTask.confirm, F.data == "newtask:cancel")
async def s_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🗑 Создание отменено.")
    await callback.answer()


@router.callback_query(NewTask.confirm, F.data == "newtask:ok")
async def s_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    d = await state.get_data()
    await state.clear()

    task_data = {
        cfg.H_STATUS: cfg.ST_NEW,
        cfg.H_INITIATOR: d.get("initiator", ""),
        cfg.H_INITIATOR_TG: d.get("initiator_tg", ""),
        cfg.H_CLIENT: d.get("client", ""),
        cfg.H_CASE: d.get("case", ""),
        cfg.H_ORGAN_TYPE: d.get("organ_type", ""),
        cfg.H_ORGAN: d.get("organ", ""),
        cfg.H_ADDRESS: d.get("address", ""),
        cfg.H_TASK_TYPE: d.get("task_type", ""),
        cfg.H_ACTION: d.get("action", ""),
        cfg.H_FULL: d.get("action", ""),
        cfg.H_SUCCESS: d.get("success", ""),
        cfg.H_LEGAL_DEADLINE: d.get("deadline", ""),
        cfg.H_PRIORITY: d.get("priority", ""),
        cfg.H_POA: d.get("poa", ""),
        cfg.H_COMMENTS: f"[создано] {d.get('notes')}" if d.get("notes") else "",
    }
    task_id = await sheets.create_task(task_data)
    await sheets.log(d.get("initiator", ""), "создано поручение", task_id, d.get("client", ""))

    await callback.message.edit_text(
        f"✅ <b>Поручение {task_id} создано</b>\n\n{_preview(d)}\n\n"
        f"Секретарь получил уведомление и назначит исполнителя."
    )
    await callback.answer("Создано!")

    # Уведомление секретарям
    secs = await sheets.secretary_tg_ids()
    prio = cfg.PRIORITY_EMOJI.get(d.get("priority", ""), "")
    await notify(
        bot, secs,
        f"🆕 <b>Новая заявка {task_id}</b> {prio}\n"
        f"👤 {d.get('client')}\n🏛 {d.get('organ')}\n"
        f"🔖 {d.get('task_type')}: {d.get('action')}\n"
        f"⏳ Срок: {d.get('deadline') or '—'}\n"
        f"От: {d.get('initiator')}\n\n"
        f"Откройте «📥 Новые заявки», чтобы назначить исполнителя.",
    )


# ── Мои поручения ─────────────────────────────────────────────────────────────

@router.message(F.text == "📋 Мои поручения")
async def btn_my(message: Message):
    user = await sheets.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    role = user.get("Роль")
    if role in cfg.EXECUTOR_ROLES:
        return  # обрабатывается в executor.py
    tasks = await sheets.filter_tasks(initiator_tg=str(user["Telegram ID"]))
    active = [t for t in tasks if t.get(cfg.H_STATUS) in cfg.ACTIVE_STATUSES]
    if not active:
        await message.answer("У вас нет активных поручений. Создать — «➕ Новое поручение».")
        return
    lines = [f"📋 <b>Ваши активные поручения: {len(active)}</b>\n"] + \
            [short_line(t) for t in active]
    await message.answer("\n".join(lines), reply_markup=open_list_kb(active))


# ── Приёмка результата ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("accept:"))
async def cb_accept(callback: CallbackQuery, bot: Bot):
    task_id = callback.data.split(":", 1)[1]
    user = await sheets.get_user(callback.from_user.id)
    task = await sheets.get_task(task_id)
    if not task:
        await callback.answer("Не найдено", show_alert=True)
        return
    await sheets.update_task(task_id, {
        cfg.H_STATUS: cfg.ST_ACCEPTED,
        cfg.H_ACCEPTED_BY: user["Имя"],
    })
    await sheets.log(user["Имя"], "принято", task_id, "")
    await callback.message.edit_text(
        f"🤝 Поручение {task_id} принято и закрыто. Спасибо!"
    )
    await callback.answer("Принято")
    # уведомим исполнителя
    await notify(bot, [g(task, cfg.H_EXECUTOR_TG)],
                 f"🤝 Ваш результат по {task_id} принят инициатором ({user['Имя']}).")


# ── Отмена поручения ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel(callback: CallbackQuery, bot: Bot):
    task_id = callback.data.split(":", 1)[1]
    user = await sheets.get_user(callback.from_user.id)
    task = await sheets.get_task(task_id)
    if not task:
        await callback.answer("Не найдено", show_alert=True)
        return
    await sheets.update_task(task_id, {cfg.H_STATUS: cfg.ST_CANCELLED})
    await sheets.log(user["Имя"], "отменено", task_id, "")
    await callback.message.edit_text(f"❌ Поручение {task_id} отменено.")
    await callback.answer("Отменено")
    recipients = [g(task, cfg.H_EXECUTOR_TG)] + \
                 [str(s) for s in await sheets.secretary_tg_ids()]
    await notify(bot, recipients, f"❌ Поручение {task_id} отменено ({user['Имя']}).")


# ── Редактирование ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit:"))
async def cb_edit(callback: CallbackQuery):
    task_id = callback.data.split(":", 1)[1]
    await callback.message.answer(
        f"✏️ Что изменить в {task_id}?", reply_markup=edit_field_kb(task_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("editf:"))
async def cb_edit_field(callback: CallbackQuery, state: FSMContext):
    _, task_id, header = callback.data.split(":", 2)
    await state.update_data(edit_task=task_id, edit_field=header)
    await callback.message.answer(f"Введите новое значение для «{header}»:")
    await state.set_state(EditTask.value)
    await callback.answer()


@router.message(EditTask.value)
async def save_edit(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    task_id = data["edit_task"]
    header = data["edit_field"]
    value = message.text.strip()
    await state.clear()
    await sheets.update_task(task_id, {header: value})
    user = await sheets.get_user(message.from_user.id)
    await sheets.log(user["Имя"] if user else "", "правка", task_id, f"{header}={value[:40]}")
    await message.answer(f"✅ {task_id}: «{header}» обновлено.")
    task = await sheets.get_task(task_id)
    recipients = [g(task, cfg.H_EXECUTOR_TG)] + \
                 [str(s) for s in await sheets.secretary_tg_ids()]
    await notify(bot, recipients,
                 f"✏️ Поручение {task_id} изменено: «{header}» → {value}")
