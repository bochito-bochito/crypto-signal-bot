# Используем лёгкий образ Python
FROM python:3.10-slim

# Метаданные
LABEL maintainer="bochito-bochito"
LABEL description="Crypto Pump/Dump Monitor Bot for Telegram"

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем только requirements.txt сначала — для кэширования слоёв
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Создаём папки для данных и логов (чтобы бот не упал при первом запуске)
RUN mkdir -p /app/logs /app/data

# Переменные окружения по умолчанию (можно переопределить при запуске)
ENV PYTHONUNBUFFERED=1
ENV TELEGRAM_BOT_TOKEN=
ENV AUTHORIZED_USERS=
ENV COINGLASS_API_KEY=

# Порт не нужен, но укажем для совместимости с orchestration-инструментами
EXPOSE 8080

# Запускаем бота
CMD ["python", "bot.py"]