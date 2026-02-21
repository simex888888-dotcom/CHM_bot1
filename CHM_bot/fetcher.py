"""
Загрузка данных с OKX
"""

import logging
import asyncio
import ssl
import certifi
import aiohttp
import pandas as pd
from typing import Optional

log = logging.getLogger("CHM.Fetcher")

OKX_CANDLES  = "https://www.okx.com/api/v5/market/candles"
OKX_TICKERS  = "https://www.okx.com/api/v5/market/tickers"
OKX_SYMBOLS  = "https://www.okx.com/api/v5/public/instruments"

TIMEFRAME_MAP = {
    "1m":  "1m",  "3m":  "3m",  "5m":  "5m",  "15m": "15m",
    "30m": "30m", "1h":  "1H",  "2h":  "2H",  "4h":  "4H",
    "6h":  "6H",  "12h": "12H", "1d":  "1D",  "1w":  "1W",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Origin": "https://www.okx.com",
    "Referer": "https://www.okx.com/",
}


class BinanceFetcher:

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout   = aiohttp.ClientTimeout(total=30, connect=10)
            ssl_ctx   = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(
                ssl=ssl_ctx,
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=HEADERS,
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_all_usdt_pairs(
        self,
        min_volume_usdt: float = 1_000_000,
        blacklist: list = None,
        max_coins: int = 0,
    ) -> list:
        blacklist = blacklist or []
        log.info("🌐 Загружаю список монет с OKX...")

        try:
            session = await self._get_session()
            await asyncio.sleep(0.5)  # небольшая пауза перед запросом

            async with session.get(OKX_SYMBOLS, params={"instType": "SWAP"}) as resp:
                if resp.status != 200:
                    log.error(f"instruments HTTP {resp.status}")
                    return []
                data = await resp.json()

            all_usdt = {
                s["instId"]
                for s in data["data"]
                if s["instId"].endswith("USDT-SWAP")
                and s["state"] == "live"
                and s["instId"] not in blacklist
            }
            log.info(f"  Найдено: {len(all_usdt)} USDT пар")

            await asyncio.sleep(0.5)

            async with session.get(OKX_TICKERS, params={"instType": "SWAP"}) as resp:
                if resp.status != 200:
                    log.error(f"tickers HTTP {resp.status}")
                    return sorted(all_usdt)
                tdata = await resp.json()

            filtered = []
            for t in tdata["data"]:
                sym = t.get("instId", "")
                if sym not in all_usdt:
                    continue
                try:
                    vol = float(t.get("volCcy24h", 0))
                except Exception:
                    vol = 0
                if vol >= min_volume_usdt:
                    filtered.append((sym, vol))

            filtered.sort(key=lambda x: x[1], reverse=True)
            coins = [sym for sym, _ in filtered]
            if max_coins and max_coins > 0:
                coins = coins[:max_coins]

            log.info(f"  После фильтра объёма: {len(coins)} монет")
            return coins

        except Exception as e:
            log.error(f"Ошибка получения монет: {e}")
            return []

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 300,
        retries: int = 3,
    ) -> Optional[pd.DataFrame]:
        interval   = TIMEFRAME_MAP.get(timeframe, "1H")
        okx_symbol = self._to_okx(symbol)
        params     = {"instId": okx_symbol, "bar": interval, "limit": str(min(limit, 300))}

        for attempt in range(1, retries + 1):
            try:
                session = await self._get_session()
                await asyncio.sleep(0.1)  # небольшая пауза между запросами
                async with session.get(OKX_CANDLES, params=params) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        log.warning(f"{symbol} HTTP {resp.status}: {text[:60]}")
                        return None
                    data = await resp.json()

                rows = data.get("data", [])
                if not rows:
                    return None

                rows = list(reversed(rows))
                df   = pd.DataFrame(rows, columns=["open_time","open","high","low","close","vol","volCcy","volCcyQuote","confirm"])
                df   = df[["open_time","open","high","low","close","volCcyQuote"]].copy()
                df.rename(columns={"volCcyQuote": "volume"}, inplace=True)
                df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
                df["open_time"] = pd.to_datetime(df["open_time"].astype(float), unit="ms")
                df.set_index("open_time", inplace=True)
                df = df.iloc[:-1]
                return df

            except asyncio.TimeoutError:
                log.warning(f"{symbol} таймаут (попытка {attempt}/{retries})")
            except Exception as e:
                log.warning(f"{symbol} ошибка: {e} (попытка {attempt}/{retries})")

            if attempt < retries:
                await asyncio.sleep(2 * attempt)

        return None

    @staticmethod
    def _to_okx(symbol: str) -> str:
        symbol = symbol.replace(" ", "")
        if symbol.endswith("USDT") and "-" not in symbol:
            return f"{symbol[:-4]}-USDT-SWAP"
        return symbol

    async def get_ticker_price(self, symbol: str) -> Optional[float]:
        try:
            session = await self._get_session()
            async with session.get(OKX_TICKERS, params={"instId": self._to_okx(symbol)}) as resp:
                if resp.status == 200:
                    d = await resp.json()
                    return float(d["data"][0]["last"])
        except Exception:
            pass
        return None

    async def get_24h_change(self, symbol: str) -> Optional[dict]:
        try:
            session = await self._get_session()
            async with session.get(OKX_TICKERS, params={"instId": self._to_okx(symbol)}) as resp:
                if resp.status == 200:
                    d    = await resp.json()
                    t    = d["data"][0]
                    last = float(t.get("last", 0))
                    op   = float(t.get("open24h", last))
                    chg  = ((last - op) / op * 100) if op else 0
                    return {
                        "change_pct":  chg,
                        "volume_usdt": float(t.get("volCcy24h", 0)),
                        "high":        float(t.get("highPrice24h", 0) or t.get("high24h", 0)),
                        "low":         float(t.get("lowPrice24h",  0) or t.get("low24h",  0)),
                    }
        except Exception:
            pass
        return None
