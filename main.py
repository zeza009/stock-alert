import os
import ta
import requests
import config
from datetime import datetime
from zoneinfo import ZoneInfo
from tvDatafeed import TvDatafeed, Interval

LINE_TOKEN   = os.environ["LINE_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]
MODE         = os.environ.get("MODE", "stocks")

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

def check_alerts(watchlist):
    print(f"⏰ เช็คราคา ({MODE}): {now_thai()}")

    tv = TvDatafeed()
    found_alert = False

    for stock in watchlist:
        ticker   = stock["ticker"]
        name     = stock["name"]
        exchange = stock.get("exchange", "NASDAQ")

        try:
            df = tv.get_hist(
                symbol=ticker,
                exchange=exchange,
                interval=Interval.in_weekly,
                n_bars=150
            )

            if df is None or len(df) < config.EMA_PERIOD:
                print(f"⚠️ {name}: ข้อมูลไม่พอ")
                continue

            price        = float(df["close"].iloc[-1])
            df["EMA100"] = ta.trend.ema_indicator(df["close"], window=config.EMA_PERIOD)
            ema100       = float(df["EMA100"].iloc[-1])

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
        print("✓ ไม่มีเข้าเงื่อนไข")

if MODE == "gold":
    check_alerts(config.GOLD)
else:
    check_alerts(config.US_STOCKS)
