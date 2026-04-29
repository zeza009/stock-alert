import os
import yfinance as yf
import ta
import requests
import config
from datetime import datetime
from zoneinfo import ZoneInfo

LINE_TOKEN   = os.environ["LINE_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]

def send_line(message):
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {LINE_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "to": LINE_USER_ID,
                "messages": [{"type": "text", "text": message}]
            }
        )
        print(f"✅ LINE: {r.status_code} {r.text}")
    except Exception as e:
        print(f"❌ LINE error: {e}")

def now_thai():
    return datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%d/%m/%Y %H:%M')

def check_alerts():
    print(f"⏰ เช็คราคา: {now_thai()}")
    found_alert = False

    for stock in config.WATCHLIST:
        ticker = stock["ticker"]
        name   = stock["name"]

        try:
            tk   = yf.Ticker(ticker)
            df   = tk.history(period="3y", interval="1wk")
            info = tk.fast_info

            if df is None or len(df) < config.EMA_PERIOD:
                print(f"⚠️ {name}: ข้อมูลไม่พอ ({len(df)} แท่ง)")
                continue

            price    = float(info.last_price)
            df["EMA100"] = ta.trend.ema_indicator(df["Close"], window=config.EMA_PERIOD)
            ema100   = float(df["EMA100"].iloc[-1])

            print(f"{name}: ราคา={price:.2f}, EMA100W={ema100:.2f}")

            if price <= ema100:
                msg  = f"🔔 {name} ({ticker})\n"
                msg += "─" * 22 + "\n"
                msg += f"📉 ราคา {price:.2f} แตะ EMA100W ({ema100:.2f})\n"
                msg += f"⏰ {now_thai()} (เวลาไทย)"
                send_line(msg)
                found_alert = True

        except Exception as e:
            print(f"❌ Error {name}: {e}")

    if not found_alert:
        print("✓ ไม่มีหุ้นเข้าเงื่อนไข")

check_alerts()
