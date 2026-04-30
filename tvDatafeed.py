import enum
import logging
import requests
import pandas as pd
import time

logger = logging.getLogger(__name__)

class Interval(enum.Enum):
    in_1_minute  = "1"
    in_3_minute  = "3"
    in_5_minute  = "5"
    in_15_minute = "15"
    in_30_minute = "30"
    in_45_minute = "45"
    in_1_hour    = "60"
    in_2_hour    = "120"
    in_3_hour    = "180"
    in_4_hour    = "240"
    in_daily     = "1D"
    in_weekly    = "1W"
    in_monthly   = "1M"

class TvDatafeed:
    def __init__(self, username=None, password=None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.tradingview.com"
        })
        # ไม่ login เลย ใช้ token ว่าง
        self.token = "unauthorized_user_token"
        print("✅ No-login mode")

    def get_hist(self, symbol, exchange, interval, n_bars=150):
        interval_val = interval.value if isinstance(interval, Interval) else interval
        end   = int(time.time())
        start = end - (n_bars * 7 * 24 * 3600 * 2)

        url = (
            f"https://history.vn.tradingview.com/history"
            f"?symbol={exchange}%3A{symbol}"
            f"&resolution={interval_val}"
            f"&from={start}"
            f"&to={end}"
            f"&countback={n_bars}"
        )

        try:
            r = self.session.get(url, timeout=10)
            j = r.json()

            if j.get("s") != "ok":
                logger.warning(f"{symbol}: status={j.get('s')}")
                return None

            df = pd.DataFrame({
                "open":   j["o"],
                "high":   j["h"],
                "low":    j["l"],
                "close":  j["c"],
                "volume": j["v"],
            }, index=pd.to_datetime(j["t"], unit="s"))

            df.index.name = "datetime"
            return df

        except Exception as e:
            logger.error(f"get_hist error {symbol}: {e}")
            return None
