# Развертывание на сервере

## Быстрый старт

### 1. На сервере клонируй репозиторий:

```bash
git clone https://github.com/v01cee/parser_avito.git
cd parser_avito
```

### 2. Создай файл `.env` с токеном:

```bash
cp .env.example .env
nano .env  # или vi .env
```

Добавь в `.env`:
```
TELEGRAM_BOT_TOKEN=твой_токен_здесь
```

### 3. Запусти через docker-compose:

```bash
docker-compose up -d --build
```

### 4. Смотри логи:

```bash
docker-compose logs -f
```

## Или используй скрипт развертывания:

```bash
chmod +x deploy.sh
./deploy.sh
```

## Команды для управления:

```bash
# Просмотр логов
docker-compose logs -f

# Перезапуск
docker-compose restart

# Остановка
docker-compose down

# Статус
docker-compose ps

# Обновление (после git pull)
docker-compose down
docker-compose up -d --build
```

## Структура данных

База данных и данные сохраняются в:
- `./avito_parser.db` - база данных SQLite
- `./data/` - директория для данных (если нужно)

## Проверка работы

После запуска проверь логи:
```bash
docker-compose logs -f | grep "БОТ ЗАПУЩЕН"
```

Должно появиться:
```
✅ Подключение успешно! Бот: @parser_avittto_bot
⏳ Ожидаю команды...
```

## Требования на сервере

- Docker и docker-compose установлены
- Минимум 2GB RAM
- Интернет соединение для работы с Telegram API и Авито

