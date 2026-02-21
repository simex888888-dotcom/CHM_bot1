"""
Клавиатуры — все настройки с описаниями
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from user_manager import UserSettings


def _check(val: bool) -> str:
    return "✅" if val else "❌"

def _btn(text: str, cb: str) -> list:
    return [InlineKeyboardButton(text=text, callback_data=cb)]

def _back(cb: str = "back_main") -> list:
    return [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]


def kb_main(user: UserSettings) -> InlineKeyboardMarkup:
    status = "🟢 Сканер ВКЛ — нажми чтобы остановить" if user.active \
        else "🔴 Сканер ВЫКЛ — нажми чтобы запустить"
    smc = "🧠 SMC: ВКЛ ✅" if user.use_smc else "🧠 SMC: ВЫКЛ ❌"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status,                         callback_data="toggle_active")],
        [InlineKeyboardButton(text="📊 Таймфрейм",                 callback_data="menu_tf")],
        [InlineKeyboardButton(text="🔄 Интервал сканирования",     callback_data="menu_interval")],
        [InlineKeyboardButton(text="📐 Пивоты и уровни S/R",      callback_data="menu_pivots")],
        [InlineKeyboardButton(text="📉 EMA тренд",                 callback_data="menu_ema")],
        [InlineKeyboardButton(text="🔬 Фильтры (RSI / Объём)",    callback_data="menu_filters")],
        [InlineKeyboardButton(text="⭐ Качество сигнала",          callback_data="menu_quality")],
        [InlineKeyboardButton(text="🛡 Стоп-лосс (ATR)",           callback_data="menu_sl")],
        [InlineKeyboardButton(text="🎯 Цели (Take Profit R:R)",    callback_data="menu_targets")],
        [InlineKeyboardButton(text="💰 Фильтр монет по объёму",    callback_data="menu_volume")],
        [InlineKeyboardButton(text=smc,                            callback_data="menu_smc")],
        [InlineKeyboardButton(text="📱 Уведомления",               callback_data="menu_notify")],
        [InlineKeyboardButton(text="🔄 Cooldown между сигналами",  callback_data="menu_cooldown")],
        [InlineKeyboardButton(text="📈 Моя статистика",            callback_data="my_stats")],
        [InlineKeyboardButton(text="❓ Как работает бот",          callback_data="how_it_works")],
        [InlineKeyboardButton(text="♻️ Сбросить к стандартным",   callback_data="reset_confirm")],
    ])


def kb_timeframes(current_tf: str, current_htf: str) -> InlineKeyboardMarkup:
    tfs = [
        ("1m",  "1 мин  — скальпинг. Очень много сигналов, высокий шум"),
        ("5m",  "5 мин  — скальпинг. Быстрые входы"),
        ("15m", "15 мин — интрадей. Баланс скорости и качества"),
        ("30m", "30 мин — интрадей. Надёжнее 15m"),
        ("1h",  "1 час  — свинг. Лучший вариант ⭐"),
        ("4h",  "4 часа — свинг. Редкие но сильные сигналы"),
        ("1d",  "1 день — позиционная. Сигналы раз в дни"),
    ]
    htfs = [
        ("4h", "4H"),
        ("1d", "1D ⭐"),
        ("1w", "1W"),
    ]
    rows = [[InlineKeyboardButton(text="── Рабочий таймфрейм ──", callback_data="noop")]]
    for tf, desc in tfs:
        mark = "◉ " if tf == current_tf else "○ "
        rows.append(_btn(f"{mark}{tf} — {desc}", f"set_tf_{tf}"))

    rows.append(_btn("── HTF таймфрейм для фильтра тренда ──", "noop"))
    for htf, label in htfs:
        mark = "◉ " if htf == current_htf else "○ "
        rows.append(_btn(f"{mark}{label}", f"set_htf_{htf}"))

    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_intervals(current: int) -> InlineKeyboardMarkup:
    options = [
        (300,   "5 мин   — для ТФ 1m-5m"),
        (900,   "15 мин  — для ТФ 15m"),
        (1800,  "30 мин  — для ТФ 30m"),
        (3600,  "1 час   — для ТФ 1h ⭐"),
        (7200,  "2 часа  — для ТФ 1h-4h"),
        (14400, "4 часа  — для ТФ 4h"),
        (86400, "1 день  — для ТФ 1d"),
    ]
    rows = []
    for sec, desc in options:
        mark = "◉ " if sec == current else "○ "
        rows.append(_btn(f"{mark}{desc}", f"set_interval_{sec}"))
    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_pivots(user: UserSettings) -> InlineKeyboardMarkup:
    strengths = [(3,"3 — много уровней, шумно"), (5,"5 — средне"), (7,"7 — стандарт ⭐"), (10,"10 — мало, только сильные"), (15,"15 — только ключевые")]
    ages      = [(50,"50 свечей"), (100,"100 свечей ⭐"), (150,"150 свечей"), (200,"200 свечей")]
    retests   = [(10,"10 свечей — быстро"), (20,"20 свечей"), (30,"30 свечей ⭐"), (50,"50 свечей — долго")]
    buffers   = [(0.1,"x0.1 — узкая зона"), (0.2,"x0.2"), (0.3,"x0.3 ⭐"), (0.5,"x0.5 — широкая зона")]

    rows = [_btn("── Чувствительность пивотов ──", "noop")]
    rows += [_btn(("◉ " if v == user.pivot_strength else "○ ") + d, f"set_pivot_strength_{v}") for v, d in strengths]
    rows.append(_btn("── Макс. возраст уровня (свечей) ──", "noop"))
    rows += [_btn(("◉ " if v == user.max_level_age else "○ ") + d, f"set_level_age_{v}") for v, d in ages]
    rows.append(_btn("── Макс. ожидание ретеста (свечей) ──", "noop"))
    rows += [_btn(("◉ " if v == user.max_retest_bars else "○ ") + d, f"set_retest_bars_{v}") for v, d in retests]
    rows.append(_btn("── Буфер зоны S/R (x ATR) ──", "noop"))
    rows += [_btn(("◉ " if v == user.zone_buffer else "○ ") + d, f"set_zone_buffer_{v}") for v, d in buffers]
    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_ema(user: UserSettings) -> InlineKeyboardMarkup:
    fast_opts = [(20,"EMA 20 — быстрый"), (50,"EMA 50 ⭐"), (100,"EMA 100")]
    slow_opts = [(100,"EMA 100"), (200,"EMA 200 ⭐"), (500,"EMA 500 — очень долгий")]
    htf_opts  = [(20,"EMA 20"), (50,"EMA 50 ⭐"), (100,"EMA 100"), (200,"EMA 200")]

    rows = [_btn("── Быстрая EMA (тренд) ──", "noop")]
    rows += [_btn(("◉ " if v == user.ema_fast else "○ ") + d, f"set_ema_fast_{v}") for v, d in fast_opts]
    rows.append(_btn("── Медленная EMA (тренд) ──", "noop"))
    rows += [_btn(("◉ " if v == user.ema_slow else "○ ") + d, f"set_ema_slow_{v}") for v, d in slow_opts]
    rows.append(_btn("── HTF EMA период ──", "noop"))
    rows += [_btn(("◉ " if v == user.htf_ema_period else "○ ") + d, f"set_htf_ema_{v}") for v, d in htf_opts]
    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_filters(user: UserSettings) -> InlineKeyboardMarkup:
    rsi_periods = [(7,"RSI 7 — быстрый"), (14,"RSI 14 ⭐"), (21,"RSI 21 — медленный")]
    ob_vals     = [(60,"OB 60 — мягко"), (65,"OB 65 ⭐"), (70,"OB 70 — строго"), (75,"OB 75 — очень строго")]
    os_vals     = [(25,"OS 25 — строго"), (30,"OS 30 — строго"), (35,"OS 35 ⭐"), (40,"OS 40 — мягко")]
    vol_mults   = [(1.0,"x1.0 — любой объём"), (1.2,"x1.2 ⭐"), (1.5,"x1.5 — повышенный"), (2.0,"x2.0 — высокий")]
    vol_lens    = [(10,"10 свечей"), (20,"20 свечей ⭐"), (30,"30 свечей")]

    rows = [
        _btn(f"{_check(user.use_rsi)} RSI фильтр — блокирует входы на экстремумах", "toggle_rsi"),
        _btn(f"{_check(user.use_volume)} Объёмный фильтр — пробой должен быть на объёме", "toggle_volume"),
        _btn(f"{_check(user.use_pattern)} Паттерны — пин-бар, поглощение, молот", "toggle_pattern"),
        _btn(f"{_check(user.use_htf)} HTF фильтр — торговля только по тренду старшего ТФ", "toggle_htf"),
        _btn("── Период RSI ──", "noop"),
    ]
    rows += [_btn(("◉ " if v == user.rsi_period else "○ ") + d, f"set_rsi_period_{v}") for v, d in rsi_periods]
    rows.append(_btn(f"── Перекупленность (OB): сейчас {user.rsi_ob} ──", "noop"))
    rows += [_btn(("◉ " if v == user.rsi_ob else "○ ") + d, f"set_rsi_ob_{v}") for v, d in ob_vals]
    rows.append(_btn(f"── Перепроданность (OS): сейчас {user.rsi_os} ──", "noop"))
    rows += [_btn(("◉ " if v == user.rsi_os else "○ ") + d, f"set_rsi_os_{v}") for v, d in os_vals]
    rows.append(_btn("── Мин. объём (x от среднего) ──", "noop"))
    rows += [_btn(("◉ " if v == user.vol_mult else "○ ") + d, f"set_vol_mult_{v}") for v, d in vol_mults]
    rows.append(_btn("── Период среднего объёма ──", "noop"))
    rows += [_btn(("◉ " if v == user.vol_len else "○ ") + d, f"set_vol_len_{v}") for v, d in vol_lens]
    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_quality(current: int) -> InlineKeyboardMarkup:
    opts = [
        (1, "⭐         — любые. Много, но шумно"),
        (2, "⭐⭐        — слабая фильтрация"),
        (3, "⭐⭐⭐       — баланс ⭐"),
        (4, "⭐⭐⭐⭐      — строгая"),
        (5, "⭐⭐⭐⭐⭐     — только идеальные"),
    ]
    rows = [_btn(("◉ " if q == current else "○ ") + d, f"set_quality_{q}") for q, d in opts]
    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_sl(user: UserSettings) -> InlineKeyboardMarkup:
    periods  = [(7,"ATR 7 — быстрый"), (14,"ATR 14 ⭐"), (21,"ATR 21 — медленный")]
    mults    = [(0.5,"x0.5 — очень близко"), (1.0,"x1.0 ⭐"), (1.5,"x1.5 — широкий"), (2.0,"x2.0 — очень широкий")]
    risks    = [(0.5,"0.5%"), (1.0,"1.0%"), (1.5,"1.5% ⭐"), (2.0,"2.0%"), (3.0,"3.0%")]

    rows = [_btn("── Период ATR ──", "noop")]
    rows += [_btn(("◉ " if v == user.atr_period else "○ ") + d, f"set_atr_period_{v}") for v, d in periods]
    rows.append(_btn("── ATR множитель для стопа ──", "noop"))
    rows += [_btn(("◉ " if v == user.atr_mult else "○ ") + d, f"set_atr_{v}") for v, d in mults]
    rows.append(_btn("── Макс. риск от цены ──", "noop"))
    rows += [_btn(("◉ " if v == user.max_risk_pct else "○ ") + d, f"set_risk_{v}") for v, d in risks]
    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_targets(user: UserSettings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        _btn(f"🎯 Цель 1: {user.tp1_rr}R — нажми чтобы изменить", "edit_tp1"),
        _btn(f"🎯 Цель 2: {user.tp2_rr}R — нажми чтобы изменить", "edit_tp2"),
        _btn(f"🏆 Цель 3: {user.tp3_rr}R — нажми чтобы изменить", "edit_tp3"),
        _back(),
    ])


def kb_volume(current: float) -> InlineKeyboardMarkup:
    opts = [
        (100_000,    "100К$ — все монеты включая мелкие"),
        (500_000,    "500К$ — средние и крупные"),
        (1_000_000,  "1М$   — стандарт ⭐"),
        (5_000_000,  "5М$   — только ликвидные"),
        (10_000_000, "10М$  — топ-50"),
        (50_000_000, "50М$  — только топ-10"),
    ]
    rows = [_btn(("◉ " if v == current else "○ ") + d, f"set_volume_{int(v)}") for v, d in opts]
    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_smc(user: UserSettings) -> InlineKeyboardMarkup:
    scores   = [(0,"0 — только информация"), (1,"1 — хотя бы один ⭐"), (2,"2 — два фактора"), (3,"3 — три фактора"), (4,"4 — все четыре")]
    ob_looks = [(30,"30 свечей"), (50,"50 свечей ⭐"), (75,"75 свечей"), (100,"100 свечей")]
    fvg_looks= [(20,"20 свечей"), (30,"30 свечей ⭐"), (50,"50 свечей")]
    liq_looks= [(20,"20 свечей"), (40,"40 свечей ⭐"), (60,"60 свечей")]

    rows = [
        _btn(f"{_check(user.use_smc)} SMC анализ — вкл/выкл всё", "toggle_smc"),
        _btn(f"{_check(user.use_ob)} Order Blocks — зоны набора позиций крупными игроками", "toggle_ob"),
        _btn(f"{_check(user.use_fvg)} Fair Value Gaps — имбалансы куда цена возвращается", "toggle_fvg"),
        _btn(f"{_check(user.use_liq)} Liquidity Sweeps — сбор стопов перед разворотом", "toggle_liq"),
        _btn(f"{_check(user.use_bos)} Break of Structure — слом рыночной структуры", "toggle_bos"),
        _btn("── Мин. кол-во SMC подтверждений ──", "noop"),
    ]
    rows += [_btn(("◉ " if v == user.min_smc_score else "○ ") + d, f"set_smc_score_{v}") for v, d in scores]
    rows.append(_btn("── Глубина поиска Order Blocks ──", "noop"))
    rows += [_btn(("◉ " if v == user.ob_lookback else "○ ") + d, f"set_ob_look_{v}") for v, d in ob_looks]
    rows.append(_btn("── Глубина поиска FVG ──", "noop"))
    rows += [_btn(("◉ " if v == user.fvg_lookback else "○ ") + d, f"set_fvg_look_{v}") for v, d in fvg_looks]
    rows.append(_btn("── Глубина поиска Liquidity Sweeps ──", "noop"))
    rows += [_btn(("◉ " if v == user.liq_lookback else "○ ") + d, f"set_liq_look_{v}") for v, d in liq_looks]
    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_cooldown(current: int) -> InlineKeyboardMarkup:
    opts = [
        (3,  "3 свечи  — очень часто"),
        (5,  "5 свечей — часто"),
        (10, "10 свечей — стандарт ⭐"),
        (15, "15 свечей — редко"),
        (20, "20 свечей — очень редко"),
    ]
    rows = [_btn(("◉ " if v == current else "○ ") + d, f"set_cooldown_{v}") for v, d in opts]
    rows.append(_back())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_notify(user: UserSettings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        _btn(f"{_check(user.notify_signal)} Сигнал входа — вход, стоп, цели", "toggle_notify_signal"),
        _btn(f"{_check(user.notify_breakout)} Пробой уровня — раннее уведомление до ретеста", "toggle_notify_breakout"),
        _back(),
    ])


def kb_reset_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, сбросить всё к стандартным", callback_data="reset_yes")],
        [InlineKeyboardButton(text="❌ Нет, отмена",                    callback_data="back_main")],
    ])


def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[_back()])
