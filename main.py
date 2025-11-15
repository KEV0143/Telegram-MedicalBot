from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
from pathlib import Path
from utils.config import load_settings
from utils.logger import setup_logging, log_info
from utils.db import Database
from utils.handlers import register_all_handlers
from utils.middleware import ActionLoggerMiddleware, ConsentGateMiddleware

async def main():
    setup_logging()
    settings = load_settings()

    log_info(f"Добро пожаловать в бота {settings.bot_name}!")
    if Path(settings.db_path).exists():
        log_info("Обнаружена база данных.")
    else:
        log_info("Происходит создание базы данных.")
    db = Database(settings.db_path)
    log_info("Происходит синхронизация базы данных.")
    db.sync_documents_from_disk(settings.docs_dir)

    try:
        admins_from_db = set(db.list_user_ids_by_role("Администратор"))
        operators_from_db = set(db.list_user_ids_by_role("Оператор"))
        settings.admin_ids = sorted(set(getattr(settings, "admin_ids", [])) | admins_from_db)
        settings.operator_ids = sorted(set(getattr(settings, "operator_ids", [])) | operators_from_db)
    except Exception as e:
        log_info(f"Не удалось синхронизировать роли из БД: {e}")

    admins = ", ".join(str(i) for i in sorted(settings.admin_ids)) or "—"
    ops = ", ".join(str(i) for i in sorted(settings.operator_ids)) or "—"
    log_info("Успешно, бот готов к работе.")
    log_info("ID Администрации:")
    log_info(f"{admins}")
    log_info("ID Операторов:")
    log_info(f"{ops}")

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(ActionLoggerMiddleware(db, settings))
    dp.callback_query.middleware(ActionLoggerMiddleware(db, settings))
    dp.message.middleware(ConsentGateMiddleware(db))
    dp.callback_query.middleware(ConsentGateMiddleware(db))

    register_all_handlers(dp, db, settings)

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
