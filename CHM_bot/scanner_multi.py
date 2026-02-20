"""
Мульти-пользовательский сканер с SMC анализом
"""

import asyncio
import logging
import time
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from config import Config
from user_manager import UserManager, UserSettings
from fetcher import BinanceFetcher
from indicator import CHMIndicator, SignalResult
from smc import SMCAnalyzer, SMCResult

log = logging.getLogger("CHM.MultiScanner")


def make_signal_text(sig: SignalResult, user: UserSettings, smc: SMCResult, change_24h=None) -> str:
    stars  = "⭐" * sig.quality + "☆" * (5 - sig.quality)
    header = "🟢 <b>LONG СИГНАЛ</b>" if sig.direction == "LONG" else "🔴 <b>SHORT СИГНАЛ</b>"
    emoji  = "📈" if sig.direction == "LONG" else "📉"

    risk = abs(sig.entry - sig.sl)
    tp1  = sig.entry + risk * user.tp1_rr if sig.direction == "LONG" else sig.entry - risk * user.tp1_rr
    tp2  = sig.entry + risk * user.tp2_rr if sig.direction == "LONG" else sig.entry - risk * user.tp2_rr
    tp3  = sig.entry + risk * user.tp3_rr if sig.direction == "LONG" else sig.entry - risk * user.tp3_rr

    def pct(t): return abs((t - sig.entry) / sig.entry * 100)

    lines = [
        header,
        "",
        f"💎 <b>{sig.symbol}</b>  {emoji}  {sig.breakout_type}",
        f"⭐ CHM качество: {stars}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        f"💰 Вход:    <code>{sig.entry:.6g}</code>",
        f"🛑 Стоп:    <code>{sig.sl:.6g}</code>  <i>(-{sig.risk_pct:.2f}%)</i>",
        "",
        f"🎯 Цель 1:  <code>{tp1:.6g}</code>  <i>(+{pct(tp1):.2f}%)</i>",
        f"🎯 Цель 2:  <code>{tp2:.6g}</code>  <i>(+{pct(tp2):.2f}%)</i>",
        f"🏆 Цель 3:  <code>{tp3:.6g}</code>  <i>(+{pct(tp3):.2f}%)</i>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📊 {sig.trend_local}  |  RSI: <code>{sig.rsi:.1f}</code>  |  Vol: <code>x{sig.volume_ratio:.1f}</code>",
        f"🕯 Паттерн: {sig.pattern}",
    ]

    # SMC блок
    if user.use_smc and smc:
        smc_score = smc.smc_long_score if sig.direction == "LONG" else smc.smc_short_score
        smc_stars = "🔵" * smc_score + "⚪" * (4 - smc_score)
        lines += [
            "",
            f"━━━━ 🧠 SMART MONEY ━━━━",
            f"SMC сила: {smc_stars}  ({smc_score}/4)",
        ]
        if smc.price_in_bull_ob and sig.direction == "LONG":
            lines.append("📦 Цена в бычьем Order Block")
        if smc.price_in_bear_ob and sig.direction == "SHORT":
            lines.append("📦 Цена в медвежьем Order Block")
        if smc.price_in_bull_fvg and sig.direction == "LONG":
            lines.append("⚡ Цена в бычьем FVG (имбаланс)")
        if smc.price_in_bear_fvg and sig.direction == "SHORT":
            lines.append("⚡ Цена в медвежьем FVG")
        if smc.recent_sell_sweep and sig.direction == "LONG":
            lines.append("💧 Sweep лоёв — сбор стопов продавцов")
        if smc.recent_buy_sweep and sig.direction == "SHORT":
            lines.append("💧 Sweep хаёв — сбор стопов покупателей")
        if smc.bos_direction == "bull" and sig.direction == "LONG":
            lines.append("📈 BOS — бычий слом структуры")
        if smc.bos_direction == "bear" and sig.direction == "SHORT":
            lines.append("📉 BOS — медвежий слом структуры")
        if smc_score == 0:
            lines.append("⚪ SMC нейтральный")

    if change_24h:
        ch = change_24h["change_pct"]
        em = "🔺" if ch > 0 else "🔻"
        lines += ["", f"📅 24h: {em} {ch:+.2f}%  |  Vol: ${change_24h['volume_usdt']:,.0f}"]

    lines += ["", "⚡ <i>CHM Laboratory — CHM BREAKER + SMC</i>"]
    return "\n".join(lines)


class UserScanner:
    def __init__(self, user_id: int):
        self.user_id   = user_id
        self.last_scan = 0.0
        self.last_signals: dict[str, int] = {}


class MultiScanner:

    def __init__(self, config: Config, bot: Bot, um: UserManager):
        self.config      = config
        self.bot         = bot
        self.um          = um
        self.fetcher     = BinanceFetcher()
        self.smc         = SMCAnalyzer()

        self._candle_cache:     dict[str, tuple] = {}
        self._htf_cache:        dict[str, tuple] = {}
        self._coins_cache:      list             = []
        self._coins_loaded_at:  float            = 0.0
        self._user_scanners:    dict[int, UserScanner] = {}
        self._indicators:       dict[int, CHMIndicator] = {}

    def _get_user_scanner(self, uid: int) -> UserScanner:
        if uid not in self._user_scanners:
            self._user_scanners[uid] = UserScanner(uid)
        return self._user_scanners[uid]

    def _get_indicator(self, user: UserSettings) -> CHMIndicator:
        cfg = self.config
        cfg.USE_RSI_FILTER     = user.use_rsi
        cfg.USE_VOLUME_FILTER  = user.use_volume
        cfg.USE_PATTERN_FILTER = user.use_pattern
        cfg.USE_HTF_FILTER     = user.use_htf
        cfg.ATR_MULT           = user.atr_mult
        cfg.MAX_RISK_PCT       = user.max_risk_pct
        cfg.TP1_RR             = user.tp1_rr
        cfg.TP2_RR             = user.tp2_rr
        cfg.TP3_RR             = user.tp3_rr
        if user.user_id not in self._indicators:
            self._indicators[user.user_id] = CHMIndicator(cfg)
        return self._indicators[user.user_id]

    async def _load_coins(self, min_vol: float) -> list:
        now = time.time()
        if self._coins_cache and (now - self._coins_loaded_at) < 3600 * 6:
            return self._coins_cache
        coins = await self.fetcher.get_all_usdt_pairs(
            min_volume_usdt=min_vol,
            blacklist=self.config.AUTO_BLACKLIST,
        )
        if not coins:
            coins = self.config.COINS
        self._coins_cache     = coins
        self._coins_loaded_at = now
        return coins

    async def _get_candles(self, symbol: str, timeframe: str):
        key = f"{symbol}_{timeframe}"
        now = time.time()
        cached = self._candle_cache.get(key)
        if cached and (now - cached[1]) < 60:
            return cached[0]
        df = await self.fetcher.get_candles(symbol, timeframe, limit=300)
        if df is not None:
            self._candle_cache[key] = (df, now)
        return df

    async def _get_htf(self, symbol: str):
        key = f"{symbol}_htf"
        now = time.time()
        cached = self._htf_cache.get(key)
        if cached and (now - cached[1]) < 3600:
            return cached[0]
        df = await self.fetcher.get_candles(symbol, self.config.HTF_TIMEFRAME, limit=100)
        if df is not None:
            self._htf_cache[key] = (df, now)
        return df

    async def _send_signal(self, user: UserSettings, sig: SignalResult, smc: SMCResult):
        change_24h = await self.fetcher.get_24h_change(sig.symbol)
        text = make_signal_text(sig, user, smc, change_24h)
        try:
            await self.bot.send_message(user.user_id, text, parse_mode="HTML")
            user.signals_received += 1
            self.um.save_user(user)
            log.info(f"✅ → {user.username or user.user_id}: {sig.symbol} {sig.direction} ⭐{sig.quality}")
        except TelegramForbiddenError:
            log.warning(f"Пользователь {user.user_id} заблокировал бота")
            user.active = False
            self.um.save_user(user)
        except Exception as e:
            log.error(f"Ошибка отправки {user.user_id}: {e}")

    async def _scan_for_user(self, user: UserSettings, coins: list) -> int:
        us        = self._get_user_scanner(user.user_id)
        indicator = self._get_indicator(user)
        signals   = 0

        for i in range(0, len(coins), self.config.CHUNK_SIZE):
            chunk = coins[i: i + self.config.CHUNK_SIZE]
            dfs   = await asyncio.gather(*[self._get_candles(s, user.timeframe) for s in chunk])

            for symbol, df in zip(chunk, dfs):
                if df is None or len(df) < 100:
                    continue

                df_htf = await self._get_htf(symbol) if user.use_htf else None

                try:
                    sig = indicator.analyze(symbol, df, df_htf)
                except Exception:
                    continue

                if sig is None or sig.quality < user.min_quality:
                    continue

                bar_now = len(df)
                if bar_now - us.last_signals.get(symbol, -999) < self.config.COOLDOWN_BARS:
                    continue

                # SMC анализ
                smc_result = SMCResult()
                if user.use_smc:
                    try:
                        smc_result = self.smc.analyze(df)
                        smc_score  = smc_result.smc_long_score if sig.direction == "LONG" \
                            else smc_result.smc_short_score

                        # Применяем фильтры SMC
                        if user.use_ob and not (
                            (sig.direction == "LONG"  and smc_result.price_in_bull_ob) or
                            (sig.direction == "SHORT" and smc_result.price_in_bear_ob)
                        ):
                            pass  # OB не совпал — не блокируем, просто учитываем в score

                        if user.min_smc_score > 0 and smc_score < user.min_smc_score:
                            continue  # недостаточно SMC подтверждений

                    except Exception as e:
                        log.debug(f"SMC ошибка {symbol}: {e}")

                us.last_signals[symbol] = bar_now

                if user.notify_signal:
                    await self._send_signal(user, sig, smc_result)
                signals += 1

            await asyncio.sleep(0.2)

        return signals

    async def scan_all_users(self):
        active = self.um.get_active_users()
        if not active:
            return

        now = time.time()
        for user in active:
            us = self._get_user_scanner(user.user_id)
            if now - us.last_scan < user.scan_interval:
                continue

            us.last_scan = now
            log.info(f"🔍 Скан для {user.username or user.user_id} (TF={user.timeframe}, SMC={'вкл' if user.use_smc else 'выкл'})")
            coins   = await self._load_coins(user.min_volume_usdt)
            signals = await self._scan_for_user(user, coins)
            log.info(f"  → {signals} сигналов")

    async def run_forever(self):
        log.info("🔄 Мульти-сканер + SMC запущен")
        while True:
            try:
                await self.scan_all_users()
            except Exception as e:
                log.error(f"Ошибка: {e}")
            await asyncio.sleep(30)
