"""
╔══════════════════════════════════════════════════════════════╗
║           SMART MONEY CONCEPTS (SMC) — Анализатор           ║
║   Order Blocks | FVG | Liquidity Sweeps | Break of Structure ║
╚══════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OrderBlock:
    direction: str    # "bull" или "bear"
    high:      float
    low:       float
    origin:    float  # середина блока
    bar_idx:   int
    strength:  int    # 1-3 (сколько раз блок устоял)
    mitigated: bool = False


@dataclass
class FVG:
    direction: str   # "bull" или "bear"
    top:       float
    bottom:    float
    bar_idx:   int
    filled:    bool = False


@dataclass
class LiquiditySweep:
    direction: str   # "buy_side" (пробой хая) или "sell_side" (пробой лоя)
    level:     float
    bar_idx:   int
    reversed:  bool = False  # вернулась ли цена обратно (настоящий sweep)


@dataclass
class BOS:
    direction: str   # "bull" или "bear"
    level:     float
    bar_idx:   int
    confirmed: bool = False


@dataclass
class SMCResult:
    """Результат SMC анализа для одной монеты"""

    # Order Blocks
    bull_ob:          Optional[OrderBlock] = None   # ближайший бычий OB
    bear_ob:          Optional[OrderBlock] = None   # ближайший медвежий OB
    price_in_bull_ob: bool = False                  # цена сейчас в бычьем OB
    price_in_bear_ob: bool = False

    # Fair Value Gaps
    bull_fvg:          Optional[FVG] = None
    bear_fvg:          Optional[FVG] = None
    price_in_bull_fvg: bool = False
    price_in_bear_fvg: bool = False

    # Liquidity Sweeps
    recent_buy_sweep:  Optional[LiquiditySweep] = None   # пробой уровня покупателей
    recent_sell_sweep: Optional[LiquiditySweep] = None

    # Break of Structure
    last_bos:          Optional[BOS] = None
    bos_direction:     str = ""   # "bull" или "bear"

    # Итоговый вердикт
    smc_long_score:   int = 0   # 0-4 (сколько SMC факторов за лонг)
    smc_short_score:  int = 0   # 0-4 (сколько SMC факторов за шорт)
    smc_summary:      str = ""  # текстовое описание


class SMCAnalyzer:

    def __init__(self, ob_lookback: int = 50, fvg_lookback: int = 30, liq_lookback: int = 40):
        self.ob_lookback  = ob_lookback
        self.fvg_lookback = fvg_lookback
        self.liq_lookback = liq_lookback

    # ─────────────────────────────────────────────
    #  ORDER BLOCKS
    # ─────────────────────────────────────────────

    def find_order_blocks(self, df: pd.DataFrame) -> list[OrderBlock]:
        """
        Order Block — последняя медвежья свеча перед сильным бычьим движением
        (и наоборот). Это зоны где институционалы набирали позицию.
        """
        obs = []
        highs  = df["high"].values
        lows   = df["low"].values
        opens  = df["open"].values
        closes = df["close"].values
        n = len(df)

        lookback = min(self.ob_lookback, n - 5)

        for i in range(2, lookback):
            idx = n - 1 - i  # идём с конца

            # Бычий OB: медвежья свеча (close < open) перед
            # сильным движением вверх (следующие 3 свечи бычьи)
            if closes[idx] < opens[idx]:  # медвежья свеча
                # Проверяем что после неё было сильное движение вверх
                if idx + 3 < n:
                    move_up = highs[idx + 3] > highs[idx] * 1.003
                    next_bull = closes[idx + 1] > opens[idx + 1]
                    if move_up and next_bull:
                        ob = OrderBlock(
                            direction="bull",
                            high=highs[idx],
                            low=lows[idx],
                            origin=(highs[idx] + lows[idx]) / 2,
                            bar_idx=idx,
                            strength=1,
                        )
                        obs.append(ob)

            # Медвежий OB: бычья свеча перед сильным движением вниз
            if closes[idx] > opens[idx]:  # бычья свеча
                if idx + 3 < n:
                    move_down = lows[idx + 3] < lows[idx] * 0.997
                    next_bear  = closes[idx + 1] < opens[idx + 1]
                    if move_down and next_bear:
                        ob = OrderBlock(
                            direction="bear",
                            high=highs[idx],
                            low=lows[idx],
                            origin=(highs[idx] + lows[idx]) / 2,
                            bar_idx=idx,
                            strength=1,
                        )
                        obs.append(ob)

        # Убираем смягчённые OB (цена уже прошла сквозь них)
        current_close = closes[-1]
        active_obs = []
        for ob in obs:
            if ob.direction == "bull" and current_close > ob.low:
                active_obs.append(ob)
            elif ob.direction == "bear" and current_close < ob.high:
                active_obs.append(ob)

        return active_obs

    # ─────────────────────────────────────────────
    #  FAIR VALUE GAPS
    # ─────────────────────────────────────────────

    def find_fvg(self, df: pd.DataFrame) -> list[FVG]:
        """
        FVG (Fair Value Gap / Имбаланс) — три свечи где средняя свеча
        создала разрыв между хаем первой и лоем третьей (или наоборот).
        Цена часто возвращается заполнить этот гэп.
        """
        fvgs = []
        highs  = df["high"].values
        lows   = df["low"].values
        closes = df["close"].values
        n = len(df)

        lookback = min(self.fvg_lookback, n - 3)

        for i in range(lookback, 0, -1):
            idx = n - 1 - i

            if idx < 2 or idx + 1 >= n:
                continue

            # Бычий FVG: лой свечи [idx+1] выше хая свечи [idx-1]
            # Значит между ними есть незаполненный пространство снизу
            if lows[idx + 1] > highs[idx - 1]:
                gap_size = lows[idx + 1] - highs[idx - 1]
                if gap_size > 0:
                    fvg = FVG(
                        direction="bull",
                        top=lows[idx + 1],
                        bottom=highs[idx - 1],
                        bar_idx=idx,
                    )
                    # Проверяем незаполнен ли (текущая цена выше гэпа)
                    if closes[-1] > fvg.bottom:
                        fvgs.append(fvg)

            # Медвежий FVG: хай свечи [idx+1] ниже лоя свечи [idx-1]
            if highs[idx + 1] < lows[idx - 1]:
                gap_size = lows[idx - 1] - highs[idx + 1]
                if gap_size > 0:
                    fvg = FVG(
                        direction="bear",
                        top=lows[idx - 1],
                        bottom=highs[idx + 1],
                        bar_idx=idx,
                    )
                    if closes[-1] < fvg.top:
                        fvgs.append(fvg)

        return fvgs

    # ─────────────────────────────────────────────
    #  LIQUIDITY SWEEPS
    # ─────────────────────────────────────────────

    def find_liquidity_sweeps(self, df: pd.DataFrame) -> list[LiquiditySweep]:
        """
        Liquidity Sweep — когда цена пробивает очевидный уровень
        (хай/лой где накоплены стопы) и резко разворачивается.
        Это классический манипуляционный паттерн смарт-мани.
        """
        sweeps = []
        highs  = df["high"].values
        lows   = df["low"].values
        closes = df["close"].values
        n = len(df)

        lookback = min(self.liq_lookback, n - 5)

        for i in range(3, lookback):
            idx = n - 1 - i

            # Ищем локальные максимумы (Buy Side Liquidity)
            # Пробой максимума с разворотом вниз
            local_high = max(highs[max(0, idx - 5): idx])
            if highs[idx] > local_high and closes[idx] < local_high:
                sweep = LiquiditySweep(
                    direction="buy_side",
                    level=local_high,
                    bar_idx=idx,
                    reversed=True,
                )
                sweeps.append(sweep)

            # Ищем локальные минимумы (Sell Side Liquidity)
            local_low = min(lows[max(0, idx - 5): idx])
            if lows[idx] < local_low and closes[idx] > local_low:
                sweep = LiquiditySweep(
                    direction="sell_side",
                    level=local_low,
                    bar_idx=idx,
                    reversed=True,
                )
                sweeps.append(sweep)

        return sweeps

    # ─────────────────────────────────────────────
    #  BREAK OF STRUCTURE
    # ─────────────────────────────────────────────

    def find_bos(self, df: pd.DataFrame) -> list[BOS]:
        """
        Break of Structure (BOS) — пробой предыдущего значимого
        максимума или минимума. Сигнализирует о смене тренда.
        """
        bos_list = []
        highs  = df["high"].values
        lows   = df["low"].values
        closes = df["close"].values
        n = len(df)

        if n < 10:
            return []

        # Ищем последние swing high/low
        for i in range(5, min(40, n - 5)):
            idx = n - 1 - i

            # Swing High (локальный максимум)
            window = highs[max(0, idx - 3): idx + 4]
            if len(window) > 0 and highs[idx] == max(window):
                # Проверяем пробой этого хая последующими свечами
                for j in range(idx + 1, min(idx + 10, n)):
                    if closes[j] > highs[idx]:
                        bos = BOS(
                            direction="bull",
                            level=highs[idx],
                            bar_idx=j,
                            confirmed=True,
                        )
                        bos_list.append(bos)
                        break

            # Swing Low
            window = lows[max(0, idx - 3): idx + 4]
            if len(window) > 0 and lows[idx] == min(window):
                for j in range(idx + 1, min(idx + 10, n)):
                    if closes[j] < lows[idx]:
                        bos = BOS(
                            direction="bear",
                            level=lows[idx],
                            bar_idx=j,
                            confirmed=True,
                        )
                        bos_list.append(bos)
                        break

        return bos_list

    # ─────────────────────────────────────────────
    #  ГЛАВНЫЙ МЕТОД
    # ─────────────────────────────────────────────

    def analyze(self, df: pd.DataFrame) -> SMCResult:
        result = SMCResult()

        if df is None or len(df) < 50:
            return result

        current_close = df["close"].iloc[-1]
        current_high  = df["high"].iloc[-1]
        current_low   = df["low"].iloc[-1]

        # ── Order Blocks ──────────────────────────────
        obs = self.find_order_blocks(df)

        bull_obs = [o for o in obs if o.direction == "bull"]
        bear_obs = [o for o in obs if o.direction == "bear"]

        if bull_obs:
            # Ближайший бычий OB снизу от текущей цены
            below = [o for o in bull_obs if o.high < current_close]
            if below:
                result.bull_ob = max(below, key=lambda x: x.high)
                ob = result.bull_ob
                result.price_in_bull_ob = (ob.low <= current_close <= ob.high * 1.001)

        if bear_obs:
            # Ближайший медвежий OB сверху
            above = [o for o in bear_obs if o.low > current_close]
            if above:
                result.bear_ob = min(above, key=lambda x: x.low)
                ob = result.bear_ob
                result.price_in_bear_ob = (ob.low * 0.999 <= current_close <= ob.high)

        # ── Fair Value Gaps ───────────────────────────
        fvgs = self.find_fvg(df)

        bull_fvgs = [f for f in fvgs if f.direction == "bull"]
        bear_fvgs = [f for f in fvgs if f.direction == "bear"]

        if bull_fvgs:
            result.bull_fvg = max(bull_fvgs, key=lambda x: x.bar_idx)
            fvg = result.bull_fvg
            result.price_in_bull_fvg = (fvg.bottom <= current_close <= fvg.top)

        if bear_fvgs:
            result.bear_fvg = max(bear_fvgs, key=lambda x: x.bar_idx)
            fvg = result.bear_fvg
            result.price_in_bear_fvg = (fvg.bottom <= current_close <= fvg.top)

        # ── Liquidity Sweeps ──────────────────────────
        sweeps = self.find_liquidity_sweeps(df)
        recent = [s for s in sweeps if s.reversed]

        if recent:
            buy_sweeps  = [s for s in recent if s.direction == "buy_side"]
            sell_sweeps = [s for s in recent if s.direction == "sell_side"]
            if buy_sweeps:
                result.recent_buy_sweep = max(buy_sweeps, key=lambda x: x.bar_idx)
            if sell_sweeps:
                result.recent_sell_sweep = max(sell_sweeps, key=lambda x: x.bar_idx)

        # ── Break of Structure ────────────────────────
        bos_list = self.find_bos(df)
        if bos_list:
            result.last_bos = max(bos_list, key=lambda x: x.bar_idx)
            result.bos_direction = result.last_bos.direction

        # ── Итоговый скор ─────────────────────────────
        long_score  = 0
        short_score = 0
        long_reasons  = []
        short_reasons = []

        # OB
        if result.price_in_bull_ob:
            long_score += 1
            long_reasons.append("📦 Цена в бычьем Order Block")
        if result.price_in_bear_ob:
            short_score += 1
            short_reasons.append("📦 Цена в медвежьем Order Block")

        # FVG
        if result.price_in_bull_fvg:
            long_score += 1
            long_reasons.append("⚡ Цена в бычьем FVG (имбаланс)")
        if result.price_in_bear_fvg:
            short_score += 1
            short_reasons.append("⚡ Цена в медвежьем FVG (имбаланс)")

        # Liquidity Sweep
        n = len(df)
        if result.recent_sell_sweep and (n - result.recent_sell_sweep.bar_idx) < 10:
            long_score += 1
            long_reasons.append("💧 Свежий sweep лоёв (сбор ликвидности вниз)")
        if result.recent_buy_sweep and (n - result.recent_buy_sweep.bar_idx) < 10:
            short_score += 1
            short_reasons.append("💧 Свежий sweep хаёв (сбор ликвидности вверх)")

        # BOS
        if result.bos_direction == "bull":
            long_score += 1
            long_reasons.append("📈 Бычий BOS (слом медвежьей структуры)")
        elif result.bos_direction == "bear":
            short_score += 1
            short_reasons.append("📉 Медвежий BOS (слом бычьей структуры)")

        result.smc_long_score  = long_score
        result.smc_short_score = short_score

        if long_score > short_score:
            result.smc_summary = "\n".join(long_reasons)
        elif short_score > long_score:
            result.smc_summary = "\n".join(short_reasons)
        else:
            result.smc_summary = "⚖️ SMC нейтральный"

        return result
