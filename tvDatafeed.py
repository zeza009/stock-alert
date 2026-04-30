import enum
import logging
import requests

logger = logging.getLogger(__name__)

class Interval(enum.Enum):
    in_1_minute   = "1"
    in_3_minute   = "3"
    in_5_minute   = "5"
    in_15_minute  = "15"
    in_30_minute  = "30"
    in_45_minute  = "45"
    in_1_hour     = "60"
    in_2_hour     = "120"
    in_3_hour     = "180"
    in_4_hour     = "240"
    in_daily      = "1D"
    in_weekly     = "1W"
    in_monthly    = "1M"

class TvDatafeed:
    signin_url    = "https://www.tradingview.com/accounts/signin/"
    search_url    = "https://symbol-search.tradingview.com/symbol_search/?text={}&hl=1&exchange=&lang=en&type=&domain=production"
    hist_url      = "https://history.vn.tradingview.com/history?symbol={exchange}%3A{symbol}&resolution={interval}&from={start}&to={end}&countback={n_bars}"

    def __init__(self, username=None, password=None):
        self.session  = requests.Session()
        self.username = username
        self.password = password
        self.token    = self.__login() if username else "unauthorized_user_token"

    def __login(self):
        data = {
            "username": self.username,
            "password": self.password,
            "remember": "on"
        }
        headers = {
            "Referer": "https://www.tradingview.com",
            "User-Agent": "Mozilla/5.0"
        }
        try:
            r = self.session.post(self.signin_url, data=data, headers=headers)
            j = r.json()
            if "user" in j:
                token = j["user"]["auth_token"]
                logger.info("Login สำเร็จ")
                return token
            else:
                logger.warning(f"Login ไม่สำเร็จ: {j}")
                return "unauthorized_user_token"
        except Exception as e:
            logger.error(f"Login error: {e}")
            return "unauthorized_user_token"

    def get_hist(self, symbol, exchange, interval, n_bars=150):
        import pandas as pd
        import time

        interval_val = interval.value if isinstance(interval, Interval) else interval
        end   = int(time.time())
        start = end - (n_bars * 7 * 24 * 3600 * 2)

        url = f"https://history.vn.tradingview.com/history?symbol={exchange}%3A{symbol}&resolution={interval_val}&from={start}&to={end}&countback={n_bars}"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Referer": "https://www.tradingview.com",
            "User-Agent": "Mozilla/5.0"
        }

        try:
            r = self.session.get(url, headers=headers)
            j = r.json()

            if j.get("s") != "ok":
                logger.warning(f"{symbol}: {j.get('s')}")
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
