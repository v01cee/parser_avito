"""
Интерактивная настройка параметров поиска для парсера Авито
"""
import json
import os
from database import Database
from avito_parser import AvitoParser


def setup_params():
    """Интерактивная настройка параметров поиска"""
    config_path = "config.json"
    
    # Загружаем существующую конфигурацию или создаем новую
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {
            "search_params": {},
            "check_interval_minutes": 1,
            "notify_on_new": True
        }
    
    print("="*60)
    print("НАСТРОЙКА ПАРАМЕТРОВ ПОИСКА НА АВИТО")
    print("="*60)
    print("\nВведите параметры поиска (нажмите Enter чтобы пропустить):\n")
    
    # Запрос поиска
    current_query = config.get('search_params', {}).get('query', '')
    query = input(f"Поисковый запрос [{current_query}]: ").strip()
    if query:
        config.setdefault('search_params', {})['query'] = query
    
    # Локация
    current_location = config.get('search_params', {}).get('location', '')
    print("\nПримеры локаций: moskva, spb, krasnodar, ekaterinburg")
    location = input(f"Локация (город) [{current_location}]: ").strip()
    if location:
        config.setdefault('search_params', {})['location'] = location
    
    # Категория (опционально)
    current_category = config.get('search_params', {}).get('category', '')
    print("\nПримеры категорий: elektronika, transport, nedvizhimost")
    category = input(f"Категория [{current_category}]: ").strip()
    if category:
        config.setdefault('search_params', {})['category'] = category
    
    # Минимальная цена
    current_price_min = config.get('search_params', {}).get('price_min', '')
    price_min = input(f"Минимальная цена [{current_price_min}]: ").strip()
    if price_min:
        config.setdefault('search_params', {})['price_min'] = price_min
    
    # Максимальная цена
    current_price_max = config.get('search_params', {}).get('price_max', '')
    price_max = input(f"Максимальная цена [{current_price_max}]: ").strip()
    if price_max:
        config.setdefault('search_params', {})['price_max'] = price_max
    
    # Интервал проверки
    current_interval = config.get('check_interval_minutes', 1)
    interval = input(f"\nИнтервал проверки в минутах [{current_interval}]: ").strip()
    if interval:
        try:
            config['check_interval_minutes'] = int(interval)
        except ValueError:
            print("Неверное значение, используется значение по умолчанию")
    
    # Уведомления
    current_notify = config.get('notify_on_new', True)
    notify = input(f"Уведомлять о новых объявлениях? (y/n) [{('y' if current_notify else 'n')}]: ").strip().lower()
    if notify in ['y', 'yes', 'да', 'д']:
        config['notify_on_new'] = True
    elif notify in ['n', 'no', 'нет', 'н']:
        config['notify_on_new'] = False
    
    # Сохранение конфигурации
    # Сохраняем в файл (для совместимости)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # Также сохраняем в базу данных
    try:
        db = Database()
        parser = AvitoParser(use_db=True)
        parser.config = config
        parser.save_config()
        print("\n✅ Конфигурация сохранена в базу данных!")
    except Exception as e:
        print(f"\n⚠️ Не удалось сохранить в БД: {e}")
    
    print("\n" + "="*60)
    print("Конфигурация сохранена!")
    print("="*60)
    print("\nТекущие параметры:")
    print(json.dumps(config, ensure_ascii=False, indent=2))
    print("\nТеперь можно запустить парсер командой: python avito_parser.py")
    print("Или запустить Telegram бота: python telegram_bot.py")


if __name__ == "__main__":
    setup_params()

