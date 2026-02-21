"""
Обработчики всех команд и кнопок
"""

import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from user_manager import UserManager, UserSettings
from keyboards import *

log = logging.getLogger("CHM.Handlers")


class EditState(StatesGroup):
    waiting_tp1 = State()
    waiting_tp2 = State()
    waiting_tp3 = State()


def settings_text(user: UserSettings) -> str:
    status = "🟢 АКТИВЕН" if user.active else "🔴 ОСТАНОВЛЕН"
    filters = [f for f, v in [("RSI", user.use_rsi), ("Объём", user.use_volume),
               ("Паттерн", user.use_pattern), ("HTF", user.use_htf)] if v]
    smc_parts = [f for f, v in [("OB", user.use_ob), ("FVG", user.use_fvg),
                 ("Sweep", user.use_liq), ("BOS", user.use_bos)] if v and user.use_smc]
    return (
        f"⚡ <b>CHM BREAKER + SMC — Профиль</b>\n\n"
        f"Статус: <b>{status}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 ТФ: <b>{user.timeframe}</b>  HTF: <b>{user.htf_timeframe}</b>\n"
        f"🔄 Скан: <b>каждые {user.scan_interval // 60} мин.</b>\n"
        f"💰 Мин. объём: <b>${user.min_volume_usdt:,.0f}</b>\n"
        f"⭐ Качество: <b>{'⭐'*user.min_quality}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 Пивоты: сила <b>{user.pivot_strength}</b> | возраст <b>{user.max_level_age}</b> | ретест <b>{user.max_retest_bars}</b>\n"
        f"📉 EMA: <b>{user.ema_fast}/{user.ema_slow}</b>  HTF EMA: <b>{user.htf_ema_period}</b>\n"
        f"🔬 RSI: <b>{user.rsi_period}п</b> OB:<b>{user.rsi_ob}</b> OS:<b>{user.rsi_os}</b>  Vol: <b>x{user.vol_mult}</b>\n"
        f"🛡 ATR: <b>{user.atr_period}п x{user.atr_mult}</b>  Макс риск: <b>{user.max_risk_pct}%</b>\n"
        f"🎯 Цели: <b>{user.tp1_rr}R / {user.tp2_rr}R / {user.tp3_rr}R</b>\n"
        f"🔁 Cooldown: <b>{user.cooldown_bars} свечей</b>\n"
        f"🔬 Фильтры: <b>{', '.join(filters) or 'все выкл'}</b>\n"
        f"🧠 SMC: <b>{'ВКЛ — '+', '.join(smc_parts) if smc_parts else 'ВЫКЛ'}</b>  min score: <b>{user.min_smc_score}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 Сигналов получено: <b>{user.signals_received}</b>\n"
    )


HOW_IT_WORKS = (
    "🔍 <b>Как работает бот</b>\n\n"
    "<b>CHM BREAKER:</b>\n"
    "• Ищет уровни S/R через пивоты\n"
    "• Ждёт пробой + ретест уровня\n"
    "• Фильтрует по RSI, объёму, паттернам, HTF тренду\n"
    "• Оценивает качество сигнала 1-5 ⭐\n\n"
    "<b>SMC (Smart Money):</b>\n"
    "• 📦 Order Blocks — зоны набора позиций\n"
    "• ⚡ Fair Value Gaps — имбалансы цены\n"
    "• 💧 Liquidity Sweeps — сбор стопов\n"
    "• 📈 Break of Structure — слом структуры\n\n"
    "<b>Команды:</b>\n"
    "/start — главное меню\n"
    "/menu — профиль и настройки\n"
    "/stop — остановить сканер\n"
    "/help — эта справка"
)


def register_handlers(dp: Dispatcher, bot: Bot, um: UserManager, scanner, config):

    def get(cb_or_msg) -> UserSettings:
        uid = cb_or_msg.from_user.id
        uname = cb_or_msg.from_user.username or ""
        return um.get_or_create(uid, uname)

    async def back_to_main(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    # ── /start /menu /help /stop ──────────────────────────
    @dp.message(Command("start"))
    async def cmd_start(msg: Message):
        user = get(msg)
        await msg.answer(
            f"👋 Привет, <b>{msg.from_user.first_name}</b>!\n\n"
            f"⚡ <b>CHM BREAKER + SMC BOT</b> — CHM Laboratory\n\n"
            f"Сканирую 200+ монет и нахожу точки входа по CHM BREAKER + Smart Money.\n\n"
            f"Настрой всё под себя и включи сканер 👇",
            parse_mode="HTML", reply_markup=kb_main(user))

    @dp.message(Command("menu"))
    async def cmd_menu(msg: Message):
        user = get(msg)
        await msg.answer(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    @dp.message(Command("help"))
    async def cmd_help(msg: Message):
        await msg.answer(HOW_IT_WORKS, parse_mode="HTML", reply_markup=kb_back())

    @dp.message(Command("stop"))
    async def cmd_stop(msg: Message):
        user = get(msg)
        user.active = False
        um.save_user(user)
        await msg.answer("🔴 Сканер остановлен. /menu — чтобы включить снова.")

    # ── Инфо / Назад ──────────────────────────────────────
    @dp.callback_query(F.data == "how_it_works")
    async def cb_how(cb: CallbackQuery):
        await cb.message.edit_text(HOW_IT_WORKS, parse_mode="HTML", reply_markup=kb_back())

    @dp.callback_query(F.data == "back_main")
    async def cb_back(cb: CallbackQuery):
        await back_to_main(cb)

    @dp.callback_query(F.data == "noop")
    async def cb_noop(cb: CallbackQuery):
        await cb.answer()

    # ── Вкл/Выкл сканер ──────────────────────────────────
    @dp.callback_query(F.data == "toggle_active")
    async def cb_toggle(cb: CallbackQuery):
        user = get(cb)
        user.active = not user.active
        um.save_user(user)
        await cb.answer("🟢 Сканер включён!" if user.active else "🔴 Сканер выключен.")
        await back_to_main(cb)

    # ── Сброс к стандартным ───────────────────────────────
    @dp.callback_query(F.data == "reset_confirm")
    async def cb_reset_confirm(cb: CallbackQuery):
        await cb.message.edit_text(
            "♻️ <b>Сбросить все настройки к стандартным?</b>\n\nЭто действие нельзя отменить.",
            parse_mode="HTML", reply_markup=kb_reset_confirm())

    @dp.callback_query(F.data == "reset_yes")
    async def cb_reset_yes(cb: CallbackQuery):
        user = get(cb)
        uid, uname, sig = user.user_id, user.username, user.signals_received
        new_user = UserSettings(user_id=uid, username=uname, signals_received=sig)
        um.save_user(new_user)
        await cb.answer("✅ Настройки сброшены!")
        user = um.get_or_create(uid)
        await cb.message.edit_text(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    # ── Таймфрейм ─────────────────────────────────────────
    @dp.callback_query(F.data == "menu_tf")
    async def cb_menu_tf(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "📊 <b>Таймфрейм</b>\n\nРабочий ТФ — на каких свечах ищем сигналы.\nHTF — старший ТФ для фильтра тренда.",
            parse_mode="HTML", reply_markup=kb_timeframes(user.timeframe, user.htf_timeframe))

    @dp.callback_query(F.data.startswith("set_tf_"))
    async def cb_set_tf(cb: CallbackQuery):
        user = get(cb)
        user.timeframe = cb.data.replace("set_tf_", "")
        um.save_user(user)
        await cb.answer(f"✅ ТФ: {user.timeframe}")
        await cb.message.edit_reply_markup(reply_markup=kb_timeframes(user.timeframe, user.htf_timeframe))

    @dp.callback_query(F.data.startswith("set_htf_"))
    async def cb_set_htf(cb: CallbackQuery):
        user = get(cb)
        user.htf_timeframe = cb.data.replace("set_htf_", "")
        um.save_user(user)
        await cb.answer(f"✅ HTF: {user.htf_timeframe}")
        await cb.message.edit_reply_markup(reply_markup=kb_timeframes(user.timeframe, user.htf_timeframe))

    # ── Интервал ──────────────────────────────────────────
    @dp.callback_query(F.data == "menu_interval")
    async def cb_menu_interval(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "🔄 <b>Интервал сканирования</b>\n\nКак часто проверять все монеты.\nСкан 200+ монет занимает ~3-5 мин.",
            parse_mode="HTML", reply_markup=kb_intervals(user.scan_interval))

    @dp.callback_query(F.data.startswith("set_interval_"))
    async def cb_set_interval(cb: CallbackQuery):
        user = get(cb)
        user.scan_interval = int(cb.data.replace("set_interval_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Каждые {user.scan_interval // 60} мин.")
        await back_to_main(cb)

    # ── Пивоты ────────────────────────────────────────────
    @dp.callback_query(F.data == "menu_pivots")
    async def cb_menu_pivots(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "📐 <b>Пивоты и уровни S/R</b>\n\n"
            "<b>Чувствительность</b> — сколько свечей слева/справа должно быть меньше/больше чтобы точка стала пивотом. Больше = сильнее уровни.\n\n"
            "<b>Возраст уровня</b> — уровни старше этого значения игнорируются.\n\n"
            "<b>Ожидание ретеста</b> — если ретест не случился за N свечей после пробоя, пробой сбрасывается.\n\n"
            "<b>Буфер зоны</b> — ширина зоны вокруг уровня (в ATR). Цена должна попасть в эту зону для ретеста.",
            parse_mode="HTML", reply_markup=kb_pivots(cb.from_user.id and get(cb)))

    @dp.callback_query(F.data == "menu_pivots")
    async def cb_menu_pivots2(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "📐 <b>Пивоты и уровни S/R</b>\n\n"
            "Чувствительность: больше = сильнее уровни, меньше сигналов.\n"
            "Возраст: уровни старше N свечей игнорируются.\n"
            "Ретест: ждём ретест не дольше N свечей.\n"
            "Буфер: ширина зоны S/R в ATR.",
            parse_mode="HTML", reply_markup=kb_pivots(user))

    for param, attr in [
        ("pivot_strength", "pivot_strength"),
        ("level_age",      "max_level_age"),
        ("retest_bars",    "max_retest_bars"),
    ]:
        def make_int_handler(a):
            @dp.callback_query(F.data.startswith(f"set_{param}_"))
            async def handler(cb: CallbackQuery, _a=a, _p=param):
                user = get(cb)
                setattr(user, _a, int(cb.data.replace(f"set_{_p}_", "")))
                um.save_user(user)
                await cb.answer("✅ Сохранено")
                await cb.message.edit_reply_markup(reply_markup=kb_pivots(user))
        make_int_handler(attr)

    @dp.callback_query(F.data.startswith("set_zone_buffer_"))
    async def cb_zone_buffer(cb: CallbackQuery):
        user = get(cb)
        user.zone_buffer = float(cb.data.replace("set_zone_buffer_", ""))
        um.save_user(user)
        await cb.answer("✅ Сохранено")
        await cb.message.edit_reply_markup(reply_markup=kb_pivots(user))

    # ── EMA ───────────────────────────────────────────────
    @dp.callback_query(F.data == "menu_ema")
    async def cb_menu_ema(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "📉 <b>EMA тренд</b>\n\n"
            "<b>Быстрая EMA</b> — сигнальная линия тренда. Цена выше = бычий тренд.\n"
            "<b>Медленная EMA</b> — долгосрочный тренд. Если быстрая выше медленной = восходящий тренд.\n"
            "<b>HTF EMA</b> — EMA на старшем таймфрейме для дополнительного подтверждения тренда.",
            parse_mode="HTML", reply_markup=kb_ema(user))

    @dp.callback_query(F.data.startswith("set_ema_fast_"))
    async def cb_ema_fast(cb: CallbackQuery):
        user = get(cb)
        user.ema_fast = int(cb.data.replace("set_ema_fast_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Быстрая EMA: {user.ema_fast}")
        await cb.message.edit_reply_markup(reply_markup=kb_ema(user))

    @dp.callback_query(F.data.startswith("set_ema_slow_"))
    async def cb_ema_slow(cb: CallbackQuery):
        user = get(cb)
        user.ema_slow = int(cb.data.replace("set_ema_slow_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Медленная EMA: {user.ema_slow}")
        await cb.message.edit_reply_markup(reply_markup=kb_ema(user))

    @dp.callback_query(F.data.startswith("set_htf_ema_"))
    async def cb_htf_ema(cb: CallbackQuery):
        user = get(cb)
        user.htf_ema_period = int(cb.data.replace("set_htf_ema_", ""))
        um.save_user(user)
        await cb.answer(f"✅ HTF EMA: {user.htf_ema_period}")
        await cb.message.edit_reply_markup(reply_markup=kb_ema(user))

    # ── Фильтры ───────────────────────────────────────────
    @dp.callback_query(F.data == "menu_filters")
    async def cb_menu_filters(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "🔬 <b>Фильтры сигналов</b>\n\nНажми чтобы вкл/выкл фильтр или изменить параметры.",
            parse_mode="HTML", reply_markup=kb_filters(user))

    for toggle, attr in [("rsi","use_rsi"),("volume","use_volume"),("pattern","use_pattern"),("htf","use_htf")]:
        def make_toggle(a, t):
            @dp.callback_query(F.data == f"toggle_{t}")
            async def handler(cb: CallbackQuery, _a=a):
                user = get(cb)
                setattr(user, _a, not getattr(user, _a))
                um.save_user(user)
                await cb.answer("✅ вкл" if getattr(user, _a) else "❌ выкл")
                await cb.message.edit_reply_markup(reply_markup=kb_filters(user))
        make_toggle(attr, toggle)

    for param, attr in [("rsi_period","rsi_period"),("rsi_ob","rsi_ob"),("rsi_os","rsi_os"),("vol_len","vol_len")]:
        def make_int_filter(a, p):
            @dp.callback_query(F.data.startswith(f"set_{p}_"))
            async def handler(cb: CallbackQuery, _a=a, _p=p):
                user = get(cb)
                setattr(user, _a, int(cb.data.replace(f"set_{_p}_", "")))
                um.save_user(user)
                await cb.answer("✅ Сохранено")
                await cb.message.edit_reply_markup(reply_markup=kb_filters(user))
        make_int_filter(attr, param)

    @dp.callback_query(F.data.startswith("set_vol_mult_"))
    async def cb_vol_mult(cb: CallbackQuery):
        user = get(cb)
        user.vol_mult = float(cb.data.replace("set_vol_mult_", ""))
        um.save_user(user)
        await cb.answer("✅ Сохранено")
        await cb.message.edit_reply_markup(reply_markup=kb_filters(user))

    # ── Качество ──────────────────────────────────────────
    @dp.callback_query(F.data == "menu_quality")
    async def cb_menu_quality(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "⭐ <b>Минимальное качество сигнала</b>\n\n"
            "Каждое подтверждение добавляет +1⭐:\n"
            "• Объём выше среднего\n• Свечной паттерн\n• RSI в нейтральной зоне\n• HTF тренд совпадает",
            parse_mode="HTML", reply_markup=kb_quality(user.min_quality))

    @dp.callback_query(F.data.startswith("set_quality_"))
    async def cb_set_quality(cb: CallbackQuery):
        user = get(cb)
        user.min_quality = int(cb.data.replace("set_quality_", ""))
        um.save_user(user)
        await cb.answer(f"✅ {'⭐'*user.min_quality}")
        await back_to_main(cb)

    # ── Стоп-лосс ─────────────────────────────────────────
    @dp.callback_query(F.data == "menu_sl")
    async def cb_menu_sl(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "🛡 <b>Стоп-лосс</b>\n\n"
            "<b>Период ATR</b> — сколько свечей для расчёта волатильности.\n"
            "<b>ATR множитель</b> — расстояние стопа = ATR × множитель.\n"
            "<b>Макс. риск</b> — если стоп выходит за этот %, он автоматически сужается.",
            parse_mode="HTML", reply_markup=kb_sl(user))

    @dp.callback_query(F.data.startswith("set_atr_period_"))
    async def cb_atr_period(cb: CallbackQuery):
        user = get(cb)
        user.atr_period = int(cb.data.replace("set_atr_period_", ""))
        um.save_user(user)
        await cb.answer(f"✅ ATR период: {user.atr_period}")
        await cb.message.edit_reply_markup(reply_markup=kb_sl(user))

    @dp.callback_query(F.data.startswith("set_atr_"))
    async def cb_set_atr(cb: CallbackQuery):
        if "period" in cb.data:
            return
        user = get(cb)
        user.atr_mult = float(cb.data.replace("set_atr_", ""))
        um.save_user(user)
        await cb.answer(f"✅ ATR x{user.atr_mult}")
        await cb.message.edit_reply_markup(reply_markup=kb_sl(user))

    @dp.callback_query(F.data.startswith("set_risk_"))
    async def cb_set_risk(cb: CallbackQuery):
        user = get(cb)
        user.max_risk_pct = float(cb.data.replace("set_risk_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Макс. риск {user.max_risk_pct}%")
        await cb.message.edit_reply_markup(reply_markup=kb_sl(user))

    # ── Цели ──────────────────────────────────────────────
    @dp.callback_query(F.data == "menu_targets")
    async def cb_menu_targets(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "🎯 <b>Цели (Take Profit)</b>\n\n1R = расстояние от входа до стопа.\nПример: вход 100$, стоп 99$ → риск 1$\nТогда TP1 = 0.8R → цель 100.80$",
            parse_mode="HTML", reply_markup=kb_targets(user))

    @dp.callback_query(F.data == "edit_tp1")
    async def cb_edit_tp1(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.waiting_tp1)
        await cb.message.answer("Введи Цель 1 (например: 0.8):")

    @dp.callback_query(F.data == "edit_tp2")
    async def cb_edit_tp2(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.waiting_tp2)
        await cb.message.answer("Введи Цель 2 (например: 1.5):")

    @dp.callback_query(F.data == "edit_tp3")
    async def cb_edit_tp3(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.waiting_tp3)
        await cb.message.answer("Введи Цель 3 (например: 2.5):")

    @dp.message(EditState.waiting_tp1)
    async def save_tp1(msg: Message, state: FSMContext):
        user = get(msg)
        try:
            user.tp1_rr = round(float(msg.text.replace(",",".")), 1)
            um.save_user(user)
            await state.clear()
            await msg.answer(f"✅ Цель 1 = {user.tp1_rr}R", reply_markup=kb_targets(user))
        except ValueError:
            await msg.answer("❌ Введи число, например: 0.8")

    @dp.message(EditState.waiting_tp2)
    async def save_tp2(msg: Message, state: FSMContext):
        user = get(msg)
        try:
            user.tp2_rr = round(float(msg.text.replace(",",".")), 1)
            um.save_user(user)
            await state.clear()
            await msg.answer(f"✅ Цель 2 = {user.tp2_rr}R", reply_markup=kb_targets(user))
        except ValueError:
            await msg.answer("❌ Введи число, например: 1.5")

    @dp.message(EditState.waiting_tp3)
    async def save_tp3(msg: Message, state: FSMContext):
        user = get(msg)
        try:
            user.tp3_rr = round(float(msg.text.replace(",",".")), 1)
            um.save_user(user)
            await state.clear()
            await msg.answer(f"✅ Цель 3 = {user.tp3_rr}R", reply_markup=kb_targets(user))
        except ValueError:
            await msg.answer("❌ Введи число, например: 2.5")

    # ── Объём монет ───────────────────────────────────────
    @dp.callback_query(F.data == "menu_volume")
    async def cb_menu_volume(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "💰 <b>Фильтр монет по объёму</b>\n\nМонеты с суточным объёмом ниже выбранного не анализируются.\nМалоликвидные монеты легко манипулируются.",
            parse_mode="HTML", reply_markup=kb_volume(user.min_volume_usdt))

    @dp.callback_query(F.data.startswith("set_volume_"))
    async def cb_set_volume(cb: CallbackQuery):
        user = get(cb)
        user.min_volume_usdt = float(cb.data.replace("set_volume_", ""))
        um.save_user(user)
        await cb.answer(f"✅ ${user.min_volume_usdt:,.0f}")
        await back_to_main(cb)

    # ── SMC ───────────────────────────────────────────────
    @dp.callback_query(F.data == "menu_smc")
    async def cb_menu_smc(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "🧠 <b>Smart Money Concepts</b>\n\n"
            "<b>Order Blocks</b> — последняя свеча перед сильным импульсом. Зона где крупные игроки набирали позицию.\n\n"
            "<b>Fair Value Gaps</b> — разрыв между свечами. Цена часто возвращается закрыть этот гэп.\n\n"
            "<b>Liquidity Sweeps</b> — пробой очевидного уровня с разворотом. Крупный игрок собирает стопы.\n\n"
            "<b>Break of Structure</b> — пробой предыдущего хая/лоя. Подтверждает смену тренда.\n\n"
            "<b>Глубина поиска</b> — сколько свечей назад искать каждый элемент.",
            parse_mode="HTML", reply_markup=kb_smc(user))

    for toggle, attr in [("smc","use_smc"),("ob","use_ob"),("fvg","use_fvg"),("liq","use_liq"),("bos","use_bos")]:
        def make_smc_toggle(a, t):
            @dp.callback_query(F.data == f"toggle_{t}")
            async def handler(cb: CallbackQuery, _a=a):
                user = get(cb)
                setattr(user, _a, not getattr(user, _a))
                um.save_user(user)
                await cb.answer("✅ вкл" if getattr(user, _a) else "❌ выкл")
                await cb.message.edit_reply_markup(reply_markup=kb_smc(user))
        make_smc_toggle(attr, toggle)

    @dp.callback_query(F.data.startswith("set_smc_score_"))
    async def cb_smc_score(cb: CallbackQuery):
        user = get(cb)
        user.min_smc_score = int(cb.data.replace("set_smc_score_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Мин. SMC: {user.min_smc_score}")
        await cb.message.edit_reply_markup(reply_markup=kb_smc(user))

    for param, attr in [("ob_look","ob_lookback"),("fvg_look","fvg_lookback"),("liq_look","liq_lookback")]:
        def make_smc_look(a, p):
            @dp.callback_query(F.data.startswith(f"set_{p}_"))
            async def handler(cb: CallbackQuery, _a=a, _p=p):
                user = get(cb)
                setattr(user, _a, int(cb.data.replace(f"set_{_p}_", "")))
                um.save_user(user)
                await cb.answer("✅ Сохранено")
                await cb.message.edit_reply_markup(reply_markup=kb_smc(user))
        make_smc_look(attr, param)

    # ── Cooldown ──────────────────────────────────────────
    @dp.callback_query(F.data == "menu_cooldown")
    async def cb_menu_cooldown(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            "🔁 <b>Cooldown между сигналами</b>\n\nМинимальное количество свечей между двумя сигналами на одной монете.\nЗащищает от спама повторных сигналов.",
            parse_mode="HTML", reply_markup=kb_cooldown(user.cooldown_bars))

    @dp.callback_query(F.data.startswith("set_cooldown_"))
    async def cb_set_cooldown(cb: CallbackQuery):
        user = get(cb)
        user.cooldown_bars = int(cb.data.replace("set_cooldown_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Cooldown: {user.cooldown_bars} свечей")
        await back_to_main(cb)

    # ── Уведомления ───────────────────────────────────────
    @dp.callback_query(F.data == "menu_notify")
    async def cb_menu_notify(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text("📱 <b>Уведомления</b>", parse_mode="HTML", reply_markup=kb_notify(user))

    @dp.callback_query(F.data == "toggle_notify_signal")
    async def cb_toggle_notify_signal(cb: CallbackQuery):
        user = get(cb)
        user.notify_signal = not user.notify_signal
        um.save_user(user)
        await cb.answer("✅" if user.notify_signal else "❌")
        await cb.message.edit_reply_markup(reply_markup=kb_notify(user))

    @dp.callback_query(F.data == "toggle_notify_breakout")
    async def cb_toggle_notify_breakout(cb: CallbackQuery):
        user = get(cb)
        user.notify_breakout = not user.notify_breakout
        um.save_user(user)
        await cb.answer("✅" if user.notify_breakout else "❌")
        await cb.message.edit_reply_markup(reply_markup=kb_notify(user))

    # ── Статистика ────────────────────────────────────────
    @dp.callback_query(F.data == "my_stats")
    async def cb_stats(cb: CallbackQuery):
        user = get(cb)
        await cb.message.edit_text(
            f"📈 <b>Статистика</b>\n\n"
            f"Сигналов получено: <b>{user.signals_received}</b>\n"
            f"Сканер: <b>{'🟢 активен' if user.active else '🔴 выключен'}</b>",
            parse_mode="HTML", reply_markup=kb_back())
