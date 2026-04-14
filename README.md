# 📊 Crypto Pump/Dump Monitor Bot

Telegram-бот для отслеживания резких изменений цены (пампы/дампы) на фьючерсах Bybit в реальном времени.

## ✨ Функции
- 🔍 Автоматический скан всех USDT-пар на Bybit
- 📉 Детекция пампов и дампов по настраиваемому % порогу
- ⏱ Гибкий интервал проверки (60–3200 сек)
- 🚀 Асинхронная работа без блокировок
- 💾 Сохранение настроек пользователей между перезапусками
- 🛡 Защита от спама (уведомление не чаще 1 раза в 15 мин)

## 🛠 Технологический стек
- `Python 3.8+`
- `aiogram 2.x` (Telegram Bot API)
- `aiohttp` (асинхронные запросы)
- `python-dotenv` (безопасное хранение конфигурации)

## 🚀 Установка и запуск
1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/ВАШ_НИК/crypto-signal-bot.git
   cd crypto-signal-bot

## 🐳 Запуск через Docker (рекомендуется)

### Требования
- Установленный [Docker](https://docs.docker.com/get-docker/)
- Установленный [Docker Compose](https://docs.docker.com/compose/install/) (опционально)

### Быстрый старт
```bash
# 1. Клонируйте репозиторий
git clone https://github.com/bochito-bochito/crypto-signal-bot.git
cd crypto-signal-bot

# 2. Настройте переменные окружения
cp .env.example .env
# Откройте .env и вставьте TELEGRAM_BOT_TOKEN и AUTHORIZED_USERS

# 3. Запустите через Docker Compose
docker-compose up -d

# 4. Просмотр логов
docker-compose logs -f
