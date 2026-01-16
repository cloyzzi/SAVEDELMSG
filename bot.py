import asyncio
import json
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.types import Update
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
import database as db
from handlers import router


async def on_startup(bot: Bot):
    await db.init_db()
    
    # Добавляем первого админа (из config)
    await db.add_admin(config.ADMIN_ID)
    
    me = await bot.get_me()
    print(f"\n✅ Бот запущен: @{me.username}")
    print(f"👑 Главный админ: {config.ADMIN_ID}\n")


async def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)
    
    allowed_updates = [
        "message",
        "callback_query",
        "business_connection",
        "business_message",
        "edited_business_message",
        "deleted_business_messages",
        "pre_checkout_query"
    ]
    
    print("🚀 Запуск бота...")
    await dp.start_polling(bot, allowed_updates=allowed_updates)


if __name__ == "__main__":
    asyncio.run(main())