"""
Мульти-пользовательский сканер — использует персональные настройки каждого пользователя
"""

import asyncio
import logging
import time
import numpy as np
import pandas as pd
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from config import Config
from user_manager import UserManager, UserSettings
from fetcher import BinanceFetcher
from smc import SMCAnalyzer, SMCResult

log = logging.getLogger("CHM.Scanner")


# ─────────────────────────────────────────────
#  Встроенный индикатор (работает от UserSettings)
# ─────────────────────────────────────────────

def ema(s, p): return s.ewm(span=p, adjust=False).mean()

def atr(df, p):
    h, l, c = df["high"], df["low"], df["close"].shift(1)
    tr = pd.concat([h-l, (h-c).abs(), (l-c).abs()], axis=1).max(axis=1)
    return tr.ewm(span=p, adjust=False).mean()

def rsi(s, p):
    d = s.diff()
    g = d.clip(lower=0).ewm(span=p, adjust=False).mean()
    ls = (-d.clip(upper=0)).ewm(span=p, adjust=False).mean()
    return 100 - 100/(1 + g/ls.replace(0, np.nan))

def pivot_high(h, strength):
    res = pd.Series(np.nan, index=h.index)
    a = h.values
    for i in range(strength, len(a)-strength):
        if a[i] == max(a[i-strength:i+strength+1]):
            res.iloc[i] = a[i]
    return res

def pivot_low(l, strength):
    res = pd.Series(np.nan, index=l.index)
    a = l.values
    for i in range(strength, len(a)-strength):
        if a[i] == min(a[i-strength:i+strength+1]):
            res.iloc[i] = a[i]
    return res

def detect_pattern(df):
    c = df.iloc[-1]
    p = df.iloc[-2]
    body = abs(c["close"]-c["open"])
    total = c["high"]-c["low"]
    upper = c["high"]-max(c["close"],c["open"])
    lower = min(c["close"],c["open"])-c["low"]
    if total == 0: return "", ""
    bull = ""
    bear = ""
    pb = abs(p["close"]-p["open"])
    if lower >= body*2 and lower >= total*0.5 and c["close"] > c["open"]: bull = "🟢 Пин-бар"
    if upper >= body*2 and upper >= total*0.5 and c["close"] < c["open"]: bear = "🔴 Пин-бар"
    if c["close"]>c["open"] and p["close"]<p["open"] and c["close"]>p["open"] and c["open"]<p["close"] and body>pb: bull = "🟢 Поглощение"
    if c["close"]<c["open"] and p["close"]>p["open"] and c["close"]<p["open"] and c["open"]>p["close"] and body>pb: bear = "🔴 Поглощение"
    if lower >= total*0.6 and upper <= total*0.1: bull = "🟢 Молот"
    if upper >= total*0.6 and lower <= total*0.1: bear = "🔴 Падающая звезда"
    return bull, bear


def analyze(symbol, df, df_htf, user: UserSettings, state: dict) -> dict | None:
    u = user
    if len(df) < u.pivot_strength * 2 + 50:
        return None

    atr_s  = atr(df, u.atr_period)
    ema50  = ema(df["close"], u.ema_fast)
    ema200 = ema(df["close"], u.ema_slow)
    rsi_s  = rsi(df["close"], u.rsi_period)
    avg_vol= df["volume"].rolling(u.vol_len).mean()

    atr_now = atr_s.iloc[-1]
    close   = df["close"].iloc[-1]
    high    = df["high"].iloc[-1]
    low     = df["low"].iloc[-1]
    open_   = df["open"].iloc[-1]
    rsi_now = rsi_s.iloc[-1]
    vol_now = df["volume"].iloc[-1]
    avgv    = avg_vol.iloc[-1]
    vol_ratio = vol_now / avgv if avgv > 0 else 0

    bull_local = close > ema50.iloc[-1] and ema50.iloc[-1] > ema200.iloc[-1]
    bear_local = close < ema50.iloc[-1] and ema50.iloc[-1] < ema200.iloc[-1]
    trend_local = "📈 Бычий" if bull_local else ("📉 Медвежий" if bear_local else "↔️ Боковик")

    htf_bull = htf_bear = True
    trend_htf = "⏸ Выкл"
    if u.use_htf and df_htf is not None and len(df_htf) > u.htf_ema_period:
        htf_ema = ema(df_htf["close"], u.htf_ema_period)
        htf_close = df_htf["close"].iloc[-1]
        htf_bull = htf_close > htf_ema.iloc[-1]
        htf_bear = htf_close < htf_ema.iloc[-1]
        trend_htf = "📈 Бычий" if htf_bull else "📉 Медвежий"

    ph = pivot_high(df["high"], u.pivot_strength)
    pl = pivot_low(df["low"],   u.pivot_strength)
    res_vals = ph.dropna()
    sup_vals = pl.dropna()
    if len(res_vals) == 0 or len(sup_vals) == 0: return None

    bar_idx = len(df) - 1
    res_level = res_vals.iloc[-1]
    sup_level = sup_vals.iloc[-1]
    res_age = bar_idx - df.index.get_loc(res_vals.index[-1])
    sup_age = bar_idx - df.index.get_loc(sup_vals.index[-1])
    res_valid = res_age <= u.max_level_age
    sup_valid = sup_age <= u.max_level_age

    sr_zone = atr_now * u.zone_buffer

    vol_ok = (vol_ratio >= u.vol_mult) if u.use_volume else True
    rsi_long_ok  = (rsi_now < u.rsi_ob) if u.use_rsi else True
    rsi_short_ok = (rsi_now > u.rsi_os) if u.use_rsi else True

    bull_pat, bear_pat = detect_pattern(df)
    pat_long_ok  = bool(bull_pat) if u.use_pattern else True
    pat_short_ok = bool(bear_pat) if u.use_pattern else True

    bull_trend = bull_local and htf_bull
    bear_trend = bear_local and htf_bear

    close_prev = df["close"].iloc[-2]

    if res_valid and close_prev > res_level+sr_zone and close > res_level+sr_zone and bull_trend and not state.get("up"):
        state["up"] = True; state["res"] = res_level; state["up_bar"] = bar_idx
    if sup_valid and close_prev < sup_level-sr_zone and close < sup_level-sr_zone and bear_trend and not state.get("dn"):
        state["dn"] = True; state["sup"] = sup_level; state["dn_bar"] = bar_idx

    if state.get("up") and (bar_idx - state.get("up_bar",0)) > u.max_retest_bars: state["up"] = False
    if state.get("dn") and (bar_idx - state.get("dn_bar",0)) > u.max_retest_bars: state["dn"] = False

    retest_up = state.get("up") and low <= (state.get("res",0)+sr_zone) and close > state.get("res",0) and close > open_
    retest_dn = state.get("dn") and high >= (state.get("sup",0)-sr_zone) and close < state.get("sup",0) and close < open_

    long_sig  = retest_up and pat_long_ok  and vol_ok and rsi_long_ok  and bull_trend
    short_sig = retest_dn and pat_short_ok and vol_ok and rsi_short_ok and bear_trend

    if not long_sig and not short_sig: return None

    direction = "LONG" if long_sig else "SHORT"

    if long_sig:
        entry = close
        sl    = low - atr_now * u.atr_mult
        risk  = entry - sl
        if (risk/entry*100) > u.max_risk_pct:
            sl = entry * (1 - u.max_risk_pct/100); risk = entry - sl
        tp1 = entry + risk * u.tp1_rr
        tp2 = entry + risk * u.tp2_rr
        tp3 = entry + risk * u.tp3_rr
        state["up"] = False
        pattern = bull_pat or "—"
    else:
        entry = close
        sl    = high + atr_now * u.atr_mult
        risk  = sl - entry
        if (risk/entry*100) > u.max_risk_pct:
            sl = entry * (1 + u.max_risk_pct/100); risk = sl - entry
        tp1 = entry - risk * u.tp1_rr
        tp2 = entry - risk * u.tp2_rr
        tp3 = entry - risk * u.tp3_rr
        state["dn"] = False
        pattern = bear_pat or "—"

    risk_pct = abs((sl-entry)/entry*100)
    quality  = 1
    reasons  = []
    if vol_ok:        quality += 1; reasons.append(f"✅ Объём x{vol_ratio:.1f}")
    if bool(bull_pat if long_sig else bear_pat): quality += 1; reasons.append(f"✅ {pattern}")
    if (long_sig and rsi_now < 50) or (short_sig and rsi_now > 50): quality += 1; reasons.append(f"✅ RSI {rsi_now:.1f}")
    if (long_sig and htf_bull) or (short_sig and htf_bear): quality += 1; reasons.append("✅ HTF тренд")
    quality = min(quality, 5)

    return dict(symbol=symbol, direction=direction, entry=entry, sl=sl,
                tp1=tp1, tp2=tp2, tp3=tp3, risk_pct=risk_pct, quality=quality,
                reasons=reasons, rsi=rsi_now, volume_ratio=vol_ratio,
                trend_local=trend_local, trend_htf=trend_htf, pattern=pattern,
                breakout_type="Ретест сопротивления" if long_sig else "Ретест поддержки")


def make_signal_text(sig: dict, user: UserSettings, smc: SMCResult, ch24=None) -> str:
    stars = "⭐"*sig["quality"] + "☆"*(5-sig["quality"])
    hdr   = "🟢 <b>LONG СИГНАЛ</b>" if sig["direction"]=="LONG" else "🔴 <b>SHORT СИГНАЛ</b>"
    emoji = "📈" if sig["direction"]=="LONG" else "📉"
    risk  = abs(sig["entry"]-sig["sl"])
    def pct(t): return abs((t-sig["entry"])/sig["entry"]*100)

    lines = [
        hdr, "",
        f"💎 <b>{sig['symbol']}</b>  {emoji}  {sig['breakout_type']}",
        f"⭐ CHM: {stars}", "",
        "━━━━━━━━━━━━━━━━━━━━",
        f"💰 Вход:   <code>{sig['entry']:.6g}</code>",
        f"🛑 Стоп:   <code>{sig['sl']:.6g}</code>  <i>(-{sig['risk_pct']:.2f}%)</i>", "",
        f"🎯 Цель 1: <code>{sig['tp1']:.6g}</code>  <i>(+{pct(sig['tp1']):.2f}%)</i>",
        f"🎯 Цель 2: <code>{sig['tp2']:.6g}</code>  <i>(+{pct(sig['tp2']):.2f}%)</i>",
        f"🏆 Цель 3: <code>{sig['tp3']:.6g}</code>  <i>(+{pct(sig['tp3']):.2f}%)</i>",
        "━━━━━━━━━━━━━━━━━━━━", "",
        f"📊 {sig['trend_local']}  |  RSI: <code>{sig['rsi']:.1f}</code>  |  Vol: <code>x{sig['volume_ratio']:.1f}</code>",
        f"🕯 Паттерн: {sig['pattern']}",
    ]
    if user.use_smc and smc:
        score = smc.smc_long_score if sig["direction"]=="LONG" else smc.smc_short_score
        dots  = "🔵"*score + "⚪"*(4-score)
        lines += ["", f"━━━━ 🧠 SMART MONEY ━━━━", f"SMC: {dots}  ({score}/4)"]
        if smc.price_in_bull_ob and sig["direction"]=="LONG":   lines.append("📦 Бычий Order Block")
        if smc.price_in_bear_ob and sig["direction"]=="SHORT":  lines.append("📦 Медвежий Order Block")
        if smc.price_in_bull_fvg and sig["direction"]=="LONG":  lines.append("⚡ Бычий FVG (имбаланс)")
        if smc.price_in_bear_fvg and sig["direction"]=="SHORT": lines.append("⚡ Медвежий FVG")
        if smc.recent_sell_sweep and sig["direction"]=="LONG":  lines.append("💧 Sweep лоёв — сбор стопов")
        if smc.recent_buy_sweep and sig["direction"]=="SHORT":  lines.append("💧 Sweep хаёв — сбор стопов")
        if smc.bos_direction=="bull" and sig["direction"]=="LONG":  lines.append("📈 Бычий BOS")
        if smc.bos_direction=="bear" and sig["direction"]=="SHORT": lines.append("📉 Медвежий BOS")
        if score == 0: lines.append("⚪ SMC нейтральный")
    if ch24:
        em = "🔺" if ch24["change_pct"]>0 else "🔻"
        lines += ["", f"📅 24h: {em} {ch24['change_pct']:+.2f}%  |  Vol: ${ch24['volume_usdt']:,.0f}"]
    lines += ["", "⚡ <i>CHM Laboratory — CHM BREAKER + SMC</i>"]
    return "\n".join(lines)


class UserScanState:
    def __init__(self): self.last_scan = 0.0; self.last_signals = {}; self.states = {}


class MultiScanner:
    def __init__(self, config: Config, bot: Bot, um: UserManager):
        self.cfg      = config
        self.bot      = bot
        self.um       = um
        self.fetcher  = BinanceFetcher()
        self._smc     = SMCAnalyzer()
        self._cache:  dict[str, tuple] = {}
        self._coins:  list = []
        self._coins_at: float = 0.0
        self._uss:    dict[int, UserScanState] = {}

    def _uss_get(self, uid): 
        if uid not in self._uss: self._uss[uid] = UserScanState()
        return self._uss[uid]

    async def _candles(self, sym, tf, limit=300):
        key = f"{sym}_{tf}"; now = time.time()
        if key in self._cache and now - self._cache[key][1] < 60: return self._cache[key][0]
        df = await self.fetcher.get_candles(sym, tf, limit=limit)
        if df is not None: self._cache[key] = (df, now)
        return df

    async def _coins_list(self, min_vol):
        now = time.time()
        if self._coins and now - self._coins_at < 3600*6: return self._coins
        coins = await self.fetcher.get_all_usdt_pairs(min_volume_usdt=min_vol, blacklist=self.cfg.AUTO_BLACKLIST)
        self._coins = coins or self.cfg.COINS; self._coins_at = now
        return self._coins

    async def _send(self, user: UserSettings, sig: dict, smc: SMCResult):
        ch24 = await self.fetcher.get_24h_change(sig["symbol"])
        text = make_signal_text(sig, user, smc, ch24)
        try:
            await self.bot.send_message(user.user_id, text, parse_mode="HTML")
            user.signals_received += 1; self.um.save_user(user)
            log.info(f"✅ {user.username or user.user_id}: {sig['symbol']} {sig['direction']} ⭐{sig['quality']}")
        except TelegramForbiddenError:
            user.active = False; self.um.save_user(user)
        except Exception as e:
            log.error(f"Ошибка отправки: {e}")

    async def _scan_user(self, user: UserSettings):
        uss   = self._uss_get(user.user_id)
        coins = await self._coins_list(user.min_volume_usdt)
        smc_a = SMCAnalyzer(ob_lookback=user.ob_lookback, fvg_lookback=user.fvg_lookback, liq_lookback=user.liq_lookback)
        sigs  = 0

        for i in range(0, len(coins), self.cfg.CHUNK_SIZE):
            chunk = coins[i:i+self.cfg.CHUNK_SIZE]
            dfs   = await asyncio.gather(*[self._candles(s, user.timeframe) for s in chunk])

            for sym, df in zip(chunk, dfs):
                if df is None or len(df) < 100: continue
                df_htf = await self._candles(sym, user.htf_timeframe, 100) if user.use_htf else None

                bar_now = len(df)
                if bar_now - uss.last_signals.get(sym, -999) < user.cooldown_bars: continue

                state = uss.states.setdefault(sym, {})
                try:
                    sig = analyze(sym, df, df_htf, user, state)
                except Exception as e:
                    log.debug(f"{sym} ошибка: {e}"); continue

                if sig is None or sig["quality"] < user.min_quality: continue

                smc_res = SMCResult()
                if user.use_smc:
                    try:
                        smc_res = smc_a.analyze(df)
                        score   = smc_res.smc_long_score if sig["direction"]=="LONG" else smc_res.smc_short_score
                        if user.min_smc_score > 0 and score < user.min_smc_score: continue
                    except: pass

                uss.last_signals[sym] = bar_now
                if user.notify_signal:
                    await self._send(user, sig, smc_res)
                sigs += 1

            await asyncio.sleep(0.2)

        log.info(f"  {user.username or user.user_id}: {sigs} сигналов из {len(coins)} монет")

    async def scan_all_users(self):
        now = time.time()
        for user in self.um.get_active_users():
            uss = self._uss_get(user.user_id)
            if now - uss.last_scan < user.scan_interval: continue
            uss.last_scan = now
            log.info(f"🔍 Скан: {user.username or user.user_id} TF={user.timeframe}")
            await self._scan_user(user)

    async def run_forever(self):
        log.info("🔄 Мульти-сканер запущен")
        while True:
            try: await self.scan_all_users()
            except Exception as e: log.error(f"Ошибка: {e}")
            await asyncio.sleep(30)
