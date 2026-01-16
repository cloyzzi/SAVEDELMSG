import os
from datetime import datetime
from aiogram import Router, Bot, F
from aiogram.types import (
    Message, BusinessConnection, BusinessMessagesDeleted, 
    FSInputFile, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import database as db

router = Router()


def get_user_media_dir(user_id: int) -> str:
    path = os.path.join(config.MEDIA_DIR, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path


# ==================== КЛАВИАТУРЫ ====================

def main_menu_kb(is_admin: bool = False):
    """Главное меню"""
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Моя подписка", callback_data="my_subscription")
    kb.button(text="🛒 Купить подписку", callback_data="buy_subscription")
    kb.button(text="📊 Статистика", callback_data="my_stats")
    kb.button(text="📢 Новости", url="https://t.me/Anvrvmod")
    kb.button(text="💬 Поддержка", url="https://t.me/mkhmmm_1")
    kb.button(text="ℹ️ Помощь", callback_data="help")
    
    if is_admin:
        kb.button(text="👑 Админ-панель", callback_data="admin_panel")
    
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def buy_subscription_kb():
    """Меню покупки подписки"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 1 месяц - 75⭐", callback_data="buy_1")
    kb.button(text="📦 2 месяца - 130⭐", callback_data="buy_2")
    kb.button(text="📦 3 месяца - 200⭐", callback_data="buy_3")
    kb.button(text="◀️ Назад", callback_data="back_to_menu")
    kb.adjust(1)
    return kb.as_markup()


def admin_panel_kb():
    """Админ-панель"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Статистика", callback_data="admin_stats")
    kb.button(text="👥 Пользователи", callback_data="admin_users")
    kb.button(text="➕ Выдать подписку", callback_data="admin_give_sub")
    kb.button(text="➖ Забрать подписку", callback_data="admin_remove_sub")
    kb.button(text="👑 Управление админами", callback_data="admin_manage")
    kb.button(text="◀️ Назад", callback_data="back_to_menu")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def back_button():
    """Кнопка назад"""
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад в меню", callback_data="back_to_menu")
    return kb.as_markup()


# ==================== ПРОВЕРКА ПОДПИСКИ ====================

async def check_user_access(user_id: int) -> bool:
    """Проверить доступ пользователя"""
    if await db.is_admin(user_id):
        return True
    return await db.check_subscription(user_id)


# ==================== МЕДИА ====================

async def download_media(bot: Bot, message: Message, owner_id: int) -> tuple:
    media_type = None
    file_path = None
    
    if message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
        ext = ".jpg"
    elif message.video:
        media_type = "video"
        file_id = message.video.file_id
        ext = ".mp4"
    elif message.video_note:
        media_type = "video_note"
        file_id = message.video_note.file_id
        ext = ".mp4"
    elif message.voice:
        media_type = "voice"
        file_id = message.voice.file_id
        ext = ".ogg"
    else:
        return None, None
    
    try:
        file = await bot.get_file(file_id)
        timestamp = int(datetime.now().timestamp())
        file_name = f"{media_type}_{message.chat.id}_{message.message_id}_{timestamp}{ext}"
        file_path = os.path.join(get_user_media_dir(owner_id), file_name)
        await bot.download_file(file.file_path, file_path)
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        file_path = None
    
    return media_type, file_path


# ==================== BUSINESS HANDLERS ====================

@router.business_connection()
async def on_business_connect(event: BusinessConnection, bot: Bot):
    print(f"\n🔗 Business connection: {event.user.first_name}")
    
    if event.is_enabled:
        await db.add_user(
            user_id=event.user.id,
            username=event.user.username or "",
            first_name=event.user.first_name,
            connection_id=event.id
        )
        
        has_access = await check_user_access(event.user.id)
        is_admin = await db.is_admin(event.user.id)
        
        if has_access:
            sub = await db.get_subscription(event.user.id)
            expires_text = ""
            
            if sub and not is_admin:
                expires_at = datetime.fromisoformat(sub['expires_at'])
                expires_text = f"\n│ 📅 <b>Подписка до:</b> {expires_at.strftime('%d.%m.%Y')}"
            
            text = (
                "╔═══════════════════════════════════╗\n"
                "        ✅ <b>БОТ ПОДКЛЮЧЁН</b>\n"
                "╚═══════════════════════════════════╝\n\n"
                f"┌─────────────────────────────────┐\n"
                f"│ 🔥 <b>Теперь вам доступно:</b>{expires_text}\n"
                f"│\n"
                f"│ • Сохранение одноразовых медиа\n"
                f"│ • Просмотр удалённых сообщений\n"
                f"│ • Сохранение всех фото/видео\n"
                f"│ • Архивация голосовых сообщений\n"
                f"└─────────────────────────────────┘\n\n"
                f"💡 <b>Используйте</b> /menu <b>для управления</b>"
            )
            
            await bot.send_message(
                event.user.id,
                text,
                reply_markup=main_menu_kb(is_admin),
                parse_mode="HTML"
            )
        else:
            text = (
                "╔═══════════════════════════════════╗\n"
                "      ⚠️ <b>ТРЕБУЕТСЯ ПОДПИСКА</b>\n"
                "╚═══════════════════════════════════╝\n\n"
                "┌─────────────────────────────────┐\n"
                "│ ❌ <b>Бот подключён, но не активен</b>\n"
                "│\n"
                "│ Для работы бота необходима\n"
                "│ активная подписка\n"
                "└─────────────────────────────────┘\n\n"
                "💡 <b>Нажмите кнопку ниже для покупки</b>"
            )
            
            await bot.send_message(
                event.user.id,
                text,
                reply_markup=main_menu_kb(),
                parse_mode="HTML"
            )


@router.business_message()
async def on_business_message(message: Message, bot: Bot):
    user = message.from_user
    chat = message.chat
    connection_id = message.business_connection_id
    
    owner = await db.get_user_by_connection(connection_id)
    
    if not owner:
        owner_id = user.id if user else chat.id
        await db.add_user(
            user_id=owner_id,
            username=user.username if user else "",
            first_name=user.first_name if user else chat.first_name,
            connection_id=connection_id
        )
        owner = {"user_id": owner_id}
    
    owner_id = owner["user_id"]
    
    # ПРОВЕРКА ПОДПИСКИ
    has_access = await check_user_access(owner_id)
    
    if not has_access:
        return
    
    # REPLY С ОДНОРАЗОВЫМ МЕДИА
    if message.reply_to_message:
        reply = message.reply_to_message
        is_protected = getattr(reply, 'has_protected_content', False)
        
        if is_protected and (reply.photo or reply.video):
            media_type, media_path = await download_media(bot, reply, owner_id)
            
            if media_path:
                sender = reply.from_user
                await db.save_message(
                    owner_id=owner_id,
                    message_id=reply.message_id,
                    chat_id=chat.id,
                    from_user_id=sender.id if sender else 0,
                    from_username=sender.username if sender else "",
                    from_first_name=sender.first_name if sender else chat.first_name,
                    text=None,
                    caption=reply.caption,
                    media_type=media_type,
                    media_path=media_path,
                    is_protected=True
                )
                
                sender_name = sender.first_name if sender else chat.first_name
                
                notification = (
                    "╔═══════════════════════════════════╗\n"
                    "      🔥 <b>ОДНОРАЗОВОЕ МЕДИА</b>\n"
                    "╚═══════════════════════════════════╝\n\n"
                    f"┌─────────────────────────────────┐\n"
                    f"│ 📁 <b>Тип:</b> {media_type.upper()}\n"
                    f"│ 👤 <b>От:</b> {sender_name}\n"
                    f"│ 💬 <b>Чат:</b> {chat.first_name}\n"
                    f"│ ✅ <b>Статус:</b> Сохранено\n"
                    f"└─────────────────────────────────┘"
                )
                
                await bot.send_message(owner_id, notification, parse_mode="HTML")
                
                try:
                    if media_type == "photo":
                        await bot.send_photo(owner_id, FSInputFile(media_path), caption=f"📷 От: <b>{sender_name}</b>", parse_mode="HTML")
                    elif media_type == "video":
                        await bot.send_video(owner_id, FSInputFile(media_path), caption=f"🎥 От: <b>{sender_name}</b>", parse_mode="HTML")
                except:
                    pass
                
                return
    
    # ОБЫЧНЫЕ СООБЩЕНИЯ
    is_protected = getattr(message, 'has_protected_content', False)
    
    if not is_protected:
        media_type, media_path = await download_media(bot, message, owner_id)
    else:
        media_type, media_path = None, None
    
    await db.save_message(
        owner_id=owner_id,
        message_id=message.message_id,
        chat_id=chat.id,
        from_user_id=user.id if user else 0,
        from_username=user.username if user else "",
        from_first_name=user.first_name if user else chat.first_name,
        text=message.text,
        caption=message.caption,
        media_type=media_type,
        media_path=media_path,
        is_protected=is_protected
    )


@router.deleted_business_messages()
async def on_deleted_messages(event: BusinessMessagesDeleted, bot: Bot):
    owner = await db.get_user_by_connection(event.business_connection_id)
    if not owner:
        return
    
    owner_id = owner["user_id"]
    
    if not await check_user_access(owner_id):
        return
    
    chat = event.chat
    message_ids = list(event.message_ids)
    
    deleted = await db.get_deleted_messages(owner_id, chat.id, message_ids)
    await db.mark_deleted(owner_id, chat.id, message_ids)
    
    if not deleted:
        return
    
    header = (
        "╔═══════════════════════════════════╗\n"
        "      🗑 <b>УДАЛЁННЫЕ СООБЩЕНИЯ</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        f"┌─────────────────────────────────┐\n"
        f"│ 📊 <b>Удалено:</b> {len(deleted)} сообщений\n"
        f"│ 💬 <b>Чат:</b> {chat.first_name}\n"
        f"└─────────────────────────────────┘"
    )
    
    await bot.send_message(owner_id, header, parse_mode="HTML")
    
    for msg in deleted:
        sender_name = msg['from_first_name'] or "Неизвестный"
        
        if msg['text']:
            full_text = msg['text']
            
            if len(full_text) <= 3900:
                formatted = (
                    f"┌─────────────────────────────────┐\n"
                    f"│ 👤 <b>{sender_name}</b>\n"
                    f"└─────────────────────────────────┘\n\n"
                    f"{full_text}"
                )
                await bot.send_message(owner_id, formatted, parse_mode="HTML")
            else:
                chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
                for i, chunk in enumerate(chunks):
                    part = f"[{i+1}/{len(chunks)}]\n" if len(chunks) > 1 else ""
                    await bot.send_message(owner_id, f"👤 <b>{sender_name}</b>\n\n{part}{chunk}", parse_mode="HTML")
        
        if msg['media_path'] and os.path.exists(msg['media_path']):
            try:
                caption = f"🗑 От: <b>{sender_name}</b>"
                if msg['media_type'] == "photo":
                    await bot.send_photo(owner_id, FSInputFile(msg['media_path']), caption=caption, parse_mode="HTML")
                elif msg['media_type'] == "video":
                    await bot.send_video(owner_id, FSInputFile(msg['media_path']), caption=caption, parse_mode="HTML")
            except:
                pass


# ==================== КОМАНДЫ ====================

@router.message(Command("start"))
async def cmd_start(message: Message):
    is_admin = await db.is_admin(message.from_user.id)
    has_access = await check_user_access(message.from_user.id)
    
    status = "✅ <b>Активна</b>" if has_access else "❌ <b>Не активна</b>"
    admin_badge = "👑 <b>ВЫ АДМИНИСТРАТОР</b>\n\n" if is_admin else ""
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "        🤖 <b>ДОБРО ПОЖАЛОВАТЬ</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        f"{admin_badge}"
        f"┌─────────────────────────────────┐\n"
        f"│ 📌 <b>Подписка:</b> {status}\n"
        f"│\n"
        f"│ <b>Бот для сохранения сообщений</b>\n"
        f"│ <b>через Telegram Business</b>\n"
        f"└─────────────────────────────────┘\n\n"
        f"💡 <b>Выберите действие из меню ниже</b>"
    )
    
    await message.answer(text, reply_markup=main_menu_kb(is_admin), parse_mode="HTML")


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    is_admin = await db.is_admin(message.from_user.id)
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "           📱 <b>ГЛАВНОЕ МЕНЮ</b>\n"
        "╚═══════════════════════════════════╝"
    )
    
    await message.answer(text, reply_markup=main_menu_kb(is_admin), parse_mode="HTML")


# ==================== CALLBACK HANDLERS ====================

@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery):
    is_admin = await db.is_admin(callback.from_user.id)
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "           📱 <b>ГЛАВНОЕ МЕНЮ</b>\n"
        "╚═══════════════════════════════════╝"
    )
    
    await callback.message.edit_text(text, reply_markup=main_menu_kb(is_admin), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "my_subscription")
async def cb_my_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id)
    
    if is_admin:
        text = (
            "╔═══════════════════════════════════╗\n"
            "         👑 <b>АДМИНИСТРАТОР</b>\n"
            "╚═══════════════════════════════════╝\n\n"
            "┌─────────────────────────────────┐\n"
            "│ ♾️ <b>Безлимитный доступ</b>\n"
            "│\n"
            "│ У вас полный доступ ко всем\n"
            "│ функциям бота без ограничений\n"
            "└─────────────────────────────────┘"
        )
    else:
        sub = await db.get_subscription(user_id)
        
        if sub:
            expires_at = datetime.fromisoformat(sub['expires_at'])
            is_active = expires_at > datetime.now()
            
            if is_active:
                days_left = (expires_at - datetime.now()).days
                text = (
                    "╔═══════════════════════════════════╗\n"
                    "         ✅ <b>ПОДПИСКА АКТИВНА</b>\n"
                    "╚═══════════════════════════════════╝\n\n"
                    "┌─────────────────────────────────┐\n"
                    f"│ 📅 <b>Действует до:</b>\n"
                    f"│    {expires_at.strftime('%d.%m.%Y %H:%M')}\n"
                    f"│\n"
                    f"│ ⏳ <b>Осталось дней:</b> {days_left}\n"
                    "└─────────────────────────────────┘\n\n"
                    "💡 <b>Вы можете продлить подписку</b>\n"
                    "<b>в любой момент</b>"
                )
            else:
                text = (
                    "╔═══════════════════════════════════╗\n"
                    "        ❌ <b>ПОДПИСКА ИСТЕКЛА</b>\n"
                    "╚═══════════════════════════════════╝\n\n"
                    "┌─────────────────────────────────┐\n"
                    f"│ 📅 <b>Истекла:</b> {expires_at.strftime('%d.%m.%Y')}\n"
                    "│\n"
                    "│ Продлите подписку для\n"
                    "│ продолжения работы\n"
                    "└─────────────────────────────────┘"
                )
        else:
            text = (
                "╔═══════════════════════════════════╗\n"
                "          ❌ <b>НЕТ ПОДПИСКИ</b>\n"
                "╚═══════════════════════════════════╝\n\n"
                "┌─────────────────────────────────┐\n"
                "│ Для использования бота\n"
                "│ необходимо приобрести подписку\n"
                "└─────────────────────────────────┘\n\n"
                "💡 <b>Нажмите кнопку ниже для покупки</b>"
            )
    
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "buy_subscription")
async def cb_buy_subscription(callback: CallbackQuery):
    text = (
        "╔═══════════════════════════════════╗\n"
        "         💎 <b>ТАРИФНЫЕ ПЛАНЫ</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        "┌─────────────────────────────────┐\n"
        "│ 📦 <b>1 МЕСЯЦ</b>\n"
        "│ ⭐ 75 звёзд\n"
        "│ 💰 Экономия: 0%\n"
        "└─────────────────────────────────┘\n\n"
        "┌─────────────────────────────────┐\n"
        "│ 📦 <b>2 МЕСЯЦА</b>\n"
        "│ ⭐ 130 звёзд\n"
        "│ 💰 Экономия: 13%\n"
        "└─────────────────────────────────┘\n\n"
        "┌─────────────────────────────────┐\n"
        "│ 📦 <b>3 МЕСЯЦА</b> 🔥\n"
        "│ ⭐ 200 звёзд\n"
        "│ 💰 Экономия: 11%\n"
        "└─────────────────────────────────┘\n\n"
        "✨ <b>Преимущества подписки:</b>\n"
        "• 🔥 Сохранение одноразовых медиа\n"
        "• 🗑 Удалённые сообщения\n"
        "• 📷 Все фото и видео\n"
        "• 🎤 Голосовые сообщения\n\n"
        "💡 <b>Выберите тариф ниже</b>"
    )
    
    await callback.message.edit_text(text, reply_markup=buy_subscription_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(callback: CallbackQuery, bot: Bot):
    months = int(callback.data.split("_")[1])
    
    prices = {1: 75, 2: 130, 3: 200}
    amount = prices[months]
    
    month_names = {1: "1 месяц", 2: "2 месяца", 3: "3 месяца"}
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Подписка на {month_names[months]}",
        description=f"Подписка на бота для сохранения сообщений на {month_names[months]}",
        payload=f"sub_{months}_{callback.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Подписка {month_names[months]}", amount=amount)]
    )
    
    await callback.answer("✅ Счёт отправлен")


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    months = int(payload.split("_")[1])
    user_id = message.from_user.id
    
    expires_at = await db.add_subscription(user_id, months)
    
    await db.save_payment(
        user_id=user_id,
        amount=message.successful_payment.total_amount,
        months=months,
        payment_id=message.successful_payment.telegram_payment_charge_id,
        status="paid"
    )
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "        ✅ <b>ОПЛАТА УСПЕШНА</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        "┌─────────────────────────────────┐\n"
        f"│ 🎉 <b>Подписка активирована!</b>\n"
        f"│\n"
        f"│ 📦 <b>Тариф:</b> {months} {'месяц' if months == 1 else 'месяца' if months < 3 else 'месяцев'}\n"
        f"│ 📅 <b>Действует до:</b>\n"
        f"│    {expires_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"└─────────────────────────────────┘\n\n"
        f"💚 <b>Спасибо за покупку!</b>\n\n"
        f"💡 Используйте /menu для управления"
    )
    
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "my_stats")
async def cb_my_stats(callback: CallbackQuery):
    stats = await db.get_user_stats(callback.from_user.id)
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "          📊 <b>СТАТИСТИКА</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        "┌─────────────────────────────────┐\n"
        f"│ 📨 <b>Всего сообщений:</b> {stats['total']}\n"
        f"│ 🗑 <b>Удалённых:</b> {stats['deleted']}\n"
        f"│ 📷 <b>С медиа:</b> {stats['media']}\n"
        f"│ 🔥 <b>Одноразовых:</b> {stats['protected']}\n"
        f"└─────────────────────────────────┘"
    )
    
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    text = (
        "╔═══════════════════════════════════╗\n"
        "            ℹ️ <b>СПРАВКА</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        "┌─────────────────────────────────┐\n"
        "│ 🔥 <b>ОДНОРАЗОВЫЕ МЕДИА</b>\n"
        "└─────────────────────────────────┘\n"
        "1️⃣ Получите одноразовое фото/видео\n"
        "2️⃣ Ответьте на него (свайп вправо)\n"
        "3️⃣ Напишите любой текст\n"
        "4️⃣ Получите сохранённый файл!\n\n"
        "┌─────────────────────────────────┐\n"
        "│ 🗑 <b>УДАЛЁННЫЕ СООБЩЕНИЯ</b>\n"
        "└─────────────────────────────────┘\n"
        "Сохраняются автоматически при\n"
        "удалении собеседником\n\n"
        "┌─────────────────────────────────┐\n"
        "│ 📖 <b>ПОДКЛЮЧЕНИЕ БОТА</b>\n"
        "└─────────────────────────────────┘\n"
        "<b>Настройки</b> → <b>Telegram Business</b> →\n"
        "<b>Чат-боты</b> → <b>Добавить бота</b>\n\n"
        "💬 <b>Поддержка:</b> @mkhmmm_1\n"
        "📢 <b>Новости:</b> @Anvrvmod"
    )
    
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="HTML")
    await callback.answer()


# ==================== АДМИН-ПАНЕЛЬ ====================

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "         👑 <b>АДМИН-ПАНЕЛЬ</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        "┌─────────────────────────────────┐\n"
        "│ Выберите действие из меню ниже\n"
        "└─────────────────────────────────┘"
    )
    
    await callback.message.edit_text(text, reply_markup=admin_panel_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    stats = await db.get_total_stats()
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "       📊 <b>ОБЩАЯ СТАТИСТИКА</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        "┌─────────────────────────────────┐\n"
        f"│ 👥 <b>Всего пользователей:</b> {stats['users']}\n"
        f"│ ✅ <b>Активных подписок:</b> {stats['active_subs']}\n"
        f"│ 📨 <b>Всего сообщений:</b> {stats['messages']}\n"
        f"│ ⭐ <b>Доход (Stars):</b> {stats['revenue']}\n"
        f"└─────────────────────────────────┘"
    )
    
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    users = await db.get_all_users()
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "         👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        "<b>Последние 10 пользователей:</b>\n\n"
    )
    
    for user in users[:10]:
        has_sub = await db.check_subscription(user['user_id'])
        status = "✅" if has_sub else "❌"
        text += f"{status} <b>{user['first_name']}</b> (ID: <code>{user['user_id']}</code>)\n"
    
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="HTML")
    await callback.answer()


user_states = {}


@router.callback_query(F.data == "admin_give_sub")
async def cb_admin_give_sub(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    user_states[callback.from_user.id] = "waiting_user_id_give"
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "        ➕ <b>ВЫДАТЬ ПОДПИСКУ</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        "┌─────────────────────────────────┐\n"
        "│ Отправьте ID пользователя и\n"
        "│ количество месяцев через пробел\n"
        "└─────────────────────────────────┘\n\n"
        "📝 <b>Пример:</b> <code>123456789 3</code>"
    )
    
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_remove_sub")
async def cb_admin_remove_sub(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    user_states[callback.from_user.id] = "waiting_user_id_remove"
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "       ➖ <b>УДАЛИТЬ ПОДПИСКУ</b>\n"
        "╚═══════════════════════════════════╝\n\n"
        "┌─────────────────────────────────┐\n"
        "│ Отправьте ID пользователя\n"
        "└─────────────────────────────────┘\n\n"
        "📝 <b>Пример:</b> <code>123456789</code>"
    )
    
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="HTML")
    await callback.answer()


@router.message(F.text)
async def handle_admin_input(message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_states:
        return
    
    if not await db.is_admin(user_id):
        return
    
    state = user_states[user_id]
    
    if state == "waiting_user_id_give":
        try:
            parts = message.text.split()
            target_user_id = int(parts[0])
            months = int(parts[1])
            
            expires_at = await db.add_subscription(target_user_id, months)
            
            text = (
                "╔═══════════════════════════════════╗\n"
                "       ✅ <b>ПОДПИСКА ВЫДАНА</b>\n"
                "╚═══════════════════════════════════╝\n\n"
                "┌─────────────────────────────────┐\n"
                f"│ 👤 <b>User ID:</b> <code>{target_user_id}</code>\n"
                f"│ 📦 <b>Срок:</b> {months} мес.\n"
                f"│ 📅 <b>До:</b> {expires_at.strftime('%d.%m.%Y')}\n"
                f"└─────────────────────────────────┘"
            )
            
            await message.answer(text, parse_mode="HTML")
            del user_states[user_id]
        except:
            await message.answer("❌ <b>Неверный формат</b>\n\nИспользуйте: <code>ID месяцы</code>", parse_mode="HTML")
    
    elif state == "waiting_user_id_remove":
        try:
            target_user_id = int(message.text.strip())
            await db.remove_subscription(target_user_id)
            
            text = (
                "╔═══════════════════════════════════╗\n"
                "      ✅ <b>ПОДПИСКА УДАЛЕНА</b>\n"
                "╚═══════════════════════════════════╝\n\n"
                "┌─────────────────────────────────┐\n"
                f"│ 👤 <b>User ID:</b> <code>{target_user_id}</code>\n"
                f"└─────────────────────────────────┘"
            )
            
            await message.answer(text, parse_mode="HTML")
            del user_states[user_id]
        except:
            await message.answer("❌ <b>Неверный ID</b>", parse_mode="HTML")