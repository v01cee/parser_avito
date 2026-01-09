"""
Быстрый тест - просто проверяет одно объявление и отправляет
"""
from avito_parser import AvitoParser
from database import Database

# Создаем парсер с хардкод данными
print("🚀 Быстрый тест парсера")
print("="*60)

# Создаем БД и парсер
db = Database()
parser = AvitoParser(use_db=True, use_browser=True)

# Хардкод название товара для теста
parser.config['search_params']['query'] = "iphone"
parser.save_config()

print(f"📦 Ищу: {parser.config['search_params']['query']}")
print("🔍 Начинаю проверку...")

try:
    result = parser.check_new_items()
    if result:
        print("\n✅ РЕЗУЛЬТАТ:")
        for item in result:
            print(f"  Заголовок: {item.get('title', 'N/A')}")
            print(f"  Цена: {item.get('price', 'N/A')}")
            print(f"  Ссылка: {item.get('link', 'N/A')}")
    else:
        print("❌ Ничего не найдено")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()


