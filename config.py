import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# 🔑 Критические переменные
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY")

# 👥 Авторизованные пользователи (указываются через запятую)
_AUTHORIZED_RAW = os.getenv("AUTHORIZED_USERS", "")
AUTHORIZED_USERS = [int(x.strip()) for x in _AUTHORIZED_RAW.split(",") if x.strip()] if _AUTHORIZED_RAW else []

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ Отсутствует TELEGRAM_BOT_TOKEN в файле .env!")