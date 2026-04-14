import os
import aiohttp
import logging
from dotenv import load_dotenv

load_dotenv()

COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY")

HEADERS = {}
if COINGLASS_API_KEY:
    HEADERS = {
        "accept": "application/json",
        "coinglassSecret": COINGLASS_API_KEY
    }

async def fetch_coinglass_data(symbol: str):
    if not COINGLASS_API_KEY:
        return "📊 Coinglass: API ключ не указан"

    coinglass_symbol = symbol.replace("USDT", "")
    result_lines = []

    # === SPOT VOLUME ===
    spot_url = f"https://open-api.coinglass.com/public/v2/spot_volume_history?symbol={coinglass_symbol}&interval=5m&exchange=bybit"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(spot_url, headers=HEADERS) as resp:
                data = await resp.json()
                history = data.get("data", {}).get("bybit", [])
                if len(history) >= 2:
                    prev_volume = float(history[-2]["v"])
                    latest_volume = float(history[-1]["v"])
                    if prev_volume > 0:
                        change_pct = (latest_volume - prev_volume) / prev_volume * 100
                        result_lines.append(f"📊 Объём (спот): {change_pct:+.1f}%")
                    else:
                        result_lines.append("📊 Объём (спот): недоступен")
                else:
                    result_lines.append("📍 Актив на споте: отсутствует")
    except Exception as e:
        logging.warning(f"[Coinglass] Ошибка получения объёма: {e}")
        result_lines.append("📊 Объём: ошибка")

    # === FUTURES OI ===
    try:
        oi_list_url = f"https://open-api-v4.coinglass.com/api/futures/open-interest/exchange-list?symbol={coinglass_symbol}"
        async with aiohttp.ClientSession() as session:
            async with session.get(oi_list_url, headers=HEADERS) as resp:
                json_data = await resp.json()
                data = json_data.get("data", [])
                for e in data:
                    if e.get("exchange") == "Bybit":
                        oi_pct = e.get("open_interest_change_percent_15m")
                        if oi_pct is not None:
                            result_lines.append(f"🔐 OI (Bybit): {oi_pct:+.1f}%")
                        else:
                            result_lines.append("🔐 OI (Bybit): недоступен")
                        break
                else:
                    result_lines.append("🔐 OI (Bybit): отсутствует")
    except Exception as e:
        logging.warning(f"[Coinglass] Ошибка получения OI: {e}")
        result_lines.append("🔐 OI: ошибка")

    return "\n".join(result_lines)