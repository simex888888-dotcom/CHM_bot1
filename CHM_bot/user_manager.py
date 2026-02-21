"""
Управление пользователями — все настройки персональные
"""

import json
import os
import logging
from dataclasses import dataclass, asdict
from typing import Optional

log = logging.getLogger("CHM.Users")
USERS_FILE = "users.json"


@dataclass
class UserSettings:
    user_id:          int
    username:         str   = ""
    active:           bool  = False

    # ── Таймфрейм и интервал ──────────────────────────
    timeframe:        str   = "1h"
    scan_interval:    int   = 3600
    htf_timeframe:    str   = "1d"   # старший ТФ для HTF фильтра

    # ── Фильтры CHM BREAKER ───────────────────────────
    use_rsi:          bool  = True
    use_volume:       bool  = True
    use_pattern:      bool  = True
    use_htf:          bool  = True
    min_quality:      int   = 3

    # ── RSI настройки ─────────────────────────────────
    rsi_period:       int   = 14
    rsi_ob:           int   = 65     # перекупленность
    rsi_os:           int   = 35     # перепроданность

    # ── Объёмный фильтр ───────────────────────────────
    vol_mult:         float = 1.2    # объём должен быть в X раз выше среднего
    vol_len:          int   = 20     # период среднего объёма

    # ── Пивоты (S/R уровни) ───────────────────────────
    pivot_strength:   int   = 7      # чувствительность поиска пивотов
    max_level_age:    int   = 100    # макс. возраст уровня (свечей)
    max_retest_bars:  int   = 30     # макс. ожидание ретеста (свечей)
    zone_buffer:      float = 0.3    # буфер зоны S/R (x ATR)

    # ── ATR / Стоп-лосс ───────────────────────────────
    atr_period:       int   = 14
    atr_mult:         float = 1.0
    max_risk_pct:     float = 1.5

    # ── EMA тренд ─────────────────────────────────────
    ema_fast:         int   = 50
    ema_slow:         int   = 200
    htf_ema_period:   int   = 50

    # ── Цели ──────────────────────────────────────────
    tp1_rr:           float = 0.8
    tp2_rr:           float = 1.5
    tp3_rr:           float = 2.5

    # ── Cooldown ──────────────────────────────────────
    cooldown_bars:    int   = 10     # пауза между сигналами на одной монете

    # ── Фильтр монет ──────────────────────────────────
    min_volume_usdt:  float = 1_000_000

    # ── SMC ───────────────────────────────────────────
    use_smc:          bool  = True
    use_ob:           bool  = True
    use_fvg:          bool  = True
    use_liq:          bool  = True
    use_bos:          bool  = True
    min_smc_score:    int   = 1
    ob_lookback:      int   = 50     # глубина поиска Order Blocks
    fvg_lookback:     int   = 30     # глубина поиска FVG
    liq_lookback:     int   = 40     # глубина поиска Sweeps

    # ── Уведомления ───────────────────────────────────
    notify_signal:    bool  = True
    notify_breakout:  bool  = False

    # ── Статистика ────────────────────────────────────
    signals_received: int   = 0


class UserManager:

    def __init__(self):
        self._users: dict[int, UserSettings] = {}
        self._load()

    def _load(self):
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for uid, d in data.items():
                    defaults = asdict(UserSettings(user_id=int(uid)))
                    merged   = {**defaults, **d}
                    self._users[int(uid)] = UserSettings(**merged)
                log.info(f"Загружено пользователей: {len(self._users)}")
            except Exception as e:
                log.error(f"Ошибка загрузки: {e}")

    def _save(self):
        try:
            data = {str(uid): asdict(u) for uid, u in self._users.items()}
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Ошибка сохранения: {e}")

    def get_or_create(self, user_id: int, username: str = "") -> UserSettings:
        if user_id not in self._users:
            self._users[user_id] = UserSettings(user_id=user_id, username=username)
            self._save()
            log.info(f"Новый пользователь: {username} ({user_id})")
        return self._users[user_id]

    def save_user(self, user: UserSettings):
        self._users[user.user_id] = user
        self._save()

    def get_active_users(self) -> list:
        return [u for u in self._users.values() if u.active]
