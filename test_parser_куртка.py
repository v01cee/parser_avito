"""
Тест парсера - ищет куртку и показывает процесс
"""
from avito_parser import AvitoParser
from database import Database
import time

print("="*60)
print("🧪 ТЕСТ ПАРСЕРА - ПОИСК КУРТКИ")
print("="*60)

# Создаем БД и парсер
print("\n1️⃣ Инициализация...")
db = Database()
parser = AvitoParser(use_db=True, use_browser=True)

# Хардкод название товара
parser.config['search_params']['query'] = "куртка"
parser.save_config()

print(f"✅ Настройка: ищу '{parser.config['search_params']['query']}'")
print("\n2️⃣ Запускаю браузер (HEADLESS=False - ты увидишь окно)...")

# Включаем видимый браузер для теста (создаем новый с headless=False)
from avito_browser_parser import AvitoBrowserParser
parser.browser_parser = AvitoBrowserParser(headless=False)

print("\n" + "="*60)
print("🔍 НАЧИНАЮ ПРОВЕРКУ...")
print("="*60)
print("⏳ Жди, браузер откроется и начнет работу...")
print("="*60 + "\n")

try:
    result = parser.check_new_items()
    
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТ:")
    print("="*60)
    
    if result:
        for item in result:
            print(f"\n✅ НАЙДЕНО ОБЪЯВЛЕНИЕ:")
            print(f"   Заголовок: {item.get('title', 'N/A')}")
            print(f"   Цена: {item.get('price', 'N/A')}")
            print(f"   Описание: {item.get('description', 'N/A')[:100]}...")
            print(f"   Ссылка: {item.get('link', 'N/A')}")
            print(f"   Время: {item.get('found_at', 'N/A')}")
    else:
        print("❌ Ничего не найдено или ошибка")
        
except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✅ ТЕСТ ЗАВЕРШЕН")
print("="*60)
print("\n💡 Браузер закроется через 5 секунд...")
time.sleep(5)

# Закрываем браузер
if parser.browser_parser and parser.browser_parser.driver:
    parser.browser_parser.close_driver()
    print("✅ Браузер закрыт")

