"""
Telegram бот для управления парсером Авито
"""
import asyncio
import json
from datetime import datetime
from typing import Dict
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from avito_parser import AvitoParser
import threading
import time
from queue import Queue

# Токен бота (хардкод для теста)
TELEGRAM_BOT_TOKEN = "8532839400:AAHatK5v4TkYELnu31zs4EcBLpNMzAZUk-0"

# Состояния для ConversationHandler
(QUERY, LOCATION, CATEGORY, PRICE_MIN, PRICE_MAX, INTERVAL) = range(6)

# Глобальные переменные
parser = None
checking = False
check_thread = None
bot_application = None  # Для доступа к боту из callback
notification_queue = Queue()  # Очередь для уведомлений


def format_item_message(item: Dict) -> str:
    """Форматирование сообщения об объявлении"""
    title = item.get('title', 'Без названия')
    price = item.get('price', 'Цена не указана')
    description = item.get('description', '')
    link = item.get('link', '')
    
    message = f"🆕 <b>НОВОЕ ОБЪЯВЛЕНИЕ!</b>\n\n"
    message += f"📦 <b>{title}</b>\n\n"
    message += f"💰 Цена: {price}\n"
    
    if description:
        desc_short = description[:100] + "..." if len(description) > 100 else description
        message += f"📝 {desc_short}\n"
    
    message += f"\n🔗 <a href='{link}'>Открыть на Авито</a>"
    
    return message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    welcome_text = """
🤖 <b>Парсер Авито</b>

Я помогу тебе отслеживать новые объявления на Авито!

<b>Доступные команды:</b>
/start - Начать работу
/setup - Настроить параметры поиска
/status - Показать текущие настройки
/start_check - Начать проверку объявлений
/stop_check - Остановить проверку
/check_now - Проверить объявления прямо сейчас

Используй /setup чтобы задать параметры поиска!
"""
    await update.message.reply_text(welcome_text, parse_mode='HTML')


async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать настройку параметров поиска"""
    await update.message.reply_text(
        "🔧 <b>Настройка параметров поиска</b>\n\n"
        "Введи название товара (например: iphone, ноутбук):",
        parse_mode='HTML'
    )
    return QUERY


async def query_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода названия товара"""
    query = update.message.text
    context.user_data['query'] = query
    
    await update.message.reply_text(
        f"✅ Название товара: <b>{query}</b>\n\n"
        "Теперь введи город/локацию (например: moskva, spb, krasnodar):\n"
        "Или отправь /skip чтобы пропустить",
        parse_mode='HTML'
    )
    return LOCATION


async def location_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода локации"""
    location = update.message.text
    context.user_data['location'] = location
    
    await update.message.reply_text(
        f"✅ Локация: <b>{location}</b>\n\n"
        "Введи категорию (например: elektronika, transport) или /skip:",
        parse_mode='HTML'
    )
    return CATEGORY


async def category_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода категории"""
    category = update.message.text
    context.user_data['category'] = category
    
    await update.message.reply_text(
        f"✅ Категория: <b>{category}</b>\n\n"
        "Введи минимальную цену (или /skip):",
        parse_mode='HTML'
    )
    return PRICE_MIN


async def price_min_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода минимальной цены"""
    price_min = update.message.text
    context.user_data['price_min'] = price_min
    
    await update.message.reply_text(
        f"✅ Минимальная цена: <b>{price_min}</b>\n\n"
        "Введи максимальную цену (или /skip):",
        parse_mode='HTML'
    )
    return PRICE_MAX


async def price_max_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода максимальной цены"""
    price_max = update.message.text
    context.user_data['price_max'] = price_max
    
    await update.message.reply_text(
        f"✅ Максимальная цена: <b>{price_max}</b>\n\n"
        "Введи интервал проверки в минутах (по умолчанию 1):",
        parse_mode='HTML'
    )
    return INTERVAL


async def interval_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода интервала"""
    try:
        interval = int(update.message.text)
        context.user_data['interval'] = interval
    except ValueError:
        interval = 1
        context.user_data['interval'] = interval
    
    # Сохраняем конфигурацию
    global parser
    if parser is None:
        parser = AvitoParser(notify_callback=send_notification_sync, use_db=True, use_browser=True)
    
    # Обновляем конфигурацию
    parser.config['search_params'] = {
        'query': context.user_data.get('query', ''),
        'location': context.user_data.get('location', ''),
        'category': context.user_data.get('category', ''),
        'price_min': context.user_data.get('price_min', ''),
        'price_max': context.user_data.get('price_max', ''),
        'sort': 'date'
    }
    parser.config['check_interval_minutes'] = interval
    parser.save_config()  # Сохранит в БД если use_db=True
    
    # Сохраняем chat_id для уведомлений
    context.bot_data['chat_id'] = update.effective_chat.id
    
    config_text = f"""
✅ <b>Настройка завершена!</b>

📦 Товар: {context.user_data.get('query', 'Не указано')}
📍 Локация: {context.user_data.get('location', 'Не указано')}
📂 Категория: {context.user_data.get('category', 'Не указано')}
💰 Цена: {context.user_data.get('price_min', '')} - {context.user_data.get('price_max', '')}
⏰ Интервал: {interval} мин

Используй /start_check чтобы начать проверку!
"""
    await update.message.reply_text(config_text, parse_mode='HTML')
    
    return ConversationHandler.END


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить текущий шаг"""
    current_state = context.user_data.get('current_state')
    
    if current_state == LOCATION:
        context.user_data['location'] = ''
        await update.message.reply_text(
            "✅ Локация пропущена\n\n"
            "Введи категорию (или /skip):",
            parse_mode='HTML'
        )
        return CATEGORY
    elif current_state == CATEGORY:
        context.user_data['category'] = ''
        await update.message.reply_text(
            "✅ Категория пропущена\n\n"
            "Введи минимальную цену (или /skip):",
            parse_mode='HTML'
        )
        return PRICE_MIN
    elif current_state == PRICE_MIN:
        context.user_data['price_min'] = ''
        await update.message.reply_text(
            "✅ Минимальная цена пропущена\n\n"
            "Введи максимальную цену (или /skip):",
            parse_mode='HTML'
        )
        return PRICE_MAX
    elif current_state == PRICE_MAX:
        context.user_data['price_max'] = ''
        await update.message.reply_text(
            "✅ Максимальная цена пропущена\n\n"
            "Введи интервал проверки в минутах:",
            parse_mode='HTML'
        )
        return INTERVAL
    
    return current_state


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить настройку"""
    await update.message.reply_text("❌ Настройка отменена")
    return ConversationHandler.END


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущие настройки"""
    global parser
    if parser is None:
        parser = AvitoParser(use_db=True, use_browser=True)
    
    config = parser.config
    params = config.get('search_params', {})
    
    # Получаем статистику из БД
    stats = parser.get_stats()
    
    status_text = f"""
📊 <b>Текущие настройки:</b>

📦 Товар: {params.get('query', 'Не задано')}
📍 Локация: {params.get('location', 'Не задано')}
📂 Категория: {params.get('category', 'Не задано')}
💰 Цена: {params.get('price_min', '')} - {params.get('price_max', '')}
⏰ Интервал: {config.get('check_interval_minutes', 1)} мин
🔄 Проверка: {'🟢 Активна' if checking else '🔴 Остановлена'}

<b>Статистика:</b>
📈 Всего найдено: {stats.get('total_found', 0)}
🆕 Новых за 24ч: {stats.get('new_today', 0)}
"""
    
    if stats.get('last_found_at'):
        status_text += f"🕐 Последнее: {stats['last_found_at']}"
    
    status_text += "\n\nИспользуй /setup чтобы изменить настройки"
    
    await update.message.reply_text(status_text, parse_mode='HTML')


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверить объявления прямо сейчас"""
    global parser
    if parser is None:
        parser = AvitoParser(notify_callback=send_notification_sync, use_db=True, use_browser=True)
    
    await update.message.reply_text("🔍 Проверяю объявления...")
    
    try:
        new_items = parser.check_new_items()
        if new_items:
            await update.message.reply_text(
                f"✅ Найдено новых объявлений: {len(new_items)}"
            )
        else:
            await update.message.reply_text("ℹ️ Новых объявлений не найдено")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


def check_loop(context):
    """Цикл проверки объявлений"""
    global parser, checking
    while checking:
        try:
            if parser:
                new_items = parser.check_new_items()
                # Уведомления отправляются через callback в очередь
        except Exception as e:
            print(f"Ошибка при проверке: {e}")
        
        if checking:
            interval = parser.config.get('check_interval_minutes', 1) if parser else 1
            time.sleep(interval * 60)


async def process_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Асинхронная обработка уведомлений из очереди"""
    global notification_queue, bot_application
    
    while True:
        try:
            # Получаем элемент из очереди (с таймаутом)
            try:
                item = notification_queue.get(timeout=1)
            except:
                await asyncio.sleep(0.1)
                continue
            
            if bot_application is None:
                continue
            
            chat_id = bot_application.bot_data.get('chat_id')
            if not chat_id:
                continue
            
            message = format_item_message(item)
            
            try:
                await bot_application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
            except Exception as e:
                print(f"Ошибка при отправке сообщения: {e}")
                
        except Exception as e:
            print(f"Ошибка в обработке уведомлений: {e}")
            await asyncio.sleep(1)


async def start_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать автоматическую проверку"""
    global parser, checking, check_thread
    
    if checking:
        await update.message.reply_text("⚠️ Проверка уже запущена!")
        return
    
    if parser is None:
        parser = AvitoParser(notify_callback=send_notification_sync, use_db=True, use_browser=True)
    
    # Проверяем, заданы ли параметры
    params = parser.config.get('search_params', {})
    if not params.get('query') and not params.get('location'):
        await update.message.reply_text(
            "❌ Параметры поиска не заданы!\n"
            "Используй /setup чтобы настроить поиск"
        )
        return
    
    checking = True
    context.bot_data['chat_id'] = update.effective_chat.id
    
    # Запускаем поток проверки
    check_thread = threading.Thread(target=check_loop, args=(context,), daemon=True)
    check_thread.start()
    
    interval = parser.config.get('check_interval_minutes', 1)
    await update.message.reply_text(
        f"✅ Проверка запущена!\n"
        f"Интервал: {interval} мин(ы)\n"
        f"Используй /stop_check чтобы остановить"
    )


async def stop_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановить проверку"""
    global checking
    
    if not checking:
        await update.message.reply_text("⚠️ Проверка не запущена!")
        return
    
    checking = False
    await update.message.reply_text("⏹️ Проверка остановлена")


def send_notification_sync(item: Dict):
    """Синхронная функция для отправки уведомления (вызывается из парсера)"""
    # Просто добавляем в очередь, обработка будет в асинхронном потоке
    global notification_queue
    notification_queue.put(item)


def main():
    """Главная функция для запуска бота"""
    global bot_application
    
    # Используем захардкоженный токен
    token = TELEGRAM_BOT_TOKEN
    
    if not token:
        print("❌ Ошибка: Токен бота не задан!")
        return
    
    # Создаем приложение
    print("🔧 Создаю приложение...")
    try:
        application = Application.builder().token(token).build()
        bot_application = application  # Сохраняем для доступа из callback
        print("✅ Приложение создано")
    except Exception as e:
        print(f"❌ Ошибка при создании приложения: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Создаем ConversationHandler для настройки
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('setup', setup)],
        states={
            QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, query_input)],
            LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, location_input),
                CommandHandler('skip', skip)
            ],
            CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, category_input),
                CommandHandler('skip', skip)
            ],
            PRICE_MIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, price_min_input),
                CommandHandler('skip', skip)
            ],
            PRICE_MAX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, price_max_input),
                CommandHandler('skip', skip)
            ],
            INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, interval_input)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('status', status))
    application.add_handler(CommandHandler('check_now', check_now))
    application.add_handler(CommandHandler('start_check', start_check))
    application.add_handler(CommandHandler('stop_check', stop_check))
    
    # Запускаем задачу для обработки уведомлений после старта
    async def post_init(app: Application):
        asyncio.create_task(process_notifications(None))
    
    application.post_init = post_init
    
    # Запускаем бота
    print("="*60)
    print("🤖 БОТ ЗАПУЩЕН!")
    print("="*60)
    print(f"💡 Токен: {token[:20]}...")
    print("💡 Используй /start в Telegram чтобы начать")
    print("="*60)
    print("⏳ Ожидаю команды...")
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES, 
            drop_pending_updates=True,
            close_loop=False
        )
    except KeyboardInterrupt:
        print("\n\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

