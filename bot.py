import asyncio
import logging
import os
import json
from datetime import datetime, timedelta

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from config import TELEGRAM_BOT_TOKEN, AUTHORIZED_USERS

# Автоматическое создание служебных папок
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)

USER_DATA_FILE = "data/users.json"
stop_event = asyncio.Event()
user_settings = {}
user_states = {}
previous_alerts = {}
should_pause_bybit = False

def load_user_settings():
    global user_settings
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                user_settings = json.load(f)
            for uid, settings in user_settings.items():
                if "joined_at" in settings:
                    settings["joined_at"] = datetime.fromisoformat(settings["joined_at"])
            user_settings = {int(uid): s for uid, s in user_settings.items()}
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить user_settings: {e}")
            user_settings = {}

def save_user_settings():
    try:
        data_to_save = {}
        for uid, settings in user_settings.items():
            data_to_save[str(uid)] = settings.copy()
            if "joined_at" in data_to_save[str(uid)]:
                data_to_save[str(uid)]["joined_at"] = data_to_save[str(uid)]["joined_at"].isoformat()
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"⚠️ Не удалось сохранить user_settings: {e}")

async def fetch_symbols():
    global should_pause_bybit
    url = "https://api.bybit.com/v5/market/instruments-info?category=linear"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if "x-ratelimit-remaining" in resp.headers:
                    remaining = int(resp.headers["x-ratelimit-remaining"])
                    should_pause_bybit = remaining < 10
                    if should_pause_bybit:
                        logger.warning(f"⚠️ Bybit API почти исчерпан ({remaining}). Пауза 5 сек.")
                data = await resp.json()
                return [
                    item["symbol"]
                    for item in data.get("result", {}).get("list", [])
                    if item.get("symbol", "").endswith("USDT")
                ]
    except Exception as e:
        logger.error(f"Ошибка получения списка пар: {e}")
        return []

async def fetch_candles(symbol: str, interval: int = 1, limit: int = 5):
    global should_pause_bybit
    if should_pause_bybit:
        logger.info(f"⏸ Пауза перед запросом свечей для {symbol}")
        await asyncio.sleep(5)

    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": str(interval),
        "limit": str(limit),
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if "x-ratelimit-remaining" in resp.headers:
                    remaining = int(resp.headers["x-ratelimit-remaining"])
                    should_pause_bybit = remaining < 10
                    if should_pause_bybit:
                        logger.warning(f"⚠️ Bybit API почти исчерпан ({remaining}). Пауза 5 сек.")
                data = await resp.json()
                return data.get("result", {}).get("list", [])
    except Exception as e:
        logger.error(f"Ошибка получения свечей для {symbol}: {e}")
        return []

async def monitor_futures():
    logger.info("📡 Цикл мониторинга начался.")
    semaphore = asyncio.Semaphore(10)

    while not stop_event.is_set():
        active_users = [uid for uid, s in user_settings.items() if s.get("active")]
        logger.info(f"▶️ Активные пользователи: {active_users}")

        if not active_users:
            await asyncio.sleep(10)
            continue

        symbols = await fetch_symbols()
        logger.info(f"🔍 Получено пар: {len(symbols)}")

        if not symbols:
            await asyncio.sleep(30)
            continue

        now = datetime.utcnow()

        for user_id in active_users:
            settings = user_settings[user_id]
            percent_threshold = settings.get("percent", 5.0)
            interval = settings.get("interval", 300)
            timeframe = 1
            candles_needed = max(2, interval // 60)

            async def process_symbol(symbol):
                async with semaphore:
                    if not user_settings.get(user_id, {}).get("active"):
                        return

                    candles = await fetch_candles(symbol, interval=timeframe, limit=candles_needed)
                    if len(candles) < 2:
                        return

                    try:
                        first_low = float(candles[0][3])
                        first_high = float(candles[0][2])
                        last_low = float(candles[-1][3])
                        last_high = float(candles[-1][2])

                        pump_change = ((last_high - first_low) / first_low) * 100
                        dump_change = ((last_low - first_high) / first_high) * 100

                        direction = None
                        percent_change = None

                        if pump_change >= percent_threshold:
                            direction = "📉 ДАМП"
                            percent_change = abs(pump_change)
                        elif dump_change <= -percent_threshold:
                            direction = "📈 ПАМП"
                            percent_change = abs(dump_change)
                        else:
                            return

                        key = f"{user_id}:{symbol}"
                        last_alert_time = previous_alerts.get(key)
                        if last_alert_time and now - last_alert_time < timedelta(minutes=15):
                            return

                        previous_alerts[key] = now

                        timestamp = int(candles[-1][0]) // 1000
                        dt = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S UTC")

                        text = (
                            f"Обнаружен {direction} `{symbol}`\n"
                            f"Bybit: [ссылка](https://www.bybit.com/trade/usdt/{symbol})\n"
                            f"Изменение: {percent_change:.2f}%\n"
                            f"Период: ~{interval} сек.\n"
                            f"Время: {dt}"
                        )

                        stop_button = InlineKeyboardMarkup().add(
                            InlineKeyboardButton("⏹ Остановить", callback_data="stop")
                        )
                        await bot.send_message(
                            user_id,
                            text,
                            reply_markup=stop_button,
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )
                    except Exception as e:
                        logger.error(f"❌ Ошибка обработки {symbol}: {e}")

            tasks = [process_symbol(symbol) for symbol in symbols]
            await asyncio.gather(*tasks)

        await asyncio.sleep(60)

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "без_ника"

    if user_id not in user_settings:
        user_settings[user_id] = {
            "percent": 5.0,
            "interval": 300,
            "active": False,
            "joined_at": datetime.utcnow(),
            "username": username
        }
        save_user_settings()

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("▶️ Старт", callback_data="start"))
    keyboard.add(
        InlineKeyboardButton("📊 Изменить %", callback_data="set_percent"),
        InlineKeyboardButton("⏱ Изменить интервал", callback_data="set_interval")
    )
    keyboard.add(InlineKeyboardButton("⏹ Стоп", callback_data="stop"))

    await message.reply("👋 Добро пожаловать! Используй кнопки:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data in ["start", "stop"])
async def toggle_monitoring(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_settings:
        return await callback.answer("❌ Неизвестный пользователь.")

    if callback.data == "start":
        user_settings[user_id]["active"] = True
        await callback.message.answer("✅ Мониторинг запущен.")
    else:
        user_settings[user_id]["active"] = False
        await callback.message.answer("⏹ Мониторинг остановлен.")

        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(InlineKeyboardButton("▶️ Старт", callback_data="start"))
        keyboard.add(
            InlineKeyboardButton("📊 Изменить %", callback_data="set_percent"),
            InlineKeyboardButton("⏱ Изменить интервал", callback_data="set_interval")
        )
        keyboard.add(InlineKeyboardButton("⏹ Стоп", callback_data="stop"))
        await callback.message.answer("📋 Меню управления:", reply_markup=keyboard)

    save_user_settings()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data in ["set_percent", "set_interval"])
async def handle_settings_change(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    key = "percent" if callback.data == "set_percent" else "interval"
    user_states[user_id] = key
    msg = "Введи новый % порог: " if key == "percent" else "Введи интервал (в секундах): "
    await callback.message.answer(msg)
    await callback.answer()

@dp.message_handler()
async def user_input(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return

    key = user_states.pop(user_id)
    try:
        value = float(message.text.strip())

        if key == "percent":
            if not 0.5 <= value <= 100:
                return await message.reply("❌ Порог должен быть от 0.5% до 100%.")
            if user_settings[user_id].get("interval", 60) >= 3200 and value < 15:
                return await message.reply("❌ При интервале >= 3200 сек, минимум 15%.")
            user_settings[user_id]["percent"] = value
            await message.reply(f"✅ Установлен порог: {value:.2f}%")

        elif key == "interval":
            if not 60 <= value <= 3200:
                return await message.reply("❌ Интервал должен быть от 60 до 3200 сек.")
            user_settings[user_id]["interval"] = int(value)
            await message.reply(f"✅ Установлен интервал: {int(value)} сек.")

        save_user_settings()

    except ValueError:
        await message.reply("❌ Введите корректное число.")

async def on_startup(dp):
    load_user_settings()
    asyncio.create_task(monitor_futures())

if __name__ == "__main__":
    logger.info("📡 Запуск бота...")
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)