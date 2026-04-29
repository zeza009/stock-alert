import os
import yfinance as yf
import pandas_ta as ta
import requests
import config
from datetime import datetime

LINE_TOKEN   = os.environ["LINE_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]

def send_line(message):
    try:
        requests.post(
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
        print("✅ ส่ง LINE สำเร็จ")
    except Exception as e:
        print(f"❌ LINE error: {e}")

def check_alerts():
    print(f"⏰ เช็คราคา: {datetime.now().strftime('%H:%M:%S')}")
    found_alert = False

    for stock in config.WATCHLIST:
        ticker = stock["ticker"]
        name   = stock["name"]

        try:
            df   = yf.download(ticker, period="3y", interval="1wk", progress=False)
            info = yf.Ticker(ticker).fast_info

            if df is None or len(df) < config.EMA_PERIOD:
                print(f"⚠️ {name}: ข้อมูลไม่พอ")
                continue

            price = float(info.last_price)

            df["EMA100"] = ta.ema(df["Close"], length=config.EMA_PERIOD)
            ema100 = float(df["EMA100"].iloc[-1])

            print(f"{name}: ราคา={price:.2f}, EMA100W={ema100:.2f}")

            # แจ้งเตือนเมื่อราคาแตะหรือต่ำกว่า EMA 100 Weekly
            if price <= ema100:
                msg  = f"🔔 {name} ({ticker})\n"
                msg += "─" * 22 + "\n"
                msg += f"📉 ราคา {price:.2f} แตะ EMA100W ({ema100:.2f})\n"
                msg += f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                send_line(msg)
                found_alert = True

        except Exception as e:
            print(f"❌ Error {name}: {e}")

    if not found_alert:
        print("✓ ไม่มีหุ้นเข้าเงื่อนไข")

check_alerts()
