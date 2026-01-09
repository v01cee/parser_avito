# Docker развертывание

## Быстрый старт

### 1. Сборка и запуск через docker-compose:

```bash
docker-compose up -d --build
```

### 2. Просмотр логов:

```bash
docker-compose logs -f
```

### 3. Остановка:

```bash
docker-compose down
```

### 4. Перезапуск:

```bash
docker-compose restart
```

## Ручная сборка и запуск

### 1. Сборка образа:

```bash
docker build -t avito-parser-bot .
```

### 2. Запуск контейнера:

```bash
docker run -d \
  --name avito_parser_bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/avito_parser.db:/app/avito_parser.db \
  avito-parser-bot
```

### 3. Просмотр логов:

```bash
docker logs -f avito_parser_bot
```

### 4. Остановка:

```bash
docker stop avito_parser_bot
docker rm avito_parser_bot
```

## Структура данных

- `data/` - директория для данных (создается автоматически)
- `avito_parser.db` - база данных SQLite (сохраняется на хосте)

## Переменные окружения

Токен бота захардкожен в коде (`telegram_bot_aiogram.py`).

Если нужно использовать переменные окружения, создай `.env` файл и раскомментируй `env_file` в `docker-compose.yml`.

## Обновление

```bash
# Остановить
docker-compose down

# Обновить код
git pull  # или скопировать новые файлы

# Пересобрать и запустить
docker-compose up -d --build
```

