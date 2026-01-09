"""
Простой тест для проверки бота
"""
import asyncio
from telegram_bot import main

if __name__ == '__main__':
    print("🚀 Запускаю тест бота...")
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


