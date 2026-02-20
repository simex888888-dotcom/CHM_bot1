"""
Обработчики команд и кнопок
"""

import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from user_manager import UserManager, UserSettings
from keyboards import (
    kb_main, kb_timeframes, kb_intervals, kb_filters, kb_smc,
    kb_smc_score, kb_quality, kb_targets, kb_sl, kb_volume,
    kb_notify, kb_back
)

log = logging.getLogger("CHM.Handlers")


class EditState(StatesGroup):
    waiting_tp1 = State()
    waiting_tp2 = State()
    waiting_tp3 = State()


def settings_text(user: UserSettings) -> str:
    status  = "🟢 АКТИВЕН" if user.active else "🔴 ОСТАНОВЛЕН"
    filters = []
    if user.use_rsi:     filters.append("RSI")
    if user.use_volume:  filters.append("Объём")
    if user.use_pattern: filters.append("Паттерн")
    if user.use_htf:     filters.append("HTF")

    smc_parts = []
    if user.use_smc:
        if user.use_ob:  smc_parts.append("OB")
        if user.use_fvg: smc_parts.append("FVG")
        if user.use_liq: smc_parts.append("Sweep")
        if user.use_bos: smc_parts.append("BOS")

    return (
        f"⚡ <b>CHM BREAKER + SMC — Профиль</b>\n"
        f"\n"
        f"Статус: <b>{status}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Таймфрейм:      <b>{user.timeframe}</b>\n"
        f"🔄 Интервал:       <b>каждые {user.scan_interval // 60} мин.</b>\n"
        f"💰 Мин. объём:     <b>${user.min_volume_usdt:,.0f}</b>\n"
        f"⭐ Мин. качество:  <b>{'⭐' * user.min_quality}</b>\n"
        f"🎯 Цели:           <b>{user.tp1_rr}R / {user.tp2_rr}R / {user.tp3_rr}R</b>\n"
        f"🛡 Стоп ATR:       <b>x{user.atr_mult}</b>  макс <b>{user.max_risk_pct}%</b>\n"
        f"🔬 CHM фильтры:    <b>{', '.join(filters) or 'все выкл'}</b>\n"
        f"🧠 SMC:            <b>{'ВКЛ — ' + ', '.join(smc_parts) if user.use_smc and smc_parts else 'ВЫКЛ'}</b>\n"
        f"  Мин. SMC score: <b>{user.min_smc_score}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 Сигналов получено: <b>{user.signals_received}</b>\n"
    )


HOW_IT_WORKS = """
🔍 <b>Как работает CHM BREAKER + SMC бот</b>

Бот сканирует 200+ монет на OKX и ищет точки входа по двум системам одновременно:

<b>1️⃣ CHM BREAKER — основная логика:</b>
• Находит уровни поддержки и сопротивления (S/R)
• Ждёт пробой уровня
• Ждёт ретест пробитого уровня
• Проверяет RSI, объём, свечные паттерны, HTF тренд
• Оценивает качество сигнала 1-5 ⭐

<b>2️⃣ Smart Money Concepts — дополнительный фильтр:</b>
• 📦 <b>Order Blocks</b> — зоны набора позиций крупными игроками
• ⚡ <b>Fair Value Gaps</b> — имбалансы куда цена возвращается
• 💧 <b>Liquidity Sweeps</b> — сбор стопов перед разворотом
• 📈 <b>Break of Structure</b> — слом рыночной структуры

<b>Сигнал приходит только если:</b>
✅ CHM BREAKER нашёл ретест уровня
✅ Все выбранные фильтры подтверждают
✅ Нужное кол-во SMC факторов совпадает
✅ Качество сигнала выше минимального

<b>Команды:</b>
/start — главное меню
/menu — настройки
/stop — остановить сканер
/help — эта справка
"""


def register_handlers(dp: Dispatcher, bot: Bot, um: UserManager, scanner, config):

    # ── /start ───────────────────────────────────────────
    @dp.message(Command("start"))
    async def cmd_start(msg: Message):
        user = um.get_or_create(msg.from_user.id, msg.from_user.username or "")
        await msg.answer(
            f"👋 Привет, <b>{msg.from_user.first_name}</b>!\n\n"
            f"⚡ <b>CHM BREAKER + SMC BOT</b>\n"
            f"by CHM Laboratory\n\n"
            f"Я сканирую 200+ монет и нахожу сигналы по методологии "
            f"CHM BREAKER совмещённой со Smart Money анализом.\n\n"
            f"Настрой бота под себя и включи сканер 👇\n\n"
            f"❓ Нажми <b>«Как работает бот»</b> чтобы узнать подробнее.",
            parse_mode="HTML",
            reply_markup=kb_main(user),
        )

    @dp.message(Command("menu"))
    async def cmd_menu(msg: Message):
        user = um.get_or_create(msg.from_user.id, msg.from_user.username or "")
        await msg.answer(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    @dp.message(Command("help"))
    async def cmd_help(msg: Message):
        await msg.answer(HOW_IT_WORKS, parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup_back())

    @dp.message(Command("stop"))
    async def cmd_stop(msg: Message):
        user = um.get_or_create(msg.from_user.id)
        user.active = False
        um.save_user(user)
        await msg.answer("🔴 Сканер остановлен.\n\nНапиши /menu чтобы включить снова.")

    # ── Как работает ─────────────────────────────────────
    @dp.callback_query(F.data == "how_it_works")
    async def how_it_works(cb: CallbackQuery):
        await cb.message.edit_text(HOW_IT_WORKS, parse_mode="HTML", reply_markup=kb_back())

    # ── Вкл/Выкл сканер ──────────────────────────────────
    @dp.callback_query(F.data == "toggle_active")
    async def toggle_active(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.active = not user.active
        um.save_user(user)
        txt = "🟢 Сканер включён! Сигналы будут приходить сюда." if user.active else "🔴 Сканер выключен."
        await cb.answer(txt)
        await cb.message.edit_text(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    # ── Таймфрейм ─────────────────────────────────────────
    @dp.callback_query(F.data == "menu_tf")
    async def menu_tf(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "📊 <b>Таймфрейм свечей</b>\n\n"
            "На каких свечах анализируется рынок.\n"
            "Меньше таймфрейм = больше сигналов, но больше шума.\n"
            "Больше таймфрейм = редкие но сильные сигналы.",
            parse_mode="HTML", reply_markup=kb_timeframes(user.timeframe))

    @dp.callback_query(F.data.startswith("set_tf_"))
    async def set_tf(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.timeframe = cb.data.replace("set_tf_", "")
        um.save_user(user)
        await cb.answer(f"✅ Таймфрейм: {user.timeframe}")
        await cb.message.edit_text(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    # ── Интервал ──────────────────────────────────────────
    @dp.callback_query(F.data == "menu_interval")
    async def menu_interval(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "🔄 <b>Интервал сканирования</b>\n\n"
            "Как часто бот проверяет все монеты.\n"
            "Рекомендуется выбирать равным своему таймфрейму.\n\n"
            "⚠️ Скан 200+ монет занимает ~3-5 минут.",
            parse_mode="HTML", reply_markup=kb_intervals(user.scan_interval))

    @dp.callback_query(F.data.startswith("set_interval_"))
    async def set_interval(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.scan_interval = int(cb.data.replace("set_interval_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Интервал: каждые {user.scan_interval // 60} мин.")
        await cb.message.edit_text(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    # ── CHM Фильтры ───────────────────────────────────────
    @dp.callback_query(F.data == "menu_filters")
    async def menu_filters(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "🔬 <b>Фильтры CHM BREAKER</b>\n\n"
            "Нажми на фильтр чтобы включить или выключить.\n"
            "Больше фильтров = меньше сигналов, но надёжнее.",
            parse_mode="HTML", reply_markup=kb_filters(user))

    @dp.callback_query(F.data == "toggle_rsi")
    async def toggle_rsi(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.use_rsi = not user.use_rsi
        um.save_user(user)
        await cb.answer("RSI: " + ("✅ включён" if user.use_rsi else "❌ выключен"))
        await cb.message.edit_reply_markup(reply_markup=kb_filters(user))

    @dp.callback_query(F.data == "toggle_volume")
    async def toggle_volume_filter(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.use_volume = not user.use_volume
        um.save_user(user)
        await cb.answer("Объём: " + ("✅" if user.use_volume else "❌"))
        await cb.message.edit_reply_markup(reply_markup=kb_filters(user))

    @dp.callback_query(F.data == "toggle_pattern")
    async def toggle_pattern(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.use_pattern = not user.use_pattern
        um.save_user(user)
        await cb.answer("Паттерны: " + ("✅" if user.use_pattern else "❌"))
        await cb.message.edit_reply_markup(reply_markup=kb_filters(user))

    @dp.callback_query(F.data == "toggle_htf")
    async def toggle_htf(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.use_htf = not user.use_htf
        um.save_user(user)
        await cb.answer("HTF: " + ("✅" if user.use_htf else "❌"))
        await cb.message.edit_reply_markup(reply_markup=kb_filters(user))

    # ── SMC ───────────────────────────────────────────────
    @dp.callback_query(F.data == "menu_smc")
    async def menu_smc(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "🧠 <b>Smart Money Concepts (SMC)</b>\n\n"
            "Анализ действий крупных игроков — банков, хедж-фондов.\n"
            "SMC помогает понять куда двигается «умные деньги» и\n"
            "фильтрует слабые сигналы CHM BREAKER.\n\n"
            "Нажми на элемент чтобы вкл/выкл:",
            parse_mode="HTML", reply_markup=kb_smc(user))

    @dp.callback_query(F.data == "toggle_smc")
    async def toggle_smc(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.use_smc = not user.use_smc
        um.save_user(user)
        await cb.answer("SMC анализ: " + ("✅ включён" if user.use_smc else "❌ выключен"))
        await cb.message.edit_reply_markup(reply_markup=kb_smc(user))

    @dp.callback_query(F.data == "toggle_ob")
    async def toggle_ob(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.use_ob = not user.use_ob
        um.save_user(user)
        await cb.answer("Order Blocks: " + ("✅" if user.use_ob else "❌"))
        await cb.message.edit_reply_markup(reply_markup=kb_smc(user))

    @dp.callback_query(F.data == "toggle_fvg")
    async def toggle_fvg(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.use_fvg = not user.use_fvg
        um.save_user(user)
        await cb.answer("FVG: " + ("✅" if user.use_fvg else "❌"))
        await cb.message.edit_reply_markup(reply_markup=kb_smc(user))

    @dp.callback_query(F.data == "toggle_liq")
    async def toggle_liq(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.use_liq = not user.use_liq
        um.save_user(user)
        await cb.answer("Liquidity Sweeps: " + ("✅" if user.use_liq else "❌"))
        await cb.message.edit_reply_markup(reply_markup=kb_smc(user))

    @dp.callback_query(F.data == "toggle_bos")
    async def toggle_bos(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.use_bos = not user.use_bos
        um.save_user(user)
        await cb.answer("BOS: " + ("✅" if user.use_bos else "❌"))
        await cb.message.edit_reply_markup(reply_markup=kb_smc(user))

    @dp.callback_query(F.data == "menu_smc_score")
    async def menu_smc_score(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "🧠 <b>Минимум SMC подтверждений для сигнала</b>\n\n"
            "Сколько SMC факторов должно совпасть одновременно\n"
            "чтобы бот отправил уведомление.\n\n"
            "0 = SMC показывается как информация, не влияет на фильтр\n"
            "1 = хотя бы один фактор (рекомендуется)\n"
            "2+ = очень строго, мало сигналов",
            parse_mode="HTML", reply_markup=kb_smc_score(user.min_smc_score))

    @dp.callback_query(F.data.startswith("set_smc_score_"))
    async def set_smc_score(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.min_smc_score = int(cb.data.replace("set_smc_score_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Мин. SMC подтверждений: {user.min_smc_score}")
        await cb.message.edit_text(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    # ── Качество ──────────────────────────────────────────
    @dp.callback_query(F.data == "menu_quality")
    async def menu_quality(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "⭐ <b>Минимальное качество сигнала</b>\n\n"
            "CHM BREAKER оценивает каждый сигнал от 1 до 5 звёзд\n"
            "на основе количества подтверждений:\n\n"
            "• Высокий объём +1⭐\n"
            "• Свечной паттерн +1⭐\n"
            "• RSI в нейтральной зоне +1⭐\n"
            "• HTF тренд совпадает +1⭐\n\n"
            "Выбери минимальный порог:",
            parse_mode="HTML", reply_markup=kb_quality(user.min_quality))

    @dp.callback_query(F.data.startswith("set_quality_"))
    async def set_quality(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.min_quality = int(cb.data.replace("set_quality_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Качество: {'⭐' * user.min_quality}")
        await cb.message.edit_text(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    # ── Цели ──────────────────────────────────────────────
    @dp.callback_query(F.data == "menu_targets")
    async def menu_targets(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "🎯 <b>Цели (Take Profit)</b>\n\n"
            "Цели задаются в R — кратных риску.\n"
            "1R = расстояние от входа до стоп-лосса.\n\n"
            "Пример: вход 100$, стоп 99$ (риск 1$)\n"
            "• TP1 = 0.8R → цель 100.80$\n"
            "• TP2 = 1.5R → цель 101.50$\n"
            "• TP3 = 2.5R → цель 102.50$\n\n"
            "Нажми на цель чтобы изменить:",
            parse_mode="HTML", reply_markup=kb_targets(user))

    @dp.callback_query(F.data == "edit_tp1")
    async def edit_tp1(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.waiting_tp1)
        await cb.message.answer("Введи значение Цели 1 (например: 0.8):")

    @dp.callback_query(F.data == "edit_tp2")
    async def edit_tp2(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.waiting_tp2)
        await cb.message.answer("Введи значение Цели 2 (например: 1.5):")

    @dp.callback_query(F.data == "edit_tp3")
    async def edit_tp3(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.waiting_tp3)
        await cb.message.answer("Введи значение Цели 3 (например: 2.5):")

    @dp.message(EditState.waiting_tp1)
    async def save_tp1(msg: Message, state: FSMContext):
        user = um.get_or_create(msg.from_user.id)
        try:
            user.tp1_rr = round(float(msg.text.replace(",", ".")), 1)
            um.save_user(user)
            await state.clear()
            await msg.answer(f"✅ Цель 1 = {user.tp1_rr}R", reply_markup=kb_targets(user))
        except ValueError:
            await msg.answer("❌ Введи число, например: 0.8")

    @dp.message(EditState.waiting_tp2)
    async def save_tp2(msg: Message, state: FSMContext):
        user = um.get_or_create(msg.from_user.id)
        try:
            user.tp2_rr = round(float(msg.text.replace(",", ".")), 1)
            um.save_user(user)
            await state.clear()
            await msg.answer(f"✅ Цель 2 = {user.tp2_rr}R", reply_markup=kb_targets(user))
        except ValueError:
            await msg.answer("❌ Введи число, например: 1.5")

    @dp.message(EditState.waiting_tp3)
    async def save_tp3(msg: Message, state: FSMContext):
        user = um.get_or_create(msg.from_user.id)
        try:
            user.tp3_rr = round(float(msg.text.replace(",", ".")), 1)
            um.save_user(user)
            await state.clear()
            await msg.answer(f"✅ Цель 3 = {user.tp3_rr}R", reply_markup=kb_targets(user))
        except ValueError:
            await msg.answer("❌ Введи число, например: 2.5")

    # ── Стоп-лосс ─────────────────────────────────────────
    @dp.callback_query(F.data == "menu_sl")
    async def menu_sl(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "🛡 <b>Настройки стоп-лосса</b>\n\n"
            "<b>ATR множитель</b> — насколько далеко от цены ставится стоп.\n"
            "ATR = средний диапазон свечи. x1.0 = стоп на расстоянии одного ATR.\n\n"
            "<b>Макс. риск</b> — если расчётный стоп больше этого %, он автоматически сужается.",
            parse_mode="HTML", reply_markup=kb_sl(user))

    @dp.callback_query(F.data.startswith("set_atr_"))
    async def set_atr(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.atr_mult = float(cb.data.replace("set_atr_", ""))
        um.save_user(user)
        await cb.answer(f"✅ ATR x{user.atr_mult}")
        await cb.message.edit_reply_markup(reply_markup=kb_sl(user))

    @dp.callback_query(F.data.startswith("set_risk_"))
    async def set_risk(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.max_risk_pct = float(cb.data.replace("set_risk_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Макс. риск {user.max_risk_pct}%")
        await cb.message.edit_reply_markup(reply_markup=kb_sl(user))

    # ── Объём монет ───────────────────────────────────────
    @dp.callback_query(F.data == "menu_volume")
    async def menu_volume(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "💰 <b>Фильтр монет по объёму</b>\n\n"
            "Монеты с суточным объёмом ниже выбранной суммы\n"
            "не будут анализироваться.\n\n"
            "Малоликвидные монеты легко манипулируются и\n"
            "дают много ложных сигналов.",
            parse_mode="HTML", reply_markup=kb_volume(user.min_volume_usdt))

    @dp.callback_query(F.data.startswith("set_volume_"))
    async def set_volume(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.min_volume_usdt = float(cb.data.replace("set_volume_", ""))
        um.save_user(user)
        await cb.answer(f"✅ Мин. объём: ${user.min_volume_usdt:,.0f}")
        await cb.message.edit_text(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))

    # ── Уведомления ───────────────────────────────────────
    @dp.callback_query(F.data == "menu_notify")
    async def menu_notify(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            "📱 <b>Настройки уведомлений</b>",
            parse_mode="HTML", reply_markup=kb_notify(user))

    @dp.callback_query(F.data == "toggle_notify_signal")
    async def toggle_notify_signal(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.notify_signal = not user.notify_signal
        um.save_user(user)
        await cb.answer("Сигнал входа: " + ("✅" if user.notify_signal else "❌"))
        await cb.message.edit_reply_markup(reply_markup=kb_notify(user))

    @dp.callback_query(F.data == "toggle_notify_breakout")
    async def toggle_notify_breakout(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        user.notify_breakout = not user.notify_breakout
        um.save_user(user)
        await cb.answer("Пробой: " + ("✅" if user.notify_breakout else "❌"))
        await cb.message.edit_reply_markup(reply_markup=kb_notify(user))

    # ── Статистика ────────────────────────────────────────
    @dp.callback_query(F.data == "my_stats")
    async def my_stats(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(
            f"📈 <b>Твоя статистика</b>\n\n"
            f"Сигналов получено: <b>{user.signals_received}</b>\n"
            f"Сканер: <b>{'🟢 активен' if user.active else '🔴 выключен'}</b>\n"
            f"Таймфрейм: <b>{user.timeframe}</b>\n"
            f"SMC: <b>{'включён' if user.use_smc else 'выключен'}</b>\n",
            parse_mode="HTML", reply_markup=kb_back())

    # ── Заглушка для info-кнопок ─────────────────────────
    @dp.callback_query(F.data == "noop")
    async def noop(cb: CallbackQuery):
        await cb.answer()

    # ── Назад ─────────────────────────────────────────────
    @dp.callback_query(F.data == "back_main")
    async def back_main(cb: CallbackQuery):
        user = um.get_or_create(cb.from_user.id)
        await cb.message.edit_text(settings_text(user), parse_mode="HTML", reply_markup=kb_main(user))


def InlineKeyboardMarkup_back():
    from keyboards import kb_back
    return kb_back()
