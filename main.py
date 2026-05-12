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
ALERT_FILE   = "/tmp/alerted.json"

def load_alerted():
    try:
        with open(ALERT_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_alerted(data):
    with open(ALERT_FILE, "w") as f:
        json.dump(data, f)

def today_str():
    return datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%Y-%m-%d')

def now_thai():
    return datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%d/%m/%Y %H:%M')

def is_market_open():
    now     = datetime.now(ZoneInfo("Asia/Bangkok"))
    hour    = now.hour
    minute  = now.minute
    weekday = now.weekday()

    if weekday > 4:
        return False

    if MODE == "stocks":
        if hour == 21 and minute >= 30: return True
        if hour >= 22 or hour < 4:      return True
        return False

    elif MODE == "gold":
        if hour == 5: return False
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

def get_insight_stocks(price, ema_short, ema_long, name):
    below_short = price < ema_short
    below_long  = price < ema_long
    gap_pct     = round((ema_long - price) / ema_long * 100, 1)
    death_cross = ema_short < ema_long

    lines  = []
    emoji  = "🟡"

    if below_long:
        emoji = "🔴"
        lines.append(f"• หลุดทั้ง EMA100W และ EMA200W")
        lines.append(f"• แนวโน้มขาลงระยะยาว ⚠️ ระวังมาก")
        if gap_pct > 10:
            lines.append(f"• ต่ำกว่า EMA200W ถึง {gap_pct}% อาจ Oversold")
        if death_cross:
            lines.append(f"• Death Cross เกิดขึ้นแล้ว สัญญาณขาลงแรง")
        lines.append(f"• แนวรับถัดไปดูที่กราฟรายสัปดาห์")

    elif below_short:
        emoji = "🟡"
        lines.append(f"• หลุด EMA100W แต่ยังอยู่เหนือ EMA200W")
        lines.append(f"• แนวโน้มอ่อนแอระยะกลาง ยังไม่วิกฤต")
        lines.append(f"• EMA200W ที่ {ema_long:.2f} คือแนวรับถัดไป")

    return emoji, "\n".join(lines)

def get_insight_gold(price, ema_short, ema_long):
    below_short = price < ema_short
    below_long  = price < ema_long
    gap_pct     = round((ema_long - price) / ema_long * 100, 1)
    death_cross = ema_short < ema_long

    lines = []
    emoji = "🟡"

    if below_long:
        emoji = "🔴"
        lines.append(f"• หลุดทั้ง EMA100D และ EMA200D")
        lines.append(f"• แนวโน้มทองขาลงระยะยาว ⚠️")
        if gap_pct > 5:
            lines.append(f"• ต่ำกว่า EMA200D ถึง {gap_pct}% Oversold มาก")
        if death_cross:
            lines.append(f"• Death Cross เกิดขึ้นแล้ว สัญญาณแรง")
        lines.append(f"• แนวรับถัดไปดูที่ EMA200D บวก Fibonacci")

    elif below_short:
        emoji = "🟡"
        lines.append(f"• หลุด EMA100D แต่ยังอยู่เหนือ EMA200D")
        lines.append(f"• แนวโน้มอ่อนแอระยะกลาง")
        lines.append(f"• EMA200D ที่ {ema_long:.2f} คือแนวรับถัดไป")

    return emoji, "\n".join(lines)

def check_us_stocks(watchlist):
    print(f"⏰ เช็คหุ้น US: {now_thai()}")

    if not is_market_open():
        print("🔴 ตลาด US ปิดอยู่")
        return

    alerted = load_alerted()
    today   = today_str()
    if alerted.get("date") != today:
        alerted = {"date": today}

    for stock in watchlist:
        ticker    = stock["ticker"]
        name      = stock["name"]
        small_cap = stock.get("small_cap", False)

        if ticker in alerted:
            print(f"⏭️ {name}: แจ้งไปแล้ววันนี้")
            continue

        try:
            tk   = yf.Ticker(ticker)
            df   = tk.history(period="5y", interval="1wk")
            info = tk.fast_info

            if df is None or len(df) < config.EMA_LONG:
                print(f"⚠️ {name}: ข้อมูลไม่พอ")
                continue

            price = float(info.last_price)

            # small cap ใช้ EMA 50W แทน EMA 100W
            short_period = config.EMA_SMALL if small_cap else config.EMA_SHORT

            df["EMA_SHORT"] = ta.trend.ema_indicator(df["Close"], window=short_period)
            df["EMA_LONG"]  = ta.trend.ema_indicator(df["Close"], window=config.EMA_LONG)

            ema_short = float(df["EMA_SHORT"].iloc[-1])
            ema_long  = float(df["EMA_LONG"].iloc[-1])

            short_label = f"EMA{short_period}W"
            long_label  = "EMA200W"

            print(f"{name}: ราคา={price:.2f}, {short_label}={ema_short:.2f}, {long_label}={ema_long:.2f}")

            if price <= ema_short:
                emoji, insight = get_insight_stocks(price, ema_short, ema_long, name)
                msg  = f"{emoji} {name} ({ticker})\n"
                msg += "─" * 22 + "\n"
                if price < ema_short:
                    msg += f"📉 ราคา {price:.2f} ต่ำกว่า {short_label} ({ema_short:.2f})\n"
                if price < ema_long:
                    msg += f"📉 ราคา {price:.2f} ต่ำกว่า {long_label} ({ema_long:.2f})\n"
                msg += f"\n💡 Insight:\n{insight}\n"
                msg += f"\n⏰ {now_thai()} (เวลาไทย)"
                send_line(msg)
                alerted[ticker] = True

        except Exception as e:
            print(f"❌ Error {name}: {e}")

    save_alerted(alerted)

def check_gold(watchlist):
    print(f"⏰ เช็คทอง: {now_thai()}")

    if not is_market_open():
        print("🔴 ตลาดทองปิดอยู่")
        return

    alerted = load_alerted()
    today   = today_str()
    if alerted.get("date") != today:
        alerted = {"date": today}

    for stock in watchlist:
        ticker = stock["ticker"]
        name   = stock["name"]

        if ticker in alerted:
            print(f"⏭️ {name}: แจ้งไปแล้ววันนี้")
            continue

        try:
            tk   = yf.Ticker(ticker)
            df   = tk.history(period="3y", interval="1d")  # Daily สำหรับทอง
            info = tk.fast_info

            if df is None or len(df) < config.EMA_LONG:
                print(f"⚠️ {name}: ข้อมูลไม่พอ")
                continue

            price = float(info.last_price)

            df["EMA_SHORT"] = ta.trend.ema_indicator(df["Close"], window=config.EMA_SHORT)
            df["EMA_LONG"]  = ta.trend.ema_indicator(df["Close"], window=config.EMA_LONG)

            ema_short = float(df["EMA_SHORT"].iloc[-1])
            ema_long  = float(df["EMA_LONG"].iloc[-1])

            print(f"{name}: ราคา={price:.2f}, EMA100D={ema_short:.2f}, EMA200D={ema_long:.2f}")

            if price <= ema_short:
                emoji, insight = get_insight_gold(price, ema_short, ema_long)
                msg  = f"{emoji} {name}\n"
                msg += "─" * 22 + "\n"
                if price < ema_short:
                    msg += f"📉 ราคา {price:.2f} ต่ำกว่า EMA100D ({ema_short:.2f})\n"
                if price < ema_long:
                    msg += f"📉 ราคา {price:.2f} ต่ำกว่า EMA200D ({ema_long:.2f})\n"
                msg += f"\n💡 Insight:\n{insight}\n"
                msg += f"\n⏰ {now_thai()} (เวลาไทย)"
                send_line(msg)
                alerted[ticker] = True

        except Exception as e:
            print(f"❌ Error {name}: {e}")

    save_alerted(alerted)

if MODE == "gold":
    check_gold(config.GOLD)
else:
    check_us_stocks(config.US_STOCKS)
