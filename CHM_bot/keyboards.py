"""
Клавиатуры Telegram бота — с описаниями под каждой опцией
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from user_manager import UserSettings


def kb_main(user: UserSettings) -> InlineKeyboardMarkup:
    status = "🟢 Сканер ВКЛЮЧЁН — нажми чтобы остановить" if user.active \
        else "🔴 Сканер ВЫКЛЮЧЕН — нажми чтобы запустить"
    smc_label = "🧠 SMC: ВКЛ ✅" if user.use_smc else "🧠 SMC: ВЫКЛ ❌"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status,                          callback_data="toggle_active")],
        [InlineKeyboardButton(text="📊 Таймфрейм",                  callback_data="menu_tf")],
        [InlineKeyboardButton(text="🔄 Интервал сканирования",      callback_data="menu_interval")],
        [InlineKeyboardButton(text="🔬 Фильтры CHM BREAKER",        callback_data="menu_filters")],
        [InlineKeyboardButton(text=smc_label,                       callback_data="menu_smc")],
        [InlineKeyboardButton(text="⭐ Качество сигнала",           callback_data="menu_quality")],
        [InlineKeyboardButton(text="🎯 Цели (Take Profit)",         callback_data="menu_targets")],
        [InlineKeyboardButton(text="🛡 Стоп-лосс (ATR)",            callback_data="menu_sl")],
        [InlineKeyboardButton(text="💰 Фильтр монет по объёму",     callback_data="menu_volume")],
        [InlineKeyboardButton(text="📱 Уведомления",                callback_data="menu_notify")],
        [InlineKeyboardButton(text="📈 Моя статистика",             callback_data="my_stats")],
        [InlineKeyboardButton(text="❓ Как работает бот",           callback_data="how_it_works")],
    ])


def _check(val: bool) -> str:
    return "✅" if val else "❌"


def kb_timeframes(current: str) -> InlineKeyboardMarkup:
    options = [
        ("1m",  "1 минута",   "Скальпинг. Очень много сигналов, высокий шум."),
        ("5m",  "5 минут",    "Скальпинг. Быстрые входы, нужно следить активно."),
        ("15m", "15 минут",   "Интрадей. Хороший баланс скорости и качества."),
        ("30m", "30 минут",   "Интрадей. Меньше сигналов, но надёжнее."),
        ("1h",  "1 час ⭐",   "Свинг. Лучший вариант для большинства трейдеров."),
        ("4h",  "4 часа",     "Свинг. Редкие но очень сильные сигналы."),
        ("1d",  "1 день",     "Позиционная. Сигналы раз в несколько дней."),
    ]
    rows = []
    for tf, label, desc in options:
        mark = "◉ " if tf == current else "○ "
        rows.append([InlineKeyboardButton(
            text=f"{mark}{tf} — {label}\n   ℹ️ {desc}",
            callback_data=f"set_tf_{tf}"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_intervals(current: int) -> InlineKeyboardMarkup:
    options = [
        (300,   "5 минут",  "Для таймфреймов 1m-5m"),
        (900,   "15 минут", "Для таймфрейма 15m"),
        (1800,  "30 минут", "Для таймфрейма 30m"),
        (3600,  "1 час ⭐", "Для таймфрейма 1h — рекомендуется"),
        (7200,  "2 часа",   "Для таймфреймов 1h-4h"),
        (14400, "4 часа",   "Для таймфрейма 4h"),
        (86400, "1 день",   "Для дневного таймфрейма"),
    ]
    rows = []
    for sec, label, desc in options:
        mark = "◉ " if sec == current else "○ "
        rows.append([InlineKeyboardButton(
            text=f"{mark}{label}\n   ℹ️ {desc}",
            callback_data=f"set_interval_{sec}"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_filters(user: UserSettings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{_check(user.use_rsi)} RSI фильтр\n   ℹ️ Блокирует входы когда рынок перекуплен/перепродан",
            callback_data="toggle_rsi"
        )],
        [InlineKeyboardButton(
            text=f"{_check(user.use_volume)} Объёмный фильтр\n   ℹ️ Пробой без объёма = ложный. Включи чтобы фильтровать такие",
            callback_data="toggle_volume"
        )],
        [InlineKeyboardButton(
            text=f"{_check(user.use_pattern)} Свечные паттерны\n   ℹ️ Пин-бар, поглощение, молот — подтверждают разворот",
            callback_data="toggle_pattern"
        )],
        [InlineKeyboardButton(
            text=f"{_check(user.use_htf)} HTF тренд (дневной)\n   ℹ️ Торгуй только по тренду старшего таймфрейма",
            callback_data="toggle_htf"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


def kb_smc(user: UserSettings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{_check(user.use_smc)} Smart Money анализ (вкл/выкл всё)\n   ℹ️ Анализ действий крупных игроков — банков и фондов",
            callback_data="toggle_smc"
        )],
        [InlineKeyboardButton(
            text=f"{_check(user.use_ob)} Order Blocks\n   ℹ️ Зоны где институционалы набирали позицию. Цена часто возвращается туда",
            callback_data="toggle_ob"
        )],
        [InlineKeyboardButton(
            text=f"{_check(user.use_fvg)} Fair Value Gaps (FVG)\n   ℹ️ Имбалансы цены — незаполненные гэпы куда цена притягивается",
            callback_data="toggle_fvg"
        )],
        [InlineKeyboardButton(
            text=f"{_check(user.use_liq)} Liquidity Sweeps\n   ℹ️ Сбор стопов крупным игроком перед разворотом — лучший сигнал",
            callback_data="toggle_liq"
        )],
        [InlineKeyboardButton(
            text=f"{_check(user.use_bos)} Break of Structure (BOS)\n   ℹ️ Слом рыночной структуры — подтверждает смену тренда",
            callback_data="toggle_bos"
        )],
        [InlineKeyboardButton(
            text=f"Мин. SMC подтверждений: {user.min_smc_score} (нажми чтобы изменить)\n   ℹ️ Сколько SMC факторов должно совпасть для сигнала (0 = без требований)",
            callback_data="menu_smc_score"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


def kb_smc_score(current: int) -> InlineKeyboardMarkup:
    options = [
        (0, "0 — SMC как информация, не фильтр"),
        (1, "1 — хотя бы один SMC фактор ⭐"),
        (2, "2 — два SMC фактора совпадают"),
        (3, "3 — три фактора (очень строго)"),
        (4, "4 — все четыре (только идеал)"),
    ]
    rows = []
    for val, label in options:
        mark = "◉ " if val == current else "○ "
        rows.append([InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"set_smc_score_{val}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад в SMC", callback_data="menu_smc")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_quality(current: int) -> InlineKeyboardMarkup:
    options = [
        (1, "⭐",         "Любые сигналы. Много, но шумно — для опытных"),
        (2, "⭐⭐",       "Слабая фильтрация. Больше сигналов"),
        (3, "⭐⭐⭐",     "Баланс. Рекомендуется для большинства"),
        (4, "⭐⭐⭐⭐",   "Строгая фильтрация. Мало но сильных сигналов"),
        (5, "⭐⭐⭐⭐⭐", "Только идеальные. Очень редко но максимально надёжно"),
    ]
    rows = []
    for q, stars, desc in options:
        mark = "◉ " if q == current else "○ "
        rows.append([InlineKeyboardButton(
            text=f"{mark}{stars}\n   ℹ️ {desc}",
            callback_data=f"set_quality_{q}"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_targets(user: UserSettings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🎯 Цель 1: {user.tp1_rr}R → нажми чтобы изменить\n   ℹ️ 1R = риск. Например 0.8R при стопе 1% = цель 0.8%",
            callback_data="edit_tp1"
        )],
        [InlineKeyboardButton(
            text=f"🎯 Цель 2: {user.tp2_rr}R → нажми чтобы изменить\n   ℹ️ Рекомендуем 1.5-2R для основной цели",
            callback_data="edit_tp2"
        )],
        [InlineKeyboardButton(
            text=f"🏆 Цель 3: {user.tp3_rr}R → нажми чтобы изменить\n   ℹ️ Максимальная цель для части позиции",
            callback_data="edit_tp3"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


def kb_sl(user: UserSettings) -> InlineKeyboardMarkup:
    options_atr = [
        (0.5, "x0.5 — очень близкий стоп (много ложных)"),
        (1.0, "x1.0 — стандарт ⭐"),
        (1.5, "x1.5 — широкий стоп (меньше выбиваний)"),
        (2.0, "x2.0 — очень широкий"),
    ]
    options_risk = [
        (0.5, "0.5% — консервативно"),
        (1.0, "1.0% — стандарт"),
        (1.5, "1.5% — умеренно ⭐"),
        (2.0, "2.0% — агрессивно"),
        (3.0, "3.0% — очень агрессивно"),
    ]
    rows = [
        [InlineKeyboardButton(text="── ATR множитель для стоп-лосса ──", callback_data="noop")],
    ]
    for val, label in options_atr:
        mark = "◉ " if val == user.atr_mult else "○ "
        rows.append([InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"set_atr_{val}")])

    rows.append([InlineKeyboardButton(text="── Макс. риск от цены ──", callback_data="noop")])
    for val, label in options_risk:
        mark = "◉ " if val == user.max_risk_pct else "○ "
        rows.append([InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"set_risk_{val}")])

    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_volume(current: float) -> InlineKeyboardMarkup:
    options = [
        (100_000,    "100К$ — все монеты включая мелкие альты"),
        (500_000,    "500К$ — средние и крупные монеты"),
        (1_000_000,  "1М$   — стандарт, хорошая ликвидность ⭐"),
        (5_000_000,  "5М$   — только ликвидные топовые"),
        (10_000_000, "10М$  — топ-50 монет по объёму"),
        (50_000_000, "50М$  — только топ-10"),
    ]
    rows = [[InlineKeyboardButton(
        text="ℹ️ Монеты с объёмом ниже суммы пропускаются.\nМалоликвидные монеты дают ложные сигналы.",
        callback_data="noop"
    )]]
    for vol, label in options:
        mark = "◉ " if vol == current else "○ "
        rows.append([InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"set_volume_{int(vol)}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_notify(user: UserSettings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{_check(user.notify_signal)} Сигнал входа\n   ℹ️ Основное уведомление с ценой входа, стопом и целями",
            callback_data="toggle_notify_signal"
        )],
        [InlineKeyboardButton(
            text=f"{_check(user.notify_breakout)} Пробой уровня\n   ℹ️ Раннее уведомление о пробое — до ретеста. Для тех кто следит активно",
            callback_data="toggle_notify_breakout"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_main")]
    ])
