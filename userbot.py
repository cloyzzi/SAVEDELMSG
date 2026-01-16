import asyncio
import os
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import MessageMediaType

# Ваши данные (получить на https://my.telegram.org)
API_ID = 12345678  # Замените на свой
API_HASH = "ваш_api_hash"  # Замените на свой
BOT_TOKEN = "токен_бота"  # Для отправки уведомлений
ADMIN_ID = 8078466679  # Ваш ID

MEDIA_DIR = "saved_media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# Userbot (ваш аккаунт)
user = Client("my_account", api_id=API_ID, api_hash=API_HASH)

# Бот для уведомлений
bot = Client("notify_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@user.on_message(filters.private & filters.incoming)
async def handle_private_message(client: Client, message: Message):
    """Перехват всех входящих сообщений"""
    
    print(f"\n📨 Сообщение от {message.from_user.first_name}")
    
    # Проверяем медиа
    has_media = message.media in [
        MessageMediaType.PHOTO,
        MessageMediaType.VIDEO,
        MessageMediaType.VIDEO_NOTE,
        MessageMediaType.VOICE
    ]
    
    if not has_media:
        return
    
    print(f"   Тип медиа: {message.media}")
    
    # Скачиваем медиа
    try:
        timestamp = int(datetime.now().timestamp())
        file_name = f"{message.media.value}_{message.from_user.id}_{timestamp}"
        file_path = os.path.join(MEDIA_DIR, file_name)
        
        # Pyrogram может скачать даже защищённый контент через userbot
        downloaded = await message.download(file_name=file_path)
        
        print(f"✅ Сохранено: {downloaded}")
        
        # Уведомляем через бота
        async with bot:
            caption = (
                f"📥 Медиа сохранено!\n\n"
                f"👤 От: {message.from_user.first_name}\n"
                f"📁 Тип: {message.media.value}\n"
                f"💾 Файл: {downloaded}"
            )
            
            if message.media == MessageMediaType.PHOTO:
                await bot.send_photo(ADMIN_ID, downloaded, caption=caption)
            elif message.media == MessageMediaType.VIDEO:
                await bot.send_video(ADMIN_ID, downloaded, caption=caption)
            elif message.media == MessageMediaType.VIDEO_NOTE:
                await bot.send_video_note(ADMIN_ID, downloaded)
                await bot.send_message(ADMIN_ID, caption)
            else:
                await bot.send_document(ADMIN_ID, downloaded, caption=caption)
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        
        # Если не удалось скачать - пробуем получить file_id и пересохранить
        try:
            async with bot:
                await bot.send_message(
                    ADMIN_ID,
                    f"⚠️ Не удалось скачать медиа от {message.from_user.first_name}\n"
                    f"Ошибка: {e}"
                )
        except:
            pass


@user.on_deleted_messages(filters.private)
async def handle_deleted(client: Client, messages: list[Message]):
    """Удалённые сообщения"""
    print(f"🗑 Удалено {len(messages)} сообщений")
    
    async with bot:
        await bot.send_message(
            ADMIN_ID,
            f"🗑 Удалено {len(messages)} сообщений!"
        )


async def main():
    print("🚀 Запуск userbot...")
    await user.start()
    print(f"✅ Userbot запущен как {(await user.get_me()).first_name}")
    
    # Держим работающим
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())