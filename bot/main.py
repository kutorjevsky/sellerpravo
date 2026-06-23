import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot import config as cfg
from bot import sheets
from bot.handlers import common, representative, secretary, executor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    if not cfg.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан (см. .env / переменные окружения).")
    if not cfg.SPREADSHEET_ID:
        raise RuntimeError("SPREADSHEET_ID не задан (см. ВНЕДРЕНИЕ.md).")

    logger.info("Подключаюсь к Google-таблице…")
    sh = await sheets.connect()
    logger.info("Подключено: %s", sh.title)

    # Первичная настройка структуры (выпадающие списки, цвета, панель).
    # Включите AUTO_SETUP=1 для ПЕРВОГО запуска, затем уберите переменную.
    if os.getenv("AUTO_SETUP", "").strip() in ("1", "true", "yes"):
        logger.info("AUTO_SETUP=on → оформляю структуру таблицы…")
        from bot import setup_sheet
        await asyncio.to_thread(setup_sheet.main)
        logger.info("Оформление завершено. Уберите AUTO_SETUP и перезапустите.")

    bot = Bot(token=cfg.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(representative.router)
    dp.include_router(secretary.router)
    dp.include_router(executor.router)

    logger.info("Бот запущен.")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
