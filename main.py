import os
import yfinance as yf
import ta
import requests
import config
import json
from datetime import datetime
from zoneinfo import ZoneInfo

LINE_TOKEN   = os.environ["LINE_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]
MODE         = os.environ.get("MODE", "stocks")

ALERT_FILE = "/tmp/alerted.json"

def load_alerted():
    try:
        with open(ALERT_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_alerted(data):
    with open(ALERT_FILE, "w") as f:
        json.dump(data, f)

def is_market_open():
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()  # 0=จันทร์, 4=ศุกร์

    if weekday > 4:  # เสาร์-อาทิตย์
        return False

    if MODE == "stocks":
        # ตลาด US: 21:30 - 04:00 เวลาไทย
        if hour == 21 and minute >= 30:
            return True
        if hour >= 22 or hour < 4:
            return True
        return False

    elif MODE == "gold":
        # ทอง: 06:00 - 05:00 (เกือบตลอด) ยกเว้น 05:00-06:00
        if hour == 5:
            return False
        return True

    return True

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
        print(f"✅ LINE: {r.status_code}")
    except Exception as e:
        print(f"❌ LINE error: {e}")

def now_thai():
    return datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%d/%m/%Y %H:%M')

def today_str():
    return datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%Y-%m-%d')

def check_alerts(watchlist):
    print(f"⏰ เช็คราคา ({MODE}): {now_thai()}")

    # เช็คว่าตลาดเปิดไหม
    if not is_market_open():
        print("🔴 ตลาดปิดอยู่ ไม่เช็คราคา")
        return

    # โหลดรายการที่แจ้งไปแล้ววันนี้
    alerted = load_alerted()
    today   = today_str()

    # รีเซ็ตถ้าวันใหม่
    if alerted.get("date") != today:
        alerted = {"date": today}

    found_alert = False

    for stock in watchlist:
        ticker = stock["ticker"]
        name   = stock["name"]

        # ข้ามถ้าแจ้งไปแล้ววันนี้
        if ticker in alerted:
            print(f"⏭️ {name}: แจ้งไปแล้ววันนี้")
            continue

        try:
            tk   = yf.Ticker(ticker)
            df   = tk.history(period="3y", interval="1wk")
            info = tk.fast_info

            if df is None or len(df) < config.EMA_PERIOD:
                print(f"⚠️ {name}: ข้อมูลไม่พอ")
                continue

            price        = float(info.last_price)
            df["EMA100"] = ta.trend.ema_indicator(df["Close"], window=config.EMA_PERIOD)
            ema100       = float(df["EMA100"].iloc[-1])

            print(f"{name}: ราคา={price:.2f}, EMA100W={ema100:.2f}")

            if price <= ema100:
                msg  = f"🔔 {name} ({ticker})\n"
                msg += "─" * 22 + "\n"
                msg += f"📉 ราคา {price:.2f} แตะ EMA100W ({ema100:.2f})\n"
                msg += f"⏰ {now_thai()} (เวลาไทย)"
                send_line(msg)
                alerted[ticker] = True
                found_alert = True

        except Exception as e:
            print(f"❌ Error {name}: {e}")

    save_alerted(alerted)

    if not found_alert:
        print("✓ ไม่มีเข้าเงื่อนไข")

if MODE == "gold":
    check_alerts(config.GOLD)
else:
    check_alerts(config.US_STOCKS)
