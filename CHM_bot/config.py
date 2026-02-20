"""
╔══════════════════════════════════════════════════════════════╗
║                  НАСТРОЙКИ CHM BREAKER BOT                  ║
║              Редактируй только этот файл!                   ║
╚══════════════════════════════════════════════════════════════╝
"""


class Config:

    # ═══════════════════════════════════════════════════════
    #  🔑 TELEGRAM — ЗАПОЛНИ ЭТИ ДВЕ СТРОКИ!
    # ═══════════════════════════════════════════════════════

    import os
    TELEGRAM_TOKEN   = os.getenv("BOT_TOKEN_CHM")
    TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")
    # ═══════════════════════════════════════════════════════
    #  📊 РЕЖИМ ВЫБОРА МОНЕТ
    # ═══════════════════════════════════════════════════════

    COIN_MODE            = "auto"
    AUTO_MIN_VOLUME_USDT = 1_000_000
    AUTO_MAX_COINS       = 0
    AUTO_BLACKLIST       = [
        "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "USDPUSDT",
        "EURUSDT",  "GBPUSDT",  "RUBUSDT",  "FDUSDUSDT",
    ]
    COINS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    ]


    # ═══════════════════════════════════════════════════════
    #  ⏱  ТАЙМФРЕЙМ И ИНТЕРВАЛ
    # ═══════════════════════════════════════════════════════

    TIMEFRAME     = "1h"
    SCAN_INTERVAL = 300
    CHUNK_SIZE    = 2


    # ═══════════════════════════════════════════════════════
    #  ⚙️  ПАРАМЕТРЫ ИНДИКАТОРА
    # ═══════════════════════════════════════════════════════

    PIVOT_STRENGTH  = 10
    ATR_PERIOD      = 14
    ATR_MULT        = 2.5
    MAX_RISK_PCT    = 2.5
    EMA_FAST        = 21
    EMA_SLOW        = 200
    RSI_PERIOD      = 14
    RSI_OB          = 70
    RSI_OS          = 30
    VOL_MULT        = 2.0
    VOL_LEN         = 20
    MAX_LEVEL_AGE   = 50
    MAX_RETEST_BARS = 15
    COOLDOWN_BARS   = 15
    ZONE_BUFFER     = 0.15
    TP1_RR          = 1.0
    TP2_RR          = 2.0
    TP3_RR          = 3.5
    HTF_TIMEFRAME   = "1h"
    HTF_EMA_PERIOD  = 60


    # ═══════════════════════════════════════════════════════
    #  🔔 ФИЛЬТРЫ И УВЕДОМЛЕНИЯ
    # ═══════════════════════════════════════════════════════

    USE_RSI_FILTER             = True
    USE_VOLUME_FILTER          = True
    USE_PATTERN_FILTER         = True
    USE_HTF_FILTER             = True
    MIN_SIGNAL_QUALITY         = 3
    NOTIFY_ON_BREAKOUT         = True
    NOTIFY_ON_SIGNAL           = True
    MAX_NOTIFICATIONS_PER_HOUR = 30
