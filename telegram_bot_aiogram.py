"""
Telegram бот для управления парсером Авито на Aiogram
"""
import asyncio
import json
from datetime import datetime
from typing import Dict
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from avito_parser import AvitoParser
import threading
import time
from queue import Queue

# Токен бота из переменной окружения
import os
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Состояния для FSM
class SearchStates(StatesGroup):
    query = State()
    # location = State()  # Закомментировано - не нужно
    # category = State()  # Закомментировано - не нужно
    # price_min = State()  # Закомментировано - не нужно
    # price_max = State()  # Закомментировано - не нужно
    interval = State()

# Глобальные переменные
parser = None
checking = False
check_thread = None
notification_queue = Queue()
bot_instance = None
chat_id_storage = None


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


async def start_handler(message: Message):
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
    await message.answer(welcome_text, parse_mode='HTML')


async def setup_handler(message: Message, state: FSMContext):
    """Начать настройку параметров поиска"""
    await message.answer(
        "🔧 <b>Настройка параметров поиска</b>\n\n"
        "Введи название товара (например: iphone, ноутбук):",
        parse_mode='HTML'
    )
    await state.set_state(SearchStates.query)


async def query_input(message: Message, state: FSMContext):
    """Обработка ввода названия товара"""
    query = message.text
    await state.update_data(query=query)
    
    # Интервал по умолчанию 5 минут - чтобы избежать блокировки IP от Авито
    interval = 5
    
    # Сохраняем конфигурацию сразу
    global parser, chat_id_storage
    
    if parser is None:
        parser = AvitoParser(notify_callback=send_notification_sync, use_db=True, use_browser=True)
    
    # Обновляем конфигурацию - только название товара
    parser.config['search_params'] = {
        'query': query,
        'sort': 'date'
    }
    parser.config['check_interval_minutes'] = interval
    parser.save_config()
    
    # Сохраняем chat_id для уведомлений
    chat_id_storage = message.chat.id
    
    await message.answer(
        f"✅ Настройка завершена!\n\n"
        f"📦 Название товара: <b>{query}</b>\n"
        f"⏰ Интервал: {interval} мин\n\n"
        f"💡 <i>Интервал установлен {interval} минут для избежания блокировки IP от Авито</i>\n\n"
        "Используй /start_check чтобы начать проверку или /check_now для разовой проверки.",
        parse_mode='HTML'
    )
    await state.clear()
    
    # Старый код - закомментирован
    # await message.answer(
    #     f"✅ Название товара: <b>{query}</b>\n\n"
    #     "Теперь введи город/локацию (например: moskva, spb, krasnodar):\n"
    #     "Или отправь /skip чтобы пропустить",
    #     parse_mode='HTML'
    # )
    # await state.set_state(SearchStates.location)


# Закомментировано - не нужно для простого поиска
# async def location_input(message: Message, state: FSMContext):
#     """Обработка ввода локации"""
#     location = message.text
#     await state.update_data(location=location)
#     
#     await message.answer(
#         f"✅ Локация: <b>{location}</b>\n\n"
#         "Введи категорию (например: elektronika, transport) или /skip:",
#         parse_mode='HTML'
#     )
#     await state.set_state(SearchStates.category)
# 
# 
# async def category_input(message: Message, state: FSMContext):
#     """Обработка ввода категории"""
#     category = message.text
#     await state.update_data(category=category)
#     
#     await message.answer(
#         f"✅ Категория: <b>{category}</b>\n\n"
#         "Введи минимальную цену (или /skip):",
#         parse_mode='HTML'
#     )
#     await state.set_state(SearchStates.price_min)
# 
# 
# async def price_min_input(message: Message, state: FSMContext):
#     """Обработка ввода минимальной цены"""
#     price_min = message.text
#     await state.update_data(price_min=price_min)
#     
#     await message.answer(
#         f"✅ Минимальная цена: <b>{price_min}</b>\n\n"
#         "Введи максимальную цену (или /skip):",
#         parse_mode='HTML'
#     )
#     await state.set_state(SearchStates.price_max)
# 
# 
# async def price_max_input(message: Message, state: FSMContext):
#     """Обработка ввода максимальной цены"""
#     price_max = message.text
#     await state.update_data(price_max=price_max)
#     
#     await message.answer(
#         f"✅ Максимальная цена: <b>{price_max}</b>\n\n"
#         "Введи интервал проверки в минутах (по умолчанию 1):",
#         parse_mode='HTML'
#     )
#     await state.set_state(SearchStates.interval)


# Закомментировано - интервал по умолчанию 1 минута, не спрашиваем
# async def interval_input(message: Message, state: FSMContext):
#     """Обработка ввода интервала"""
#     global parser, chat_id_storage
#     
#     try:
#         interval = int(message.text)
#     except ValueError:
#         interval = 1
#     
#     data = await state.get_data()
#     
#     # Сохраняем конфигурацию
#     if parser is None:
#         parser = AvitoParser(notify_callback=send_notification_sync, use_db=True, use_browser=True)
#     
#     # Обновляем конфигурацию - только название товара
#     parser.config['search_params'] = {
#         'query': data.get('query', ''),
#         'sort': 'date'
#     }
#     parser.config['check_interval_minutes'] = interval
#     parser.save_config()
#     
#     # Сохраняем chat_id для уведомлений
#     chat_id_storage = message.chat.id
#     
#     config_text = f"""
# ✅ <b>Настройка завершена!</b>
# 
# 📦 Товар: {data.get('query', 'Не указано')}
# ⏰ Интервал: {interval} мин
# 
# Используй /start_check чтобы начать проверку!
# """
#     await message.answer(config_text, parse_mode='HTML')
#     await state.clear()


# Закомментировано - не нужно для простого поиска
# async def skip_handler(message: Message, state: FSMContext):
#     """Пропустить текущий шаг"""
#     current_state = await state.get_state()
#     
#     if current_state == SearchStates.location:
#         await state.update_data(location='')
#         await message.answer(
#             "✅ Локация пропущена\n\n"
#             "Введи категорию (или /skip):",
#             parse_mode='HTML'
#         )
#         await state.set_state(SearchStates.category)
#     elif current_state == SearchStates.category:
#         await state.update_data(category='')
#         await message.answer(
#             "✅ Категория пропущена\n\n"
#             "Введи минимальную цену (или /skip):",
#             parse_mode='HTML'
#         )
#         await state.set_state(SearchStates.price_min)
#     elif current_state == SearchStates.price_min:
#         await state.update_data(price_min='')
#         await message.answer(
#             "✅ Минимальная цена пропущена\n\n"
#             "Введи максимальную цену (или /skip):",
#             parse_mode='HTML'
#         )
#         await state.set_state(SearchStates.price_max)
#     elif current_state == SearchStates.price_max:
#         await state.update_data(price_max='')
#         await message.answer(
#             "✅ Максимальная цена пропущена\n\n"
#             "Введи интервал проверки в минутах:",
#             parse_mode='HTML'
#         )
#         await state.set_state(SearchStates.interval)


async def status_handler(message: Message):
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
⏰ Интервал: {config.get('check_interval_minutes', 1)} мин
🔄 Проверка: {'🟢 Активна' if checking else '🔴 Остановлена'}

<b>Статистика:</b>
📈 Всего найдено: {stats.get('total_found', 0)}
🆕 Новых за 24ч: {stats.get('new_today', 0)}
"""
    
    if stats.get('last_found_at'):
        status_text += f"🕐 Последнее: {stats['last_found_at']}"
    
    status_text += "\n\nИспользуй /setup чтобы изменить настройки"
    
    await message.answer(status_text, parse_mode='HTML')


async def check_now_handler(message: Message):
    """Проверить объявления прямо сейчас"""
    global parser, chat_id_storage, bot_instance
    if parser is None:
        # Создаем парсер БЕЗ callback, отправляем вручную
        parser = AvitoParser(notify_callback=None, use_db=True, use_browser=True)
    
    chat_id_storage = message.chat.id
    bot_instance = message.bot  # Сохраняем бота для использования
    
    await message.answer("🔍 Проверяю объявления...")
    print(f"📱 Chat ID установлен: {chat_id_storage}")
    
    try:
        new_items = parser.check_new_items()
        print(f"📦 Получено объявлений из парсера: {len(new_items) if new_items else 0}")
        
        if new_items:
            # Отправляем найденные объявления сразу в Telegram
            for item in new_items:
                try:
                    print(f"📤 Отправляю объявление: {item.get('title', 'N/A')}")
                    message_text = format_item_message(item)
                    
                    await message.answer(
                        message_text,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                    print(f"✅ Сообщение УСПЕШНО отправлено в Telegram!")
                except Exception as e:
                    print(f"❌ Ошибка при отправке сообщения в Telegram: {e}")
                    import traceback
                    traceback.print_exc()
                    await message.answer(f"❌ Ошибка при отправке: {str(e)}")
            
            await message.answer(
                f"✅ Найдено объявлений: {len(new_items)}"
            )
        else:
            await message.answer("ℹ️ Новых объявлений не найдено")
    except Exception as e:
        print(f"❌ Ошибка в check_now_handler: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(f"❌ Ошибка: {str(e)}")


def check_loop():
    """Цикл проверки объявлений"""
    global parser, checking
    while checking:
        try:
            if parser:
                new_items = parser.check_new_items()
        except Exception as e:
            print(f"Ошибка при проверке: {e}")
        
        if checking:
            interval = parser.config.get('check_interval_minutes', 1) if parser else 1
            time.sleep(interval * 60)


async def start_check_handler(message: Message):
    """Начать автоматическую проверку"""
    global parser, checking, check_thread, chat_id_storage, bot_instance
    
    if checking:
        await message.answer("⚠️ Проверка уже запущена!")
        return
    
    if parser is None:
        # Для автопроверки используем callback через очередь
        parser = AvitoParser(notify_callback=send_notification_sync, use_db=True, use_browser=True)
    
    # Сохраняем бота и chat_id для уведомлений
    bot_instance = message.bot
    chat_id_storage = message.chat.id
    print(f"📱 Chat ID для автопроверки установлен: {chat_id_storage}")
    
    # Проверяем, заданы ли параметры
    params = parser.config.get('search_params', {})
    if not params.get('query'):
        await message.answer(
            "❌ Параметры поиска не заданы!\n"
            "Используй /setup чтобы настроить поиск"
        )
        return
    
    checking = True
    
    # Запускаем поток проверки
    check_thread = threading.Thread(target=check_loop, daemon=True)
    check_thread.start()
    
    interval = parser.config.get('check_interval_minutes', 1)
    await message.answer(
        f"✅ Проверка запущена!\n"
        f"Интервал: {interval} мин(ы)\n"
        f"Используй /stop_check чтобы остановить"
    )


async def stop_check_handler(message: Message):
    """Остановить проверку"""
    global checking
    
    if not checking:
        await message.answer("⚠️ Проверка не запущена!")
        return
    
    checking = False
    await message.answer("⏹️ Проверка остановлена")


def send_notification_sync(item: Dict):
    """Синхронная функция для отправки уведомления (вызывается из парсера)"""
    # Просто добавляем в очередь, обработка будет в асинхронном потоке
    global notification_queue
    print(f"📤 Добавляю объявление в очередь уведомлений: {item.get('title', 'N/A')}")
    notification_queue.put(item)
    print(f"✅ Объявление добавлено в очередь (размер очереди: {notification_queue.qsize()})")


async def process_notifications():
    """Асинхронная обработка уведомлений из очереди"""
    global notification_queue, bot_instance, chat_id_storage
    
    print("🔄 Задача обработки уведомлений запущена")
    
    while True:
        try:
            # Получаем элемент из очереди (с таймаутом)
            try:
                item = notification_queue.get(timeout=1)
                print(f"📨 Получено объявление из очереди: {item.get('title', 'N/A')}")
            except:
                await asyncio.sleep(0.1)
                continue
            
            if bot_instance is None:
                print("⚠️ bot_instance is None, пропускаю уведомление")
                continue
                
            if chat_id_storage is None:
                print("⚠️ chat_id_storage is None, пропускаю уведомление")
                continue
            
            message = format_item_message(item)
            
            try:
                print(f"📤 Отправляю сообщение в Telegram (chat_id: {chat_id_storage})...")
                await bot_instance.send_message(
                    chat_id=chat_id_storage,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                print(f"✅ Сообщение успешно отправлено в Telegram!")
            except Exception as e:
                print(f"❌ Ошибка при отправке сообщения в Telegram: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"❌ Ошибка в обработке уведомлений: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(1)


async def main():
    """Главная функция для запуска бота"""
    global bot_instance
    
    # Используем захардкоженный токен
    token = TELEGRAM_BOT_TOKEN
    
    if not token:
        print("❌ Ошибка: Токен бота не задан!")
        print("💡 Установи переменную окружения TELEGRAM_BOT_TOKEN")
        print("   Например: export TELEGRAM_BOT_TOKEN='твой_токен'")
        return
    
    print(f"🔑 Токен бота: {token[:20]}...")
    print("🚀 Запускаю бота...")
    
    # Создаем бота (стандартный способ)
    bot = Bot(token=token)
    bot_instance = bot
    dp = Dispatcher(storage=MemoryStorage())
    
    print(f"✅ Бот создан")
    
    # Регистрируем обработчики
    dp.message.register(start_handler, Command('start'))
    dp.message.register(setup_handler, Command('setup'))
    dp.message.register(status_handler, Command('status'))
    dp.message.register(check_now_handler, Command('check_now'))
    dp.message.register(start_check_handler, Command('start_check'))
    dp.message.register(stop_check_handler, Command('stop_check'))
    
    # Обработчики для настройки - только название товара (интервал по умолчанию 1 минута)
    dp.message.register(query_input, SearchStates.query)
    # dp.message.register(interval_input, SearchStates.interval)  # Закомментировано - интервал по умолчанию 1 мин
    
    # Закомментировано - не нужно для простого поиска
    # dp.message.register(location_input, SearchStates.location, ~F.text.startswith('/skip'))
    # dp.message.register(skip_handler, SearchStates.location, F.text == '/skip')
    # dp.message.register(category_input, SearchStates.category, ~F.text.startswith('/skip'))
    # dp.message.register(skip_handler, SearchStates.category, F.text == '/skip')
    # dp.message.register(price_min_input, SearchStates.price_min, ~F.text.startswith('/skip'))
    # dp.message.register(skip_handler, SearchStates.price_min, F.text == '/skip')
    # dp.message.register(price_max_input, SearchStates.price_max, ~F.text.startswith('/skip'))
    # dp.message.register(skip_handler, SearchStates.price_max, F.text == '/skip')
    
    # Запускаем задачу для обработки уведомлений
    asyncio.create_task(process_notifications())
    
    # Запускаем бота
    print("="*60)
    print("🤖 БОТ ЗАПУЩЕН НА AIOGRAM!")
    print("="*60)
    print(f"💡 Токен: {token[:20]}...")
    print("💡 Используй /start в Telegram чтобы начать")
    print("="*60)
    print("⏳ Ожидаю команды...")
    print("💡 Проверяю подключение к Telegram API...")
    
    # Проверяем подключение перед запуском polling
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔄 Попытка подключения {attempt + 1}/{max_retries}...")
            me = await bot.get_me()
            print(f"✅ Подключение успешно! Бот: @{me.username}")
            break
        except Exception as e:
            print(f"⚠️ Попытка {attempt + 1} не удалась: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Жду 5 секунд перед следующей попыткой...")
                await asyncio.sleep(5)
            else:
                print("❌ Не удалось подключиться к Telegram API после всех попыток")
                print("💡 Проверь:")
                print("   - Интернет соединение")
                print("   - Файрвол/антивирус не блокирует подключение")
                print("   - Прокси/VPN если используется")
                return
    
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\n\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await bot.session.close()
        except:
            pass
        try:
            await dp.storage.close()
        except:
            pass


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

