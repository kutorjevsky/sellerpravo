"""Старт, регистрация, помощь, поиск, карточка поручения, комментарии."""
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import sheets, config as cfg
from bot.states import Registration, Comment, Search
from bot.keyboards import role_kb, card_kb, open_list_kb, remove_kb
from bot.utils import task_card, short_line, notify, main_menu_role, g

router = Router()


def role_label(role: str) -> str:
    return f"{cfg.ROLE_EMOJI.get(role, '')} {role}"


# ── Старт / регистрация ───────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await sheets.get_user(message.from_user.id)
    if user and user.get("Имя"):
        await message.answer(
            f"С возвращением, <b>{user['Имя']}</b>!\nРоль: {role_label(user.get('Роль',''))}",
            reply_markup=main_menu_role(user.get("Роль", "")),
        )
        return
    await message.answer(
        "👋 Система управления поручениями <b>Seller Pravo</b>.\n\n"
        "Давайте зарегистрируемся. Введите имя и фамилию:",
        reply_markup=remove_kb(),
    )
    await state.set_state(Registration.name)


@router.message(Registration.name)
async def reg_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Введите корректное имя (минимум 2 символа).")
        return
    await state.update_data(name=name)
    await message.answer(f"Приятно, <b>{name}</b>! Выберите роль:", reply_markup=role_kb())
    await state.set_state(Registration.role)


@router.callback_query(Registration.role, F.data.startswith("reg_role:"))
async def reg_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":", 1)[1]
    if role not in cfg.ROLES:
        await callback.answer("Неверная роль")
        return
    data = await state.get_data()
    await sheets.register_user(
        callback.from_user.id, data["name"], role,
        callback.from_user.username or "",
    )
    await sheets.log(data["name"], "регистрация", "", role)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Готово!\nИмя: <b>{data['name']}</b>\nРоль: {role_label(role)}"
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_role(role))
    await callback.answer()


@router.message(Command("changerole"))
async def cmd_changerole(message: Message, state: FSMContext):
    user = await sheets.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    await state.update_data(name=user["Имя"])
    await message.answer("Выберите новую роль:", reply_markup=role_kb())
    await state.set_state(Registration.role)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Команды</b>\n"
        "/start — меню\n/whoami — мой профиль\n/changerole — сменить роль\n\n"
        "<b>Как это работает</b>\n"
        "• Представитель создаёт поручение → оно попадает в реестр (Google-таблица).\n"
        "• Секретарь назначает исполнителя и план-дату.\n"
        "• Исполнитель отчитывается — результат и комментарии приходят инициатору и секретарю.\n"
        "• Любой может искать поручения через 🔍 Поиск.\n"
        "Всё автоматически сохраняется в общий реестр."
    )


@router.message(Command("whoami"))
async def cmd_whoami(message: Message):
    user = await sheets.get_user(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы. /start")
        return
    await message.answer(
        f"👤 <b>{user['Имя']}</b>\nРоль: {role_label(user.get('Роль',''))}\n"
        f"ID: {user['Telegram ID']}",
        reply_markup=main_menu_role(user.get("Роль", "")),
    )


# ── Открыть карточку ──────────────────────────────────────────────────────────

async def render_and_send(message: Message, task: dict, user: dict):
    role = user.get("Роль", "")
    is_creator = str(task.get(cfg.H_INITIATOR_TG)) == str(user["Telegram ID"])
    is_assignee = str(task.get(cfg.H_EXECUTOR_TG)) == str(user["Telegram ID"])
    kb = card_kb(task, role, is_creator, is_assignee)
    await message.answer(task_card(task), reply_markup=kb)


@router.callback_query(F.data.startswith("open:"))
async def cb_open(callback: CallbackQuery):
    task_id = callback.data.split(":", 1)[1]
    user = await sheets.get_user(callback.from_user.id)
    task = await sheets.get_task(task_id)
    if not user or not task:
        await callback.answer("Не найдено", show_alert=True)
        return
    await render_and_send(callback.message, task, user)
    await callback.answer()


# ── Поиск ─────────────────────────────────────────────────────────────────────

@router.message(F.text == "🔍 Поиск")
@router.message(Command("search"))
async def btn_search(message: Message, state: FSMContext):
    user = await sheets.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    await message.answer(
        "🔍 Введите запрос (клиент, номер дела, орган, ID, слово из задачи):"
    )
    await state.set_state(Search.query)


@router.message(Search.query)
async def do_search(message: Message, state: FSMContext):
    await state.clear()
    query = message.text.strip()
    results = await sheets.search_tasks(query, limit=15)
    if not results:
        await message.answer(f"По запросу «{query}» ничего не найдено.")
        return
    lines = [f"🔍 Найдено: {len(results)}\n"] + [short_line(t) for t in results]
    await message.answer("\n".join(lines), reply_markup=open_list_kb(results))


# ── Комментарий (общий для всех ролей) ────────────────────────────────────────

@router.callback_query(F.data.startswith("comment:"))
async def cb_comment(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split(":", 1)[1]
    await state.update_data(comment_task=task_id)
    await callback.message.answer(f"💬 Напишите комментарий к поручению {task_id}:")
    await state.set_state(Comment.text)
    await callback.answer()


@router.message(Comment.text)
async def save_comment(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    task_id = data.get("comment_task")
    await state.clear()
    user = await sheets.get_user(message.from_user.id)
    author = user["Имя"] if user else message.from_user.full_name
    text = message.text.strip()

    await sheets.append_comment(task_id, author, text)
    await sheets.log(author, "комментарий", task_id, text[:80])
    task = await sheets.get_task(task_id)

    await message.answer(f"✅ Комментарий к {task_id} сохранён.")

    # Уведомляем заинтересованных, кроме автора
    recipients = set()
    if task:
        recipients.add(g(task, cfg.H_INITIATOR_TG))
        recipients.add(g(task, cfg.H_EXECUTOR_TG))
    for sid in await sheets.secretary_tg_ids():
        recipients.add(str(sid))
    recipients.discard(str(message.from_user.id))
    recipients.discard("")

    await notify(
        bot, recipients,
        f"💬 <b>Новый комментарий к {task_id}</b>\n"
        f"От: {author}\n"
        f"🏛 {g(task, cfg.H_ORGAN)} · {g(task, cfg.H_CLIENT)}\n\n«{text}»",
    )
