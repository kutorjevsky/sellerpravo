from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot.config import ROLES, ROLE_EMOJI
from bot.keyboards import (
    role_keyboard, menu_representative, menu_secretary, menu_executor,
)
from bot.states import Registration

router = Router()


def main_menu(role: str):
    if role in ("representative",):
        return menu_representative()
    if role == "secretary":
        return menu_secretary()
    return menu_executor()


def role_label(role: str) -> str:
    return f"{ROLE_EMOJI.get(role, '')} {ROLES.get(role, role)}"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)

    if user:
        await message.answer(
            f"Добро пожаловать, <b>{user['name']}</b>!\n"
            f"Ваша роль: {role_label(user['role'])}",
            reply_markup=main_menu(user["role"]),
        )
        return

    await message.answer(
        "Добро пожаловать в систему заданий <b>Seller Pravo</b>!\n\n"
        "Как вас зовут? Введите имя и фамилию:",
    )
    await state.set_state(Registration.waiting_name)


@router.message(Registration.waiting_name)
async def reg_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Введите корректное имя (минимум 2 символа).")
        return
    await state.update_data(name=name)
    await message.answer(
        f"Приятно познакомиться, <b>{name}</b>!\n\nВыберите вашу роль:",
        reply_markup=role_keyboard(),
    )
    await state.set_state(Registration.waiting_role)


@router.callback_query(Registration.waiting_role, F.data.startswith("role:"))
async def reg_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":")[1]
    if role not in ROLES:
        await callback.answer("Неверная роль.")
        return

    data = await state.get_data()
    name = data["name"]
    username = callback.from_user.username

    await db.create_user(callback.from_user.id, name, role, username)
    await state.clear()

    await callback.message.edit_text(
        f"✅ Регистрация завершена!\n\n"
        f"Имя: <b>{name}</b>\n"
        f"Роль: {role_label(role)}\n\n"
        f"Используйте меню для работы с заданиями.",
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu(role))
    await callback.answer()


@router.message(Command("whoami"))
async def cmd_whoami(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы. Введите /start.")
        return
    await message.answer(
        f"👤 <b>{user['name']}</b>\n"
        f"Роль: {role_label(user['role'])}\n"
        f"ID: {user['telegram_id']}",
        reply_markup=main_menu(user["role"]),
    )


@router.message(Command("changerole"))
async def cmd_changerole(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь: /start")
        return
    await message.answer("Выберите новую роль:", reply_markup=role_keyboard())
    await state.update_data(name=user["name"])
    await state.set_state(Registration.waiting_role)


@router.message(Command("help"))
async def cmd_help(message: Message):
    user = await db.get_user(message.from_user.id)
    role = user["role"] if user else "—"

    text = (
        "<b>Команды бота</b>\n\n"
        "/start — главное меню\n"
        "/whoami — ваш профиль\n"
        "/changerole — сменить роль\n"
        "/help — эта справка\n"
    )
    if role in ("representative", "secretary"):
        text += "\n<b>Для представителей:</b>\n📝 Новое задание — создать задание\n📋 Мои задания — история\n"
    if role == "secretary":
        text += "\n<b>Для секретаря:</b>\n📋 На сегодня / На завтра — распределение заданий\n"
    if role in ("courier", "assistant"):
        text += "\n<b>Для исполнителей:</b>\n📋 Мои задания — задания на сегодня\n📅 Зарегистрировать выезд — куда едете\n"

    await message.answer(text)
